"""The NBA's daily run (Stage 65): a pick is saved once and never rewritten,
Model B makes it only with a named price, an unread injury report is said
and never filled in, and grading counts only final games.

Payloads are synthetic.

Run with: pytest tests/test_nba_daily.py -v
"""
import json
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from src.sports.nba import daily, ratings

NOW = datetime(2026, 10, 21, 21, 30, tzinfo=UTC)


class Fixed:
    """A fitted model stand-in that records the columns it was asked about."""

    def __init__(self, p):
        self.p, self.seen = p, None

    def predict_proba(self, x):
        self.seen = list(x.columns)
        return np.array([[1 - self.p, self.p]])


def models():
    return {'a': Fixed(0.55), 'b': Fixed(0.40), 'a_no_availability': Fixed(0.60), 'b_no_availability': Fixed(0.45)}


GAME = pd.Series({'game_id': '401909834', 'season': 2026, 'slate': '2026-10-21',
                  'start_utc': pd.Timestamp('2026-10-21 23:00', tz='UTC'), 'home': 'ORL', 'away': 'ATL'})
FEATS = {'point_matchup': 2.0, 'efficiency_matchup': 1.5, 'availability_matchup': -0.05}
ESPN = {'source': 'espn', 'provider': 'DraftKings', 'home_price': -130, 'away_price': 110, 'home_prob': 0.5427}
NONE = {'source': None, 'home_prob': None, 'why': 'ESPN has no pre-game price; Kalshi lists no quoted market for the game'}
AVAIL = {'read': True, 'home': 0.97, 'away': 1.02}


def test_model_b_makes_the_pick_with_a_price_and_names_its_source():
    m = models()
    r = daily.pick_record(GAME, FEATS, m, ESPN, AVAIL, None, NOW)
    assert (r['pick'], r['pick_model'], r['model_b'], r['market_source']) == ('ATL', 'model_b', 0.4, 'espn')
    assert m['b'].seen == [*daily.A_COLUMNS, 'market_logit']


def test_with_no_price_the_pick_is_model_as_and_says_no_price():
    r = daily.pick_record(GAME, FEATS, models(), NONE, AVAIL, None, NOW)
    assert (r['pick'], r['pick_model'], r['model_b'], r['market_source']) == ('ORL', 'model_a', None, None)
    assert r['market']['why'].startswith('ESPN has no pre-game price')


def test_an_unread_injury_report_runs_both_models_without_availability_and_says_so():
    m = models()
    feats = {k: v for k, v in FEATS.items() if k != 'availability_matchup'}
    r = daily.pick_record(GAME, feats, m, ESPN, None, None, NOW)
    assert m['a_no_availability'].seen == daily.NO_AVAIL and m['a'].seen is None
    assert m['b_no_availability'].seen == [*daily.NO_AVAIL, 'market_logit']
    assert r['model_a'] == 0.6 and r['model_b'] == 0.45
    assert r['availability']['read'] is False and 'not read' in r['availability']['note']
    assert 'availability_matchup' not in r['features']


def test_availability_counts_everyone_not_listed_out():
    minutes = pd.DataFrame([
        {'game_id': '1', 'team': 'ORL', 'player_id': 'star', 'minutes': 36},
        {'game_id': '1', 'team': 'ORL', 'player_id': 'bench', 'minutes': 12},
    ])
    day_of = {'1': pd.Timestamp('2026-10-20')}
    day = pd.Timestamp('2026-10-21')
    assert daily.availability_for(minutes, day_of, 'ORL', day, 120, set()) == 1.0
    assert daily.availability_for(minutes, day_of, 'ORL', day, 120, {'star'}) == 12 / 48


def test_a_saved_pick_is_never_rewritten(tmp_path):
    first = daily.pick_record(GAME, FEATS, models(), ESPN, AVAIL, None, NOW)
    assert daily.save_once(first, tmp_path) is True
    assert daily.save_once(dict(first, pick='ORL'), tmp_path) is False
    assert json.loads((tmp_path / '401909834.json').read_text())['pick'] == 'ATL'


