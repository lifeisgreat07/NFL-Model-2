"""What the NHL's pages read beside the picks: the season's schedule and
the ratings as they stand.

Run with: pytest tests/test_nhl_page_inputs.py -v
"""
import json

import pandas as pd

from src.sports.nhl import page_inputs as pi
from src.sports.nhl.ratings import DayRatings


def test_the_schedule_file_carries_every_game_in_plain_json():
    sched = pd.DataFrame([
        {'game_id': '1', 'slate': '2026-10-06', 'start_utc': pd.Timestamp('2026-10-06 23:00', tz='UTC'),
         'home': 'TOR', 'away': 'MTL', 'status': 'final', 'game_type': 'regular', 'home_score': 3,
         'away_score': 2, 'last_period': 'OT', 'neutral_site': False},
        {'game_id': '2', 'slate': '2026-10-07', 'start_utc': pd.Timestamp('2026-10-07 23:30', tz='UTC'),
         'home': 'BOS', 'away': 'BUF', 'status': 'scheduled', 'game_type': 'regular', 'home_score': pd.NA,
         'away_score': pd.NA, 'last_period': None, 'neutral_site': False}])
    sched['home_score'] = sched['home_score'].astype('Int64')
    doc = pi.schedule_json(sched, '2026-10-06')
    json.dumps(doc)  # plain JSON, nothing pandas left in it
    assert doc['as_of'] == '2026-10-06' and len(doc['games']) == 2
    assert doc['games'][0]['start_utc'] == '2026-10-06T23:00:00Z' and doc['games'][0]['home_score'] == 3
    assert doc['games'][1]['home_score'] is None and doc['games'][1]['last_period'] is None


def test_goalie_names_come_from_the_picks_that_named_them():
    picks = [{'goalies': {'home': {'player_id': 8476883, 'name': 'Andrei Vasilevskiy'},
                          'away': {'player_id': 8481020, 'basis': 'last_start'}}}]
    assert pi.goalie_names(picks) == {'8476883': 'Andrei Vasilevskiy'}


RATED = DayRatings(goal={'TBL': 0.4, 'WPG': -0.1, 'UTA': 0.2}, shot={'TBL': 2.0, 'WPG': 1.0, 'UTA': -1.0},
                   goalies=pd.DataFrame({'saved': [12.0, -5.0, 1.0], 'shots': [1000.0, 800.0, 10.0]},
                                        index=pd.Index([8476883, 8481020, 1], name='goalie')))


def test_clubs_are_rated_by_franchise_best_first():
    doc = pi.ratings_json(RATED, 2000.0, ['TBL', 'WPG', 'UTA'], [], {}, '2026-10-06')
    assert [t['team'] for t in doc['teams']] == ['TBL', 'UTA', 'WPG']
    assert doc['teams'][0] == {'team': 'TBL', 'goal': 0.4, 'shot': 2.0}
    moved = pi.ratings_json(RATED, 2000.0, ['ARI'], [], {}, '2026-10-06')
    assert moved['teams'] == [{'team': 'ARI', 'goal': 0.2, 'shot': -1.0}], "Arizona reads Utah's franchise"


def test_only_recent_goalies_are_listed_best_first_with_k_shrinking_them():
    doc = pi.ratings_json(RATED, 2000.0, [], [8476883, '8481020'], {'8476883': 'Andrei Vasilevskiy'}, '2026-10-06')
    assert [g['player_id'] for g in doc['goalies']] == ['8476883', '8481020'], 'goalie 1 has no recent start'
    top = doc['goalies'][0]
    assert top['name'] == 'Andrei Vasilevskiy' and top['rating'] == round(12.0 / 3000.0, 5)
    assert doc['goalies'][1]['name'] is None
