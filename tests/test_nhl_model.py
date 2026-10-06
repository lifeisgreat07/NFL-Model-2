"""Model A's features and the Stage 56 backtest's machinery, on synthetic games.

What matters most here is the walk-forward: no feature, and no
prediction, may use a game from its own day or later. The tests change
those games' results and check nothing before them moves.

Run with: pytest tests/test_nhl_model.py -v
"""
import numpy as np
import pandas as pd
import pytest

from src.sports.nhl import backtest, ratings

TEAMS = ['TOR', 'MTL', 'BOS', 'WPG', 'UTA', 'SEA']


def synthetic(days=120, seed=7, strength=None):
    """Three games a day among six teams; TOR is strong, SEA weak."""
    rng = np.random.default_rng(seed)
    strength = strength or {'TOR': 1.0, 'MTL': 0.3, 'BOS': 0.2, 'WPG': 0.0, 'UTA': -0.4, 'SEA': -1.1}
    rows, gid = [], 0
    start = pd.Timestamp('2021-10-01')
    for d in range(days):
        order = rng.permutation(TEAMS)
        for i in range(0, 6, 2):
            home, away = order[i], order[i + 1]
            edge = strength[home] - strength[away] + 0.2
            hg, ag = rng.poisson(3 + edge / 2), rng.poisson(3 - edge / 2)
            if hg == ag:
                hg += 1
            gid += 1
            rows.append({'game_id': str(2021000000 + gid), 'season': 2021, 'game_type': 'regular',
                         'game_date': (start + pd.Timedelta(days=d)).strftime('%Y-%m-%d'),
                         'home': home, 'away': away, 'home_score': hg, 'away_score': ag, 'last_period': 'REG',
                         'home_sog': int(30 + 4 * edge + rng.integers(-3, 4)), 'away_sog': int(30 - 4 * edge),
                         'home_goalie_id': f'G{home}', 'home_goalie_sa': 30, 'home_goalie_ga': ag,
                         'away_goalie_id': f'G{away}', 'away_goalie_sa': 30, 'away_goalie_ga': hg})
    return pd.DataFrame(rows)


# --- ratings ------------------------------------------------------------------------

def test_franchises_follow_the_roster():
    assert ratings.franchise('ATL') == 'WPG'
    assert ratings.franchise('PHX') == 'UTA' and ratings.franchise('ARI') == 'UTA'
    assert ratings.franchise('VGK') == 'VGK'


def test_a_shootout_counts_as_a_win_but_not_in_the_goal_margin():
    g = synthetic(days=1).iloc[:1].assign(home_score=3, away_score=2, last_period='SO',
                                           home='ATL', away='ARI')
    p = ratings.prepare(g).iloc[0]
    assert p['goal_margin'] == 0 and p['home_win'] == 1
    assert (p['home'], p['away']) == ('WPG', 'UTA')


def test_a_game_one_half_life_ago_weighs_a_half():
    days = pd.Series(pd.to_datetime(['2026-01-01', '2025-12-02']))
    w = ratings.weights(days, pd.Timestamp('2026-01-31'), 30)
    assert w == pytest.approx([0.5, 0.25])


def test_the_ridge_ranks_the_strong_team_first_and_finds_the_home_edge():
    g = ratings.prepare(synthetic(days=120))
    edge, r = ratings.ridge_ratings(g, 'goal_margin', np.ones(len(g)))
    assert max(r, key=r.get) == 'TOR' and min(r, key=r.get) == 'SEA'
    assert edge > 0


def test_a_goalie_better_than_the_league_rates_above_zero_and_k_pulls_him_back():
    g = ratings.prepare(synthetic(days=60))
    g.loc[g['home'] == 'TOR', 'home_goalie_ga'] = 0
    terms = ratings.goalie_terms(g, np.ones(len(g)))
    small, big = ratings.goalie_rating(terms, 'GTOR', 100), ratings.goalie_rating(terms, 'GTOR', 10000)
    assert small > big > 0
    assert ratings.goalie_rating(terms, 'nobody', 100) == 0.0


