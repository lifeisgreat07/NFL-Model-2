"""MLB's daily run (Stage 101 item 3): picks saved once per game and official date before first pitch, graded only on
their own date, with every input named.

Nothing is fetched: every feed is built here, and the history is a small made-up league.

Run with: pytest tests/test_mlb_daily.py -v
"""
import json
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from src.core import pick_guard
from src.sports.mlb import daily, ratings

NOW = datetime(2027, 4, 1, 16, 30, tzinfo=UTC)  # 12:30 PM Eastern
RUNS = tuple((d, h, m) for d in range(7) for h, m in ((17, 0), (22, 0), (23, 30)))
CLUBS = ['147', '111', '139', '141']


def history(n_days=60, seed=3):
    """A season of made-up games: two a day among four clubs, each with a starter and a reliever line."""
    rng = np.random.default_rng(seed)
    games, lines = [], []
    start = pd.Timestamp('2026-04-01')
    for d in range(n_days):
        day = start + pd.Timedelta(days=d)
        for j, (home, away) in enumerate(((CLUBS[d % 4], CLUBS[(d + 1) % 4]), (CLUBS[(d + 2) % 4], CLUBS[(d + 3) % 4]))):
            gid = f'9{d:03d}{j}'
            hs, as_ = int(rng.integers(0, 9)), int(rng.integers(0, 9))
            if hs == as_:
                hs += 1
            games.append({'game_id': gid, 'season': 2026, 'slate': str(day.date()), 'game_type': 'regular',
                          'start_utc': f'{day.date()}T23:05:00Z', 'home': home, 'away': away, 'home_score': hs,
                          'away_score': as_, 'neutral_site': False, 'venue_id': 1,
                          'home_starter': f'p{home}{d % 5}', 'away_starter': f'p{away}{d % 5}'})
            for club, starter, runs in ((home, f'p{home}{d % 5}', as_), (away, f'p{away}{d % 5}', hs)):
                lines.append({'game_id': gid, 'club': club, 'order': 0, 'pitcher_id': starter, 'outs': 18,
                              'runs': max(runs - 1, 0)})
                lines.append({'game_id': gid, 'club': club, 'order': 1, 'pitcher_id': f'r{club}', 'outs': 9,
                              'runs': min(runs, 1)})
    return pd.DataFrame(games), pd.DataFrame(lines)


def game(gid, slate='2027-04-01', start='2027-04-01 17:35', status='scheduled', home='147', away='111',
         number=1, dh='N', neutral=False, home_win=None, hs=None, as_=None):
    return {'game_id': gid, 'season': 2027, 'slate': slate, 'start_utc': pd.Timestamp(start, tz='UTC'), 'home': home,
            'away': away, 'status': status, 'home_score': hs, 'away_score': as_, 'home_win': home_win,
            'game_type': 'regular', 'game_number': number, 'double_header': dh, 'venue_id': 1, 'venue': 'Park',
            'neutral_site': neutral, 'series_game': 1, 'series_games': 3, 'start_time_tbd': False}


def test_a_pick_is_one_file_per_game_and_official_date_never_rewritten(tmp_path):
    rec = {'game_id': '1', 'slate': '2027-04-01', 'start_utc': '2027-04-01T23:05:00Z',
           'saved_utc': '2027-04-01T16:30:00Z', 'pick': '147'}
    assert daily.save_once(rec, tmp_path) and (tmp_path / '1_2027-04-01.json').exists()
    assert not daily.save_once(rec | {'pick': '111'}, tmp_path)
    assert json.loads((tmp_path / '1_2027-04-01.json').read_text(encoding='utf-8'))['pick'] == '147'
    # The same game postponed and picked again for the day it is played is a new file.
    assert daily.save_once(rec | {'slate': '2027-04-02', 'start_utc': '2027-04-02T23:05:00Z'}, tmp_path)


