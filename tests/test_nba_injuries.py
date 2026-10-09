"""The NBA's injury report as a model input (Stage 65): strict, matched by
ESPN's athlete id, and Out the only status that removes a player.

The fixture's shape is ESPN's report as read on 2026-10-09 (one team, one
player cut down to the fields this reads).

Run with: pytest tests/test_nba_injuries.py -v
"""
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.sports.nba import injuries

ROOT = Path(__file__).resolve().parents[1]
REG = json.loads((ROOT / 'experiments/nba/stage65/registry.json').read_text(encoding='utf-8'))
TEAMS = {'ATL', 'ORL', 'UTAH'}


def player(name, pid, team, status):
    href = f'https://www.espn.com/nba/player/_/id/{pid}/{name.lower().replace(" ", "-")}' if pid else ''
    return {'status': status, 'athlete': {'displayName': name, 'links': [{'href': href}],
                                          'team': {'abbreviation': team}}}


def report(*players):
    return {'injuries': [{'displayName': 'x', 'injuries': list(players)}]}


def test_out_is_the_only_status_that_removes_a_player_as_registered():
    assert 'not listed Out' in REG['availability']['playing']
    rows = injuries.parse(report(player('Keshon Gilbert', 4585618, 'ATL', 'Day-To-Day'),
                                 player('A Out', 11, 'ATL', 'Out'), player('B Out', 12, 'ORL', 'Out')), TEAMS)
    assert injuries.out_ids(rows, 'ATL') == {'11'} and injuries.out_ids(rows, 'ORL') == {'12'}


def test_the_athlete_id_comes_from_the_players_link():
    rows = injuries.parse(report(player('Keshon Gilbert', 4585618, 'ATL', 'Day-To-Day')), TEAMS)
    assert rows == [{'team': 'ATL', 'athlete_id': '4585618', 'name': 'Keshon Gilbert', 'status': 'Day-To-Day'}]


@pytest.mark.parametrize('bad, why', [
    (player('X', 1, 'XYZ', 'Out'), "team 'XYZ' not on the schedule"),
    (player('Y', None, 'ATL', 'Out'), 'no athlete id'),
    (player('Z', 2, 'ATL', 'Suspension'), "unknown status 'Suspension'"),
])
def test_anything_unrecognised_refuses_the_whole_report(bad, why):
    """A refused report makes the run use the models without availability,
    and say so, rather than read a list it half understands."""
    with pytest.raises(injuries.InjurySourceError, match=why):
        injuries.parse(report(player('ok', 3, 'ATL', 'Out'), bad), TEAMS)


def test_an_empty_report_is_refused():
    with pytest.raises(injuries.InjurySourceError, match='no injury list'):
        injuries.parse({'injuries': []}, TEAMS)


def test_what_the_pick_stores():
    rows = injuries.parse(report(player('Zed', 2, 'ORL', 'Out'), player('Abe', 1, 'ORL', 'Day-To-Day')), TEAMS)
    got = injuries.for_game(rows, 'ORL', 'ATL', datetime(2026, 10, 21, 21, 30, tzinfo=UTC))
    assert got['read_utc'] == '2026-10-21T21:30:00Z' and got['away'] == []
    assert [p['name'] for p in got['home']] == ['Abe', 'Zed']