def test_a_days_features_ignore_that_day_and_everything_after():
    g = ratings.prepare(synthetic(days=90))
    day = g['day'].iloc[len(g) // 2]
    before = ratings.features(g, 60, [500], first_day=str(day.date()))
    changed = g.copy()
    later = changed['day'] >= day
    changed.loc[later, ['home_score', 'away_score', 'goal_margin', 'shot_margin']] = [9, 0, 9, 40]
    changed.loc[later, 'home_goalie_ga'] = 9
    after = ratings.features(changed, 60, [500], first_day=str(day.date()))
    cols = ['goal_matchup', 'shot_matchup', 'goalie_matchup_500']
    first = before['day'] == day
    pd.testing.assert_frame_equal(before.loc[first, cols].reset_index(drop=True),
                                  after.loc[after['day'] == day, cols].reset_index(drop=True))


def test_no_features_until_there_are_a_hundred_earlier_games():
    g = ratings.prepare(synthetic(days=40))
    f = ratings.features(g, 60, [500])
    first = f['day'].min()
    assert (g['day'] < first).sum() >= 100
    assert (g['day'] < first - pd.Timedelta(days=1)).sum() < 100


# --- the backtest's machinery -----------------------------------------------------

def table(days=80):
    g = ratings.prepare(synthetic(days=days))
    t = ratings.features(g, 60, [500]).merge(g[['game_id']], on='game_id')
    t['home_prob'] = np.where(np.arange(len(t)) % 2 == 0, 0.55, np.nan)
    t.loc[t.index >= len(t) // 2, 'season'] = 2022
    return t


COLS = ['goal_matchup', 'shot_matchup', 'goalie_matchup_500']


def test_a_days_predictions_do_not_see_that_days_results():
    t = table()
    day = t.loc[t['season'] == 2022, 'day'].min()
    p1 = backtest.walk_forward(t, COLS, [2022])
    flipped = t.copy()
    flipped.loc[flipped['day'] >= day, 'home_win'] = 1 - flipped.loc[flipped['day'] >= day, 'home_win']
    p2 = backtest.walk_forward(flipped, COLS, [2022])
    first = t.loc[t['day'] == day, 'game_id']
    assert p1.loc[first].tolist() == pytest.approx(p2.loc[first].tolist())
    assert set(p1.index) == set(t.loc[t['season'] == 2022, 'game_id'])


def test_a_market_model_neither_trains_on_nor_predicts_unpriced_games():
    t = table()
    p = backtest.walk_forward(t, COLS, [2022], needs_market=True)
    priced = t.dropna(subset=['home_prob'])
    assert set(p.index) == set(priced.loc[priced['season'] == 2022, 'game_id'])


def test_the_base_rate_is_the_share_of_earlier_home_wins():
    t = table()
    p = backtest.base_rate(t, [2022])
    gid = p.index[0]
    day = t.set_index('game_id').loc[gid, 'day']
    assert p.loc[gid] == pytest.approx(t.loc[t['day'] < day, 'home_win'].mean())


def test_the_registered_labels():
    assert backtest.label({'low': -0.02, 'high': -0.001}) == 'ACCEPT'
    assert backtest.label({'low': 0.001, 'high': 0.02}) == 'REJECT'
    assert backtest.label({'low': -0.01, 'high': 0.01}) == 'INCONCLUSIVE'
    assert backtest.label({'low': -0.01, 'high': 0.0}) == 'INCONCLUSIVE'


def test_the_day_block_bootstrap_is_paired_and_seeded():
    t = table()
    p = backtest.walk_forward(t, COLS, [2022])
    same = backtest.day_block_interval(p, p, t, 0.9833)
    assert (same['diff'], same['low'], same['high']) == (0.0, 0.0, 0.0)
    worse = (p * 0 + 0.5)
    a = backtest.day_block_interval(p, worse, t, 0.9833)
    b = backtest.day_block_interval(p, worse, t, 0.9833)
    assert a == b and a['low'] <= a['diff'] <= a['high']
    assert a['days'] == t.loc[t['season'] == 2022, 'day'].nunique()


def test_scores_report_log_loss_brier_and_accuracy():
    t = pd.DataFrame({'game_id': ['a', 'b'], 'home_win': [1, 0]})
    s = backtest.scores(pd.Series({'a': 0.8, 'b': 0.4}), t)
    assert s['games'] == 2 and s['accuracy'] == 1.0
    assert s['log_loss'] == pytest.approx(-(np.log(0.8) + np.log(0.6)) / 2)
    assert s['brier'] == pytest.approx((0.04 + 0.16) / 2)


def test_a_live_pick_gets_exactly_the_features_the_backtest_scored():
    """The daily run rates a game with `day_ratings(...).matchup`; the
    backtest with `features`. They must be the same numbers."""
    g = ratings.prepare(synthetic(days=90))
    day = g['day'].iloc[len(g) // 2]
    table = ratings.features(g, 60, [500], first_day=str(day.date()))
    first = table[table['day'] == day].reset_index(drop=True)
    rated = ratings.day_ratings(g[g['day'] < day], day, 60)
    games = g[g['day'] == day].reset_index(drop=True)
    for i, row in games.iterrows():
        live = rated.matchup(row['home'], row['away'], row['home_goalie_id'], row['away_goalie_id'], [500])
        for col, value in live.items():
            assert first.loc[i, col] == pytest.approx(value, abs=1e-12)
