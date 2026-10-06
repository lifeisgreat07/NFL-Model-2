"""The NHL's injury list (Stage 55 item 3): the latest day only, each club by
its abbreviation, stored in the pick with where and when it was read, and a
failed read never stops a pick being saved.

Payloads are synthetic parquet files in the shape of SportsDataverse's
`espn_nhl_injuries` release.

Run with: pytest tests/test_nhl_injuries.py -v
"""
import io
import json
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from src.sports.nhl import daily, injuries

NOW = datetime(2026, 10, 10, 21, 0, tzinfo=UTC)


def parquet(rows):
    buf = io.BytesIO()
    pd.DataFrame(rows).to_parquet(buf, index=False)
    return buf.getvalue()


def row(day, club, name, status='Out', pos='C'):
    return {'as_of_date': day, 'team_display_name': club, 'athlete_display_name': name,
            'athlete_position': pos, 'status': status, 'league': 'nhl'}


LIST = [
    row('2026-10-08', 'Tampa Bay Lightning', 'Old Name'),
    row('2026-10-09', 'Tampa Bay Lightning', 'Brayden Point', 'Day-To-Day'),
    row('2026-10-09', 'Tampa Bay Lightning', 'Anthony Cirelli', 'Injured Reserve'),
    row('2026-10-09', 'Montreal Canadiens', 'Kaiden Guhle', 'Injured Reserve', 'D'),
    row('2026-10-09', 'Philadelphia Flyers', 'Nikita Grebenkin', 'Suspension', 'RW'),
]


def test_the_season_starting_in_2026_is_espns_2027_file():
    assert injuries.source(2026).endswith('/injuries_2027.parquet')


def test_only_the_latest_day_is_read_and_each_club_is_its_abbreviation():
    day, table = injuries.latest(parquet(LIST))
    assert day == '2026-10-09'
    assert 'Old Name' not in set(table['athlete_display_name'])
    assert set(table['team']) == {'TBL', 'MTL', 'PHI'}


def test_a_game_stores_each_sides_players_sorted_with_source_and_times():
    day, table = injuries.latest(parquet(LIST))
    got = injuries.for_game(day, table, 'TBL', 'MTL', NOW)
    assert got == {'source': 'espn_nhl_injuries', 'as_of': '2026-10-09', 'read_utc': '2026-10-10T21:00:00Z',
                   'home': [{'name': 'Anthony Cirelli', 'position': 'C', 'status': 'Injured Reserve'},
                            {'name': 'Brayden Point', 'position': 'C', 'status': 'Day-To-Day'}],
                   'away': [{'name': 'Kaiden Guhle', 'position': 'D', 'status': 'Injured Reserve'}]}
    assert injuries.for_game(day, table, 'BOS', 'NYR', NOW)['home'] == []


@pytest.mark.parametrize('raw, why', [
    (b'not parquet', 'not a parquet file'),
    (parquet([{'as_of_date': '2026-10-09', 'team_display_name': 'Boston Bruins'}]), 'columns missing'),
    (parquet([row('2026-10-09', 'Quebec Nordiques', 'Peter Stastny')]), 'clubs not recognised'),
])
def test_a_file_that_is_not_the_list_is_refused_not_guessed(raw, why):
    with pytest.raises(injuries.InjurySourceError, match=why):
        injuries.latest(raw)


def test_a_failed_read_is_none_and_says_so(capsys):
    def down(url):
        raise OSError('503')
    assert daily.read_injuries(2026, down) is None
    assert daily.read_injuries(2026, lambda url: b'junk') is None
    assert capsys.readouterr().out.count('picks saved without them') == 2


class Fixed:
    def __init__(self, p):
        self.p = p

    def predict_proba(self, x):
        return np.array([[1 - self.p, self.p]])


def test_the_pick_stores_the_list_and_none_when_there_is_none():
    game = pd.Series({'game_id': '1', 'season': 2026, 'slate': '2026-10-10',
                      'start_utc': pd.Timestamp('2026-10-10 23:00', tz='UTC'), 'home': 'TBL', 'away': 'MTL'})
    feats = {'goal_matchup': 0.0, 'shot_matchup': 0.0, 'goalie_matchup_500': 0.0}
    day, table = injuries.latest(parquet(LIST))
    listed = injuries.for_game(day, table, 'TBL', 'MTL', NOW)
    with_list = daily.pick_record(game, feats, 500, Fixed(0.5), Fixed(0.5), None, {}, NOW, listed)
    assert json.loads(json.dumps(with_list))['injuries'] == listed
    assert daily.pick_record(game, feats, 500, Fixed(0.5), Fixed(0.5), None, {}, NOW)['injuries'] is None
