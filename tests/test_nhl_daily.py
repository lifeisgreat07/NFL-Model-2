"""The NHL's daily run: a pick is saved once and never rewritten, a goalie is
matched to the league's player or falls back with a note, and grading
counts only final games.

Stage 58's code, tested before anything schedules it. Payloads are
synthetic.

Run with: pytest tests/test_nhl_daily.py -v
"""
import json
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from src.sports.nhl import daily, roster

NOW = datetime(2026, 10, 10, 21, 0, tzinfo=UTC)


# --- goalies by name ----------------------------------------------------------

ROSTER = {'goalies': [{'id': 8476883, 'firstName': {'default': 'Andrei'}, 'lastName': {'default': 'Vasilevskiy'}},
                      {'id': 8478406, 'firstName': {'default': 'Jonas'}, 'lastName': {'default': 'Johansson'}}]}


def test_a_projected_goalie_is_found_by_name_on_his_clubs_roster():
    gs = roster.goalies_of(ROSTER)
    assert roster.match('Andrei Vasilevskiy', gs) == (8476883, None)
    assert roster.match('andrei vasilevskiy', gs) == (8476883, None)


def test_a_name_off_the_roster_or_missing_is_reported_not_guessed():
    gs = roster.goalies_of(ROSTER)
    assert roster.match('Dan Vladar', gs)[0] is None and 'not a goalie' in roster.match('Dan Vladar', gs)[1]
    assert roster.match(None, gs) == (None, 'no goalie named')
    twins = gs + [(1, 'Andrei Vasilevskiy')]
    assert 'matches 2 goalies' in roster.match('Andrei Vasilevskiy', twins)[1]


def test_the_fallback_is_each_clubs_last_starter_by_franchise():
    box = pd.DataFrame([
        {'game_id': '1', 'game_date': '2024-04-01', 'home': 'TBL', 'away': 'UTA', 'home_goalie_id': 10, 'away_goalie_id': 20},
        {'game_id': '2', 'game_date': '2024-04-03', 'home': 'ARI', 'away': 'TBL', 'home_goalie_id': 21, 'away_goalie_id': 11},
    ])
    assert daily.last_starters(box) == {'TBL': 11, 'UTA': 21}


# --- saving --------------------------------------------------------------------

class Fixed:
    def __init__(self, p):
        self.p = p

    def predict_proba(self, x):
        return np.array([[1 - self.p, self.p]])


GAME = pd.Series({'game_id': '2026020100', 'season': 2026, 'slate': '2026-10-10',
                  'start_utc': pd.Timestamp('2026-10-10 23:00', tz='UTC'), 'home': 'TBL', 'away': 'PHI'})
FEATS = {'goal_matchup': 0.4, 'shot_matchup': 2.0, 'goalie_matchup_500': 0.01}
LINE = {'home_prob': 0.62, 'home_price': -180.0, 'away_price': 155.0, 'book': 'DraftKings'}


def test_model_b_makes_the_pick_when_there_is_a_market_and_model_a_when_there_is_not():
    with_line = daily.pick_record(GAME, FEATS, 500, Fixed(0.55), Fixed(0.40), LINE, {}, NOW)
    assert (with_line['pick'], with_line['pick_model'], with_line['model_b']) == ('PHI', 'model_b', 0.4)
    without = daily.pick_record(GAME, FEATS, 500, Fixed(0.55), Fixed(0.40), None, {}, NOW)
    assert (without['pick'], without['pick_model'], without['model_b']) == ('TBL', 'model_a', None)
    assert without['saved_utc'] == '2026-10-10T21:00:00Z' and without['start_utc'] == '2026-10-10T23:00:00Z'


def test_a_saved_pick_is_never_rewritten(tmp_path):
    first = daily.pick_record(GAME, FEATS, 500, Fixed(0.55), Fixed(0.40), LINE, {}, NOW)
    assert daily.save_once(first, tmp_path) is True
    second = dict(first, pick='TBL')
    assert daily.save_once(second, tmp_path) is False
    assert json.loads((tmp_path / '2026020100.json').read_text())['pick'] == 'PHI'


# --- grading -------------------------------------------------------------------

def test_only_final_games_are_graded_and_a_cancelled_one_is_never_counted(tmp_path):
    for gid, pick in (('1', 'TBL'), ('2', 'BOS'), ('3', 'NYR'), ('4', 'SEA')):
        (tmp_path / f'{gid}.json').write_text(json.dumps({'game_id': gid, 'pick': pick}))
    sched = pd.DataFrame([
        {'game_id': '1', 'home': 'TBL', 'away': 'PHI', 'status': 'final', 'home_win': 1},
        {'game_id': '2', 'home': 'BOS', 'away': 'OTT', 'status': 'final', 'home_win': 0},
        {'game_id': '3', 'home': 'NYR', 'away': 'NJD', 'status': 'cancelled', 'home_win': pd.NA},
        {'game_id': '4', 'home': 'SEA', 'away': 'VAN', 'status': 'in_progress', 'home_win': pd.NA},
    ])
    results = {r['game_id']: r['result'] for r in daily.grade(tmp_path, sched)}
    assert results == {'1': 'correct', '2': 'wrong', '3': 'cancelled', '4': 'pending'}


# --- history ---------------------------------------------------------------------