def test_only_final_games_are_graded_and_a_cancelled_one_is_never_counted(tmp_path):
    for gid, pick in (('1', 'ORL'), ('2', 'BOS'), ('3', 'NY'), ('4', 'SA')):
        (tmp_path / f'{gid}.json').write_text(json.dumps({'game_id': gid, 'pick': pick, 'market_source': 'espn'}))
    sched = pd.DataFrame([
        {'game_id': '1', 'home': 'ORL', 'away': 'ATL', 'status': 'final', 'home_win': 1},
        {'game_id': '2', 'home': 'BOS', 'away': 'PHI', 'status': 'final', 'home_win': 0},
        {'game_id': '3', 'home': 'NY', 'away': 'BKN', 'status': 'cancelled', 'home_win': pd.NA},
        {'game_id': '4', 'home': 'SA', 'away': 'DAL', 'status': 'in_progress', 'home_win': pd.NA},
    ])
    results = {r['game_id']: r['result'] for r in daily.grade(tmp_path, sched)}
    assert results == {'1': 'correct', '2': 'wrong', '3': 'cancelled', '4': 'pending'}


def test_drift_is_scored_on_model_a_for_final_games_only(tmp_path):
    for gid, p in (('1', 0.7), ('2', 0.4), ('3', 0.6)):
        (tmp_path / f'{gid}.json').write_text(json.dumps({'game_id': gid, 'pick': 'X', 'model_a': p}))
    sched = pd.DataFrame([
        {'game_id': '1', 'status': 'final', 'home_win': 1},
        {'game_id': '2', 'status': 'final', 'home_win': 0},
        {'game_id': '3', 'status': 'scheduled', 'home_win': pd.NA},
    ])
    assert daily.drift_rows(tmp_path, sched) == [(0.7, 1), (0.4, 0)]


def test_the_season_file_only_fetches_finished_games_it_does_not_have(tmp_path, monkeypatch):
    pd.DataFrame([{'game_id': '1', 'slate': '2026-10-20'}]).to_csv(tmp_path / 'games_2026.csv', index=False)
    sched = pd.DataFrame([{'game_id': '1', 'status': 'final'}, {'game_id': '2', 'status': 'final'},
                          {'game_id': '3', 'status': 'scheduled'}, {'game_id': '4', 'status': 'final'}])
    asked = []

    def fake_boxscores(season, get, schedule, pause):
        gid = schedule['game_id'].iloc[0]
        asked.append(gid)
        if gid == '4':
            raise daily.history.HistoryError('game 4: no players listed')
        return (pd.DataFrame([{'game_id': gid, 'slate': '2026-10-21'}]),
                pd.DataFrame([{'game_id': gid, 'team': 'ORL', 'player_id': 'p', 'minutes': 30}]), [])
    monkeypatch.setattr(daily.history, 'boxscores', fake_boxscores)
    games, minutes = daily.refresh_season(2026, sched, folder=tmp_path)
    assert asked == ['2', '4']
    assert games['game_id'].tolist() == ['1', '2'] and minutes['game_id'].tolist() == ['2']


def test_the_values_are_the_ones_stage_61s_validation_chose():
    assert daily.chosen() == (120.0, 10.0)


def test_the_live_availability_matches_the_backtests_for_the_same_players():
    """Fed the box score's players, the live path gives the backtest's own
    availability_matchup: the registration's one term, two code paths."""
    g = pd.DataFrame([
        {'game_id': 'a', 'slate': '2026-10-01', 'home': 'ORL', 'away': 'ATL'},
        {'game_id': 'b', 'slate': '2026-10-05', 'home': 'ATL', 'away': 'ORL'},
        {'game_id': 'c', 'slate': '2026-10-09', 'home': 'ORL', 'away': 'ATL'},
    ]).assign(day=lambda d: pd.to_datetime(d['slate']))
    m = pd.DataFrame([
        {'game_id': gid, 'team': t, 'player_id': f'{t}{i}', 'minutes': mins}
        for gid, mins_by in (('a', (30, 20, 10)), ('b', (32, 0, 16)), ('c', (0, 24, 24)))
        for t in ('ORL', 'ATL') for i, mins in enumerate(mins_by)])
    table = ratings.availability_table(g, m, 120)
    day_of = dict(zip(g['game_id'], g['day']))
    out_c = {p for p in m.loc[(m['game_id'] == 'c') & (m['minutes'] == 0), 'player_id']}
    live = (daily.availability_for(m, day_of, 'ORL', g['day'][2], 120, out_c)
            - daily.availability_for(m, day_of, 'ATL', g['day'][2], 120, out_c))
    assert abs(live - table['c']) < 1e-12