def test_a_pick_that_could_have_seen_its_result_is_refused(tmp_path):
    late = {'game_id': '1', 'slate': '2027-04-01', 'start_utc': '2027-04-01T17:00:00Z',
            'saved_utc': '2027-04-01T17:05:00Z'}
    with pytest.raises(pick_guard.LeakedPick):
        daily.save_once(late, tmp_path)
    fitted = {'game_id': '2', 'slate': '2027-04-01', 'training_through': '2027-04-01'}
    with pytest.raises(pick_guard.LeakedPick):
        daily.save_once(fitted, tmp_path)


def test_a_pick_is_graded_only_on_its_own_official_date():
    pick = {'game_id': '1', 'slate': '2027-04-01', 'pick': '147'}
    final = pd.Series(game('1', status='final', home_win=1, hs=5, as_=2))
    assert daily.grade_one(pick, final) == 'correct'
    assert daily.grade_one(pick | {'pick': '111'}, final) == 'wrong'
    moved = pd.Series(game('1', slate='2027-04-02', status='final', home_win=1, hs=5, as_=2))
    assert daily.grade_one(pick, moved) == 'postponed'
    assert daily.grade_one(pick, pd.Series(game('1', status='postponed'))) == 'postponed'
    assert daily.grade_one(pick, pd.Series(game('1', status='cancelled'))) == 'cancelled'
    assert daily.grade_one(pick, pd.Series(game('1', status='final', home_win=pd.NA, hs=3, as_=3))) == 'tie'
    assert daily.grade_one(pick, pd.Series(game('1', status='in_progress'))) == 'pending'
    assert daily.grade_one(pick, None) == 'pending'


def test_a_suspended_game_is_scored_once_completed_since_it_keeps_its_official_date():
    pick = {'game_id': '746942', 'slate': '2024-06-26', 'pick': '111'}
    resumed = pd.Series(game('746942', slate='2024-06-26', start='2024-08-26 18:05', status='final', home='111',
                             away='141', home_win=1, hs=4, as_=1))
    assert daily.grade_one(pick, resumed) == 'correct'


def test_drift_reads_scored_regular_season_picks_in_start_order():
    graded = [
        {'game_id': '2', 'slate': '2027-04-02', 'start_utc': '2027-04-02T23:05:00Z', 'game_type': 'regular',
         'model_a': 0.6, 'home_win': 1, 'result': 'correct'},
        {'game_id': '1', 'slate': '2027-04-01', 'start_utc': '2027-04-01T23:05:00Z', 'game_type': 'regular',
         'model_a': 0.4, 'home_win': 0, 'result': 'correct'},
        {'game_id': '3', 'slate': '2027-10-01', 'start_utc': '2027-10-01T23:05:00Z', 'game_type': 'wild_card',
         'model_a': 0.5, 'home_win': 1, 'result': 'wrong'},
        {'game_id': '4', 'slate': '2027-04-03', 'start_utc': '2027-04-03T23:05:00Z', 'game_type': 'regular',
         'model_a': 0.5, 'home_win': None, 'result': 'postponed'},
    ]
    assert daily.drift_rows(graded) == [(0.4, 0, '2027-04-01'), (0.6, 1, '2027-04-02')]


def test_the_models_are_fitted_strictly_before_the_picks_official_date():
    rng = np.random.default_rng(1)
    n = 80
    table = pd.DataFrame({'day': ['2027-03-31'] * n + ['2027-04-01'] * n, 'run_matchup_10': rng.normal(size=2 * n),
                          'starter_matchup_150': rng.normal(size=2 * n), 'home_win': rng.integers(0, 2, 2 * n),
                          'home_prob': 0.5, 'season': 2027})
    _, trained = daily.fit_before(table, pd.Timestamp('2027-04-01'), ['run_matchup_10', 'starter_matchup_150'], 2010)
    assert trained['training_through'] == '2027-03-31' and trained['data_provenance']['training_games'] == n


