"""MLB's Model A features (Stage 99), as experiments/mlb/stage98/registry.json fixes them, on games built by hand.

Run with: pytest tests/test_mlb_ratings.py -v
"""
import numpy as np
import pandas as pd
import pytest

from src.sports.mlb import backtest, ratings


def games(rows):
    g = pd.DataFrame(rows, columns=['game_id', 'season', 'slate', 'game_type', 'home', 'away', 'home_score',
                                    'away_score', 'neutral_site', 'home_starter', 'away_starter'])
    return ratings.prepare(g)


def test_a_neutral_game_carries_no_home_term_in_the_run_fit():
    g = games([['1', 2025, '2025-04-01', 'regular', 'A', 'B', 5, 1, False, 'p', 'q'],
               ['2', 2025, '2025-04-02', 'regular', 'B', 'A', 2, 3, True, 'q', 'p']])
    w = np.ones(2)
    edge, r = ratings.run_ratings(g, w, 0.0001)
    # with no home term on game 2, A - B = 1 from it, and edge + (A - B) = 4 from game 1
    assert r['A'] - r['B'] == pytest.approx(1.0, abs=1e-3) and edge == pytest.approx(3.0, abs=1e-3)


def test_an_official_tie_has_no_winner_and_rates_as_level():
    g = games([['1', 2016, '2016-09-29', 'regular', 'A', 'B', 1, 1, False, 'p', 'q']])
    assert pd.isna(g.iloc[0]['home_win']) and g.iloc[0]['run_margin'] == 0


def test_a_starters_rate_is_shrunk_toward_the_league_by_150_outs():
    day_of = pd.Series(pd.to_datetime(['2025-04-01', '2025-04-01']), index=['1', '2'])
    lines = pd.DataFrame({'game_id': ['1', '1', '2', '2'], 'pitcher_id': ['p', 'q', 'r', 's'],
                          'outs': [27, 27, 27, 27], 'runs': [9, 1, 3, 3]})
    league, rates = ratings.pitcher_rates(lines, day_of, pd.Timestamp('2025-04-02'), 1e9)
    assert league == pytest.approx(4.0)  # 16 runs over 108 outs, per 27
    assert rates['p'] == pytest.approx((9 + 150 * 16 / 108) / (27 + 150) * 27)
    assert ratings.DayRatings({}, league, rates).starter('nobody') == pytest.approx(league)
    _, firm = ratings.pitcher_rates(lines, day_of, pd.Timestamp('2025-04-02'), 1e9, k=1200)
    assert firm['p'] == pytest.approx((9 + 1200 * 16 / 108) / (27 + 1200) * 27), 'K is the grid value given'


def test_each_k_in_the_grid_gets_its_own_starter_column():
    rows = [[str(i), 2025, f'2025-04-{1 + i // 60:02d}', 'regular', 'A' if i % 2 else 'B', 'B' if i % 2 else 'A',
             3 + i % 3, 2, False, 'p' if i % 2 else 'q', 'q' if i % 2 else 'p'] for i in range(180)]
    g = games(rows)
    pid = [p for i in range(180) for p in (('p', 'q') if i % 2 else ('q', 'p'))]
    lines = pd.DataFrame({'game_id': [str(i) for i in range(180) for _ in (0, 1)], 'pitcher_id': pid,
                          'outs': [27] * 360, 'runs': [6 if p == 'p' else 1 for p in pid]})
    t = ratings.features(g, lines, 120, [10.0], [150.0, 2400.0])
    assert {'starter_matchup_150', 'starter_matchup_2400', 'run_matchup_10'} <= set(t.columns)
    assert 'starter_matchup' not in t.columns
    assert (t['starter_matchup_2400'].abs() < t['starter_matchup_150'].abs()).all(), 'more shrinkage, smaller gap'


def test_a_rating_reads_only_appearances_before_its_day():
    day_of = pd.Series(pd.to_datetime(['2025-04-01', '2025-04-05']), index=['1', '2'])
    lines = pd.DataFrame({'game_id': ['1', '2'], 'pitcher_id': ['p', 'p'], 'outs': [27, 3], 'runs': [0, 30]})
    _, rates = ratings.pitcher_rates(lines, day_of, pd.Timestamp('2025-04-05'), 1e9)
    _, later = ratings.pitcher_rates(lines, day_of, pd.Timestamp('2025-04-06'), 1e9)
    assert rates['p'] < later['p'], 'the 30-run outing on the 5th is not seen on the 5th'


def test_starter_matchup_favours_home_when_the_away_starter_is_worse():
    rated = ratings.DayRatings({'A': 1.0, 'B': 0.0}, 4.0, {'good': 3.0, 'bad': 6.0})
    m = rated.matchup('A', 'B', 'good', 'bad')
    assert m == {'run_matchup': 1.0, 'starter_matchup': 3.0}


