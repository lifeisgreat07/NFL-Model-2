"""The NBA's injury report as a model input (Stage 65): matched by ESPN's
athlete id, Out (and Suspension) the only statuses that remove a player, and
strict about what it keeps: since Stage 83 item 5 a row it cannot read costs
only its own team's games their availability, while a team it does not know
still refuses the whole report.

The fixture's shape is ESPN's report as read on 2026-10-09 (one team, one
player cut down to the fields this reads).

Run with: pytest tests/test_nba_injuries.py -v
"""
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.sports.nba import daily, injuries

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
                                 player('A Out', 11, 'ATL', 'Out'), player('B Out', 12, 'ORL', 'Out')), TEAMS).rows
    assert injuries.out_ids(rows, 'ATL') == {'11'} and injuries.out_ids(rows, 'ORL') == {'12'}


def test_a_suspended_player_is_removed_like_an_out_one():
    """ESPN listed Kingston Flemings as Suspension on 2026-11-02 and the strict read refused the whole
    report. Mark ruled a suspended player cannot play, so he is Out for availability (registry `amended`)."""
    assert 'Suspension' in REG['availability']['amended']
    rows = injuries.parse(report(player('Sus Pended', 21, 'ATL', 'Suspension'), player('Day', 22, 'ATL', 'Day-To-Day'),
                                 player('A Out', 23, 'ATL', 'Out')), TEAMS).rows
    assert injuries.out_ids(rows, 'ATL') == {'21', '23'}


def test_the_athlete_id_comes_from_the_players_link():
    got = injuries.parse(report(player('Keshon Gilbert', 4585618, 'ATL', 'Day-To-Day')), TEAMS)
    assert got.rows == [{'team': 'ATL', 'athlete_id': '4585618', 'name': 'Keshon Gilbert', 'status': 'Day-To-Day'}]
    assert got.unread == {}


def test_a_team_the_schedule_does_not_know_refuses_the_whole_report():
    """A changed team code would leave the real team with no rows, which reads
    as fully healthy, so this one is still a whole-report refusal."""
    with pytest.raises(injuries.InjurySourceError, match="team 'XYZ' not on the schedule"):
        injuries.parse(report(player('ok', 3, 'ATL', 'Out'), player('X', 1, 'XYZ', 'Out')), TEAMS)


@pytest.mark.parametrize('bad, why', [
    (player('Y', None, 'ATL', 'Out'), 'Y: no athlete id'),
    (player('Z', 2, 'ATL', 'Rest'), "Z: unknown status 'Rest'"),
])
def test_a_row_it_cannot_read_is_left_out_and_its_team_named(bad, why):
    """Stage 83 item 5: the rest of the report is kept; the team is named so
    its games are picked without availability."""
    got = injuries.parse(report(player('ok', 3, 'ATL', 'Out'), bad, player('B Out', 12, 'ORL', 'Out')), TEAMS)
    assert got.unread == {'ATL': [why]}
    assert [r['name'] for r in got.rows] == ['ok', 'B Out']


def game(rep):
    minutes = None
    return daily.game_availability(rep, 'ORL', 'ATL', minutes, {}, None, 120.0, datetime(2026, 11, 4, 21, 30, tzinfo=UTC))


def test_only_the_unread_teams_games_go_without_availability(monkeypatch):
    monkeypatch.setattr(daily, 'availability_for', lambda minutes, day_of, team, day, h, out: 0.9 if out else 1.0)
    rep = injuries.parse(report(player('Z', 2, 'ATL', 'Rest'), player('B Out', 12, 'ORL', 'Out')), TEAMS)
    matchup, avail, listed, why = game(rep)
    assert (matchup, avail, listed) == (None, None, None)
    assert why == "injury report rows not read for ATL (Z: unknown status 'Rest')"
    other = daily.game_availability(rep, 'ORL', 'UTAH', None, {}, None, 120.0, datetime(2026, 11, 4, tzinfo=UTC))
    assert other[0] == pytest.approx(0.9 - 1.0) and other[1] == {'read': True, 'home': 0.9, 'away': 1.0}
    assert other[3] == ''


def test_no_report_means_no_availability_for_any_game():
    assert game(None) == (None, None, None, 'injury report not read')


def test_the_pick_says_why_it_ran_without_availability():
    src = (ROOT / 'src' / 'sports' / 'nba' / 'daily.py').read_text(encoding='utf-8')
    assert "'note': f'{why}; both models ran without availability'" in src
    assert 'record = pick_record(g, feats, models, price, avail, injury_list, now, why) | trained' in src


def test_the_registry_records_the_change():
    assert 'is no longer refused whole' in REG['availability']['amended_2026_11_04']
    assert 'still refuses the whole report' in REG['availability']['amended_2026_11_04']
    (a,) = [x for x in REG['amendments'] if x['entry'] == 'availability']
    assert a['date'] == '2026-11-04' and a['before_any_result'] is False and 'all 15 picks' in a['seen']


def test_an_empty_report_is_refused():
    with pytest.raises(injuries.InjurySourceError, match='no injury list'):
        injuries.parse({'injuries': []}, TEAMS)


@pytest.mark.parametrize('payload', [
    {'injuries': [{'displayName': 'Atlanta Hawks', 'items': [player('A Out', 11, 'ATL', 'Out')]}]},
    {'injuries': [{'displayName': 'Atlanta Hawks', 'injuries': []}, {'displayName': 'Orlando Magic'}]},
])
def test_teams_with_no_player_read_refuse_the_report(payload):
    """Stage 92 item 8 (audit 7, R5): a renamed per-team key gave zero rows and
    no unread team, which read as every player playing."""
    with pytest.raises(injuries.InjurySourceError, match='teams listed and not one player read'):
        injuries.parse(payload, TEAMS)


def test_a_refused_report_makes_every_pick_say_it_ran_without_availability():
    """The refusal reaches the pick: no report, no availability, and the reason stored."""
    def get(url):
        return json.dumps({'injuries': [{'displayName': 'Atlanta Hawks', 'items': []}]}).encode()
    assert daily.read_injuries(get, TEAMS) is None
    assert game(None)[3] == 'injury report not read'


def test_one_unread_row_is_still_a_report_not_a_refusal():
    got = injuries.parse(report(player('Z', 2, 'ATL', 'Rest')), TEAMS)
    assert got.rows == [] and got.unread == {'ATL': ["Z: unknown status 'Rest'"]}


def test_what_the_pick_stores():
    rows = injuries.parse(report(player('Zed', 2, 'ORL', 'Out'), player('Abe', 1, 'ORL', 'Day-To-Day')), TEAMS).rows
    got = injuries.for_game(rows, 'ORL', 'ATL', datetime(2026, 10, 21, 21, 30, tzinfo=UTC))
    assert got['read_utc'] == '2026-10-21T21:30:00Z' and got['away'] == []
    assert [p['name'] for p in got['home']] == ['Abe', 'Zed']