def test_the_season_file_only_fetches_finished_games_it_does_not_have(tmp_path, monkeypatch):
    stored = pd.DataFrame([{'game_id': '1', 'game_date': '2026-10-01'}])
    stored.to_csv(tmp_path / 'boxscores_2026.csv', index=False)
    sched = pd.DataFrame([{'game_id': '1', 'status': 'final', 'game_type': 'regular'},
                          {'game_id': '2', 'status': 'final', 'game_type': 'regular'},
                          {'game_id': '3', 'status': 'scheduled', 'game_type': 'regular'}])
    asked = []

    def fake_boxscores(season, get, schedule, pause):
        asked.extend(schedule['game_id'])
        return pd.DataFrame([{'game_id': '2', 'game_date': '2026-10-02'}])
    monkeypatch.setattr(daily.history, 'boxscores', fake_boxscores)
    out = daily.refresh_season(2026, sched, folder=tmp_path)
    assert asked == ['2']
    assert out['game_id'].tolist() == ['1', '2']


def test_drift_is_scored_on_model_a_for_final_games_only(tmp_path):
    for gid, p in (('1', 0.7), ('2', 0.4), ('3', 0.6)):
        (tmp_path / f'{gid}.json').write_text(json.dumps({'game_id': gid, 'pick': 'X', 'model_a': p}))
    sched = pd.DataFrame([
        {'game_id': '1', 'status': 'final', 'home_win': 1},
        {'game_id': '2', 'status': 'final', 'home_win': 0},
        {'game_id': '3', 'status': 'scheduled', 'home_win': pd.NA},
    ])
    assert daily.drift_rows(tmp_path, sched) == [(0.7, 1), (0.4, 0)]


def test_a_box_score_not_settled_yet_is_skipped_and_tried_next_run(tmp_path, monkeypatch):
    sched = pd.DataFrame([{'game_id': '1', 'status': 'final', 'game_type': 'regular'},
                          {'game_id': '2', 'status': 'final', 'game_type': 'regular'}])

    def fake_boxscores(season, get, schedule, pause):
        gid = schedule['game_id'].iloc[0]
        if gid == '1':
            raise daily.history.HistoryError('game 1 home: 0 starting goalies flagged, not 1')
        return pd.DataFrame([{'game_id': gid, 'game_date': '2026-10-02'}])
    monkeypatch.setattr(daily.history, 'boxscores', fake_boxscores)
    out = daily.refresh_season(2026, sched, folder=tmp_path)
    assert out['game_id'].tolist() == ['2']


# --- standings ---------------------------------------------------------------------

class Rated:
    def matchup(self, home, away, home_goalie, away_goalie, ks):
        assert home_goalie is None and away_goalie is None, 'a future game has no known goalie'
        return {'goal_matchup': 0.0, 'shot_matchup': 0.0, 'goalie_matchup_2000': 0.0}


class Half:
    def predict_proba(self, x):
        return np.tile([0.5, 0.5], (len(x), 1))


def test_the_standings_file_is_written_from_model_a_with_no_goalies(tmp_path, monkeypatch):
    monkeypatch.setattr(daily, 'PATHS', type('P', (), {'results': tmp_path})())
    sched = pd.DataFrame([
        {'game_id': '1', 'home': 'TOR', 'away': 'MTL', 'status': 'final', 'home_win': 1, 'last_period': 'OT',
         'game_type': 'regular'},
        {'game_id': '2', 'home': 'MTL', 'away': 'TOR', 'status': 'scheduled', 'home_win': None, 'last_period': None,
         'game_type': 'regular'}])
    games = pd.DataFrame({'season': [2025, 2026, 2026], 'last_period': ['REG', 'OT', 'REG']})
    out = daily.write_standings(sched, games, Rated(), Half(), 2000.0, '2026-10-10', 2026, n_sim=40)
    doc = json.loads(out.read_text(encoding='utf-8'))
    assert out.name == 'standings_2026.json' and doc['as_of'] == '2026-10-10'
    assert doc['overtime_share'] == round(1 / 3, 4)
    mtl = next(t for t in doc['teams'] if t['team'] == 'MTL')
    assert mtl['points_now'] == 1 and 1 < mtl['projected_points'] < 3


# --- page inputs ---------------------------------------------------------------------

def test_the_page_inputs_are_written_every_run_from_ratings_before_today(tmp_path, monkeypatch):
    monkeypatch.setattr(daily, 'PATHS', type('P', (), {'results': tmp_path})())
    seen = {}

    def fake_day_ratings(train, day, half_life):
        seen['last'] = train['day'].max()
        seen['day'] = day
        return daily.ratings.DayRatings({}, {}, pd.DataFrame({'saved': [], 'shots': []}))
    monkeypatch.setattr(daily.ratings, 'day_ratings', fake_day_ratings)
    games = pd.DataFrame({'day': pd.to_datetime(['2026-10-08', '2026-10-09', '2026-10-10']),
                          'season': [2026, 2026, 2026], 'home_goalie_id': [1, 2, 3], 'away_goalie_id': [4, 5, 6]})
    sched = pd.DataFrame([{'game_id': '9', 'slate': '2026-10-10', 'start_utc': pd.Timestamp('2026-10-10 23:00', tz='UTC'),
                           'home': 'TOR', 'away': 'MTL', 'status': 'scheduled', 'game_type': 'regular',
                           'home_score': None, 'away_score': None, 'last_period': None, 'neutral_site': False}])
    daily.write_page_inputs(sched, games, tmp_path / 'none', 120.0, 2000.0, pd.Timestamp('2026-10-10', tz='UTC'), 2026)
    assert seen['last'] == pd.Timestamp('2026-10-09') and seen['day'] == pd.Timestamp('2026-10-10'), \
        "today's games are not in today's ratings"
    sched_doc = json.loads((tmp_path / 'schedule_2026.json').read_text(encoding='utf-8'))
    ratings_doc = json.loads((tmp_path / 'ratings_2026.json').read_text(encoding='utf-8'))
    assert sched_doc['as_of'] == ratings_doc['as_of'] == '2026-10-10'
    assert [t['team'] for t in ratings_doc['teams']] == ['MTL', 'TOR']