class Constant:
    """A fitted model stand-in: a fixed decision value, and a pipeline whose last step has an intercept."""

    def __init__(self, z, intercept=0.3):
        self.z, self.step = z, type('S', (), {'intercept_': np.array([intercept])})()

    def decision_function(self, x):
        return np.full(len(x), self.z)

    def predict_proba(self, x):
        p = 1 / (1 + np.exp(-(self.z + x['market_logit'].to_numpy())))
        return np.column_stack([1 - p, p])

    def __getitem__(self, i):
        return self.step


def test_a_neutral_site_game_loses_model_as_home_edge_but_not_model_bs():
    models = {'a': Constant(0.5), 'b': Constant(0.0)}
    cols = ['run_matchup_10', 'starter_matchup_150']
    feats = {cols[0]: 0.1, cols[1]: -0.2}
    home, _ = daily.predict(models, feats, cols, False, None)
    neutral, b = daily.predict(models, feats, cols, True, 0.6)
    assert home == pytest.approx(1 / (1 + np.exp(-0.5))) and neutral == pytest.approx(1 / (1 + np.exp(-0.2)))
    assert b == pytest.approx(0.6)


def test_the_pick_is_model_bs_when_priced_and_says_which_starter_was_unknown():
    g = game('1')
    price = {'source': 'espn', 'home_prob': 0.55}
    rec = daily.pick_record(g, {'run_matchup_10': 0.1}, (680776, None), 0.45, 0.55, price, NOW)
    assert rec['pick'] == '147' and rec['pick_model'] == 'model_b' and rec['market_source'] == 'espn'
    assert rec['starters'] == {'home': {'id': '680776', 'named': True}, 'away': {'id': None, 'named': False}}
    unpriced = daily.pick_record(g, {}, (None, None), 0.45, None, {'source': None}, NOW)
    assert unpriced['pick'] == '111' and unpriced['pick_model'] == 'model_a' and unpriced['model_b'] is None


def test_a_box_score_not_settled_is_left_for_the_next_run(tmp_path):
    sched = pd.DataFrame([game('1', status='final', home_win=1, hs=3, as_=2),
                          game('2', status='final', home_win=0, hs=1, as_=4)])

    def box(gid):
        return {'teams': {side: {'team': {'id': int(club)}, 'pitchers': [int(f'{gid}{i}') for i in (1, 2)],
                                 'players': {f'ID{gid}{i}': {'stats': {'pitching': {'outs': 12 + i, 'runs': i}}}
                                             for i in (1, 2)}}
                          for side, club in (('home', '147'), ('away', '111'))}}

    def get(url):
        gid = url.split('/game/')[1].split('/')[0]
        if gid == '2':
            raise OSError('not yet')
        return json.dumps(box(gid)).encode()
    games, lines = daily.refresh_season(2027, sched, tmp_path, get)
    assert list(games['game_id']) == ['1'] and len(lines) == 4
    assert games.loc[0, 'home_starter'] == '11' and games.loc[0, 'away_starter'] == '11'
    assert (tmp_path / 'games_2027.csv').exists()


class LockWithRuns(daily.GameLock):
    def __init__(self):
        super().__init__(runs=RUNS)