def test_the_walk_forward_takes_the_intercept_off_a_neutral_game():
    rng = np.random.default_rng(5)
    n = 300
    t = pd.DataFrame({'game_id': [str(i) for i in range(n)], 'season': [2024] * (n - 2) + [2025, 2025],
                      'day': list(pd.date_range('2024-01-01', periods=n - 2)) + [pd.Timestamp('2025-06-01')] * 2,
                      'x': rng.normal(size=n), 'neutral_site': [False] * (n - 1) + [True]})
    t['home_win'] = (rng.random(n) < 1 / (1 + np.exp(-(0.5 + t['x'])))).astype(int)
    t.loc[n - 1, 'x'] = t.loc[n - 2, 'x']
    p = backtest.walk_forward(t, ['x'], [2025])
    tied = t.copy()
    tied.loc[n - 2, 'home_win'] = np.nan
    assert str(n - 2) not in backtest.walk_forward(tied, ['x'], [2025]).index, 'a tie is never scored'
    assert p[str(n - 1)] < p[str(n - 2)], 'the same matchup at a neutral site is less sure of the home side'


def test_only_seasons_checked_against_retrosheet_are_read(tmp_path):
    (tmp_path / 'checks.json').write_text('{"2024": {"checked": true}, "2025": {"checked": false}}', encoding='utf-8')
    with pytest.raises(backtest.history.HistoryError, match=r'not used: \[2025\]'):
        backtest.load_history(2024, 2025, folder=tmp_path)


def test_tuning_reads_no_game_after_the_validation_seasons(monkeypatch):
    seen = {}

    def fake_features(g, lines, h, alphas, shrinks=None, last_day=None):
        seen['max_season'] = int(g['season'].max())
        raise StopIteration
    monkeypatch.setattr(backtest.ratings, 'features', fake_features)
    g = pd.DataFrame({'season': [2023, 2024, 2025]})
    with pytest.raises(StopIteration):
        backtest.tune(g, pd.DataFrame(), backtest.registry())
    assert seen['max_season'] == 2024


def synthetic(n_days=400, per_day=3, seed=11):
    """A table as ratings.features returns it, over 2024 to 2026, with one feature that carries the outcome."""
    rng = np.random.default_rng(seed)
    days = pd.date_range('2024-03-01', periods=n_days, freq='2D')
    rows = []
    for d in days:
        for j in range(per_day):
            x = rng.normal()
            rows.append({'game_id': f'{d:%Y%m%d}{j}', 'day': d, 'season': d.year, 'game_type': 'regular',
                         'home': 'A', 'away': 'B', 'neutral_site': False,
                         'run_matchup_10': x, 'starter_matchup_150': rng.normal(),
                         'home_win': float(rng.random() < 1 / (1 + np.exp(-(0.2 + x))))})
    return pd.DataFrame(rows)


def test_without_a_price_a_game_is_neither_trained_on_nor_predicted_by_model_b():
    t = synthetic()
    t['home_prob'] = np.where(np.arange(len(t)) % 4 == 0, np.nan, 0.55)
    p = backtest.walk_forward(t, ['run_matchup_10'], [2025], needs_market=True)
    priced = set(t.loc[(t['season'] == 2025) & t['home_prob'].notna(), 'game_id'])
    assert set(p.index) == priced


def test_the_interval_resamples_whole_days_and_is_zero_for_identical_forecasts():
    t = synthetic(n_days=60)
    a = pd.Series(0.6, index=t['game_id'])
    iv = backtest.day_block_interval(a, a, t, 0.9833, n=200)
    assert iv['days'] == 60 and iv['games'] == 180
    assert iv['diff'] == iv['low'] == iv['high'] == 0.0


def test_confirmation_answers_each_question_on_its_own_games(monkeypatch):
    t = synthetic()
    t.loc[t.index[-1], 'home_win'] = np.nan  # an official tie: never scored
    market = pd.DataFrame({'game_id': t['game_id'][::2], 'home_prob': 0.55})
    monkeypatch.setattr(backtest.ratings, 'features', lambda g, lines, h, alphas, shrinks: t.copy())
    reg = backtest.registry()
    reg['protocol']['confirmation_seasons'] = [2025, 2026]
    out = backtest.confirm(pd.DataFrame(), pd.DataFrame(), market, reg,
                           {'H_days': 120, 'lambda': 10.0, 'K_outs': 150.0})
    played = t[t['season'].isin([2025, 2026])].dropna(subset=['home_win'])
    priced = played[played['game_id'].isin(market['game_id'])]
    q = out['questions']
    assert q['H1']['games'] == len(played) and q['M1']['games'] == len(played)
    assert q['H2']['games'] == q['H3']['games'] == len(priced) == out['scores']['market']['games']
    assert {k: v.get('label') for k, v in q.items()}['M1'] is None
    assert all(q[h]['label'] in ('ACCEPT', 'REJECT', 'INCONCLUSIVE') for h in ('H1', 'H2', 'H3'))
    assert q['H1']['level'] == 0.9833


def test_confirmation_reads_through_the_last_confirmation_season_and_so_waits_for_its_check(monkeypatch):
    seen = {}

    def fake_load(first, last, folder=None):
        seen['span'] = (first, last)
        raise StopIteration
    monkeypatch.setattr(backtest, 'load_history', fake_load)
    with pytest.raises(StopIteration):
        backtest.main(['confirm'])
    assert seen['span'] == (2010, 2026)