def test_the_run_saves_the_games_the_lock_names_and_grades_and_reports_drift(tmp_path, monkeypatch):
    past_g, past_l = history()
    sched = pd.DataFrame([game('701', start='2027-04-01 17:35'), game('702', start='2027-04-01 23:05'),
                          game('700', slate='2027-03-31', start='2027-03-31 23:05', status='final', home_win=1,
                               hs=4, as_=3)])
    paths = type('P', (), {'predictions': tmp_path / 'predictions', 'results': tmp_path / 'results',
                           'data': tmp_path / 'data'})()
    monkeypatch.setattr(daily, 'PATHS', paths)
    monkeypatch.setattr(daily.mlb_schedule, 'load_schedule', lambda season, get=None: sched)
    monkeypatch.setattr(daily, 'stored_history', lambda first, last: (past_g, past_l))
    monkeypatch.setattr(daily, 'refresh_season', lambda season, s, get=None: (past_g.iloc[:0], past_l.iloc[:0]))
    monkeypatch.setattr(daily, 'unchecked_seasons', lambda first, last: [2026])
    monkeypatch.setattr(daily, 'chosen', lambda: (120.0, 10.0, 150.0))
    monkeypatch.setattr(daily.backtest, 'load_market', lambda first, last: pd.DataFrame(
        {'game_id': past_g['game_id'], 'home_prob': 0.54}))
    monkeypatch.setattr(daily, 'GameLock', LockWithRuns)
    monkeypatch.setattr(daily.drift, 'BASELINE', tmp_path / 'no_baseline.json')
    asked = []

    def get(url):
        asked.append(url)
        if 'probablePitcher' in url:
            return json.dumps({'dates': [{'games': [
                {'gamePk': 701, 'gameType': 'R', 'officialDate': '2027-04-01', 'gameDate': '2027-04-01T17:35:00Z',
                 'teams': {'home': {'team': {'id': 147}, 'probablePitcher': {'id': 6801}},
                           'away': {'team': {'id': 111}}}}]}]}).encode()
        if 'scoreboard' in url:
            return json.dumps({'events': [{'id': 'e701', 'date': '2027-04-01T17:35Z', 'competitions': [{
                'competitors': [{'homeAway': 'home', 'team': {'abbreviation': 'NYY'}},
                                {'homeAway': 'away', 'team': {'abbreviation': 'BOS'}}]}]}]}).encode()
        if '/odds' in url:
            return json.dumps({'items': [{'provider': {'name': 'DraftKings'}, 'homeTeamOdds': {'moneyLine': -140},
                                          'awayTeamOdds': {'moneyLine': 120}}]}).encode()
        raise AssertionError(url)
    assert daily.main(NOW, get) == 0
    saved = list((paths.predictions / '2027').glob('*.json'))
    assert [p.name for p in saved] == ['701_2027-04-01.json']  # 702 is held for the 22:00 run
    pick = json.loads(saved[0].read_text(encoding='utf-8'))
    assert pick['market_source'] == 'espn' and pick['pick_model'] == 'model_b'
    assert pick['starters']['home'] == {'id': '6801', 'named': True} and pick['starters']['away']['named'] is False
    assert pick['training_through'] < '2027-04-01' and pick['unchecked_seasons'] == [2026]
    assert not any('kalshi' in u for u in asked)  # ESPN priced it, so Kalshi was never read
    lines = json.loads((paths.data / 'lines' / '2027.json').read_text(encoding='utf-8'))
    assert [r['game_id'] for r in lines] == ['701']
    report = json.loads((paths.results / 'drift_2027.json').read_text(encoding='utf-8'))
    assert report['running'] is False
    assert (paths.data / 'starters_2027.csv').exists()


def test_a_started_game_with_no_pick_is_named(tmp_path):
    assert daily.missed(['1', '2'], {'1': '2027-04-01', '2': '2027-04-01'}, tmp_path) == ['1', '2']
    (tmp_path / '1_2027-04-01.json').write_text('{}', encoding='utf-8')
    assert daily.missed(['1', '2'], {'1': '2027-04-01', '2': '2027-04-01'}, tmp_path) == ['2']


def test_history_reads_every_stored_season_and_names_the_unchecked(tmp_path):
    g, ln = history(n_days=5)
    g.to_csv(tmp_path / 'games_2026.csv', index=False)
    ln.to_csv(tmp_path / 'pitchers_2026.csv', index=False)
    (tmp_path / 'checks.json').write_text(json.dumps({'2025': {'checked': True}}), encoding='utf-8')
    games, lines = daily.stored_history(2025, 2026, tmp_path)
    assert len(games) == 10 and len(lines) == 40
    assert daily.unchecked_seasons(2025, 2026, tmp_path) == [2026]
    assert ratings.prepare(games)['day'].min() == pd.Timestamp('2026-04-01') + timedelta(0)
