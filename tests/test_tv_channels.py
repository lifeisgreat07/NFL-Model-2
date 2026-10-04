"""A TV channel reaches the page only after it passes every check (Stage 15).

src/pipeline/tv_channels.py reads nfl.com's by-week schedule and decides, per game,
which networks may be shown. These tests hold each check the plan numbers --
the exact join and cross-check, the closed network list, the slot rules and
their sourced exceptions, provenance and change history -- over synthetic
games, so no league content is committed and the suite makes no network
call. data/tv/exceptions.json is checked for what every entry must carry.

Run with: pytest tests/test_tv_channels.py -v
"""
import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]

from src.pipeline import tv_channels as tv

UTC = UTC


def utc(*args):
    return datetime(*args, tzinfo=UTC)


# Thursday 2026-10-01, 8:15 PM Eastern = 00:15 UTC Friday.
TNF = {
    'id': 'g1', 'time': '2026-10-02T00:15:00Z', 'season': 2026, 'week': 4, 'seasonType': 'REG',
    'homeTeam': {'fullName': 'Cleveland Browns'}, 'awayTeam': {'fullName': 'Pittsburgh Steelers'},
    'broadcastInfo': {'homeNetworkChannels': ['Prime Video'], 'territory': 'NATIONAL'},
    'externalIds': [{'source': 'elias', 'id': '2026100100'}],
}
ROW = {'old_game_id': '2026100100', 'away_team': 'PIT', 'home_team': 'CLE',
       'kickoff': utc(2026, 10, 2, 0, 15)}


def game(**changes):
    g = copy.deepcopy(TNF)
    for dotted, value in changes.items():
        target, keys = g, dotted.split('__')
        for k in keys[:-1]:
            target = target[k]
        target[keys[-1]] = value
    return g


@pytest.mark.parametrize('when, name, allowed', [
    (utc(2026, 10, 2, 0, 15), 'Thursday night', {'Prime Video'}),
    (utc(2026, 10, 5, 0, 20), 'Sunday night', {'NBC'}),
    (utc(2026, 10, 6, 0, 15), 'Monday night', {'ESPN', 'ABC'}),
    (utc(2026, 10, 4, 17, 0), 'Sunday afternoon', {'CBS', 'FOX'}),
    (utc(2026, 10, 4, 20, 25), 'Sunday afternoon', {'CBS', 'FOX'}),
    (utc(2026, 12, 13, 18, 0), 'Sunday afternoon', {'CBS', 'FOX'}),  # 1 PM in EST, not EDT
])
def test_each_ruled_slot_is_judged_in_eastern_time(when, name, allowed):
    assert tv.slot(when) == (name, allowed)


@pytest.mark.parametrize('when', [utc(2026, 9, 10, 0, 20), utc(2026, 10, 4, 13, 30)])
def test_a_wednesday_opener_or_a_london_morning_has_no_rule(when):
    assert tv.slot(when)[1] is None


def test_alternate_feeds_are_dropped_and_unknown_names_reported():
    g = game(broadcastInfo__homeNetworkChannels=['ESPN', 'ABC', 'ESPN2', 'ESPN DEPORTES', 'SKYCAST'])
    assert tv.networks_of(g) == (['ESPN', 'ABC'], ['SKYCAST'])


def test_a_simulcast_shows_its_first_network_only():
    """nfl.com listed ESPN and ABC for week 4's Falcons at Saints; ABC's own
    schedule has that game on ESPN alone. The first listed network is the
    rights holder, and the only one shown."""
    mnf = game(time='2026-10-06T00:15:00Z',
               broadcastInfo__homeNetworkChannels=['ESPN', 'ABC', 'ESPN2', 'ESPN DEPORTES'])
    row = dict(ROW, kickoff=utc(2026, 10, 6, 0, 15))
    rec = tv.check_game(mnf, row, [])
    assert rec['networks'] == ['ESPN'] and rec['listed'] == ['ESPN', 'ABC']


def test_nfl_com_spellings_become_the_listed_names():
    g = game(broadcastInfo__homeNetworkChannels=['NFL NETWORK', 'NETFLIX'])
    assert tv.networks_of(g)[0] == ['NFL Network', 'Netflix']


def test_a_game_passing_every_check_shows_its_channel():
    rec = tv.check_game(TNF, ROW, [])
    assert rec['networks'] == ['Prime Video'] and rec['held_back'] == []
    assert (rec['away'], rec['home'], rec['territory']) == ('PIT', 'CLE', 'NATIONAL')


def test_no_nflverse_game_with_that_id_holds_it_back():
    assert tv.check_game(TNF, None, [])['networks'] == []


def test_a_team_disagreement_holds_the_channel_back():
    rec = tv.check_game(game(homeTeam={'fullName': 'Baltimore Ravens'}), ROW, [])
    assert rec['networks'] == [] and any('teams disagree' in h for h in rec['held_back'])


def test_a_kickoff_disagreement_holds_the_channel_back():
    rec = tv.check_game(game(time='2026-10-02T01:15:00Z'), ROW, [])
    assert rec['networks'] == [] and any('kickoff disagrees' in h for h in rec['held_back'])


def test_a_missing_kickoff_holds_the_channel_back():
    rec = tv.check_game(game(time=None), ROW, [])
    assert rec['networks'] == [] and any('kickoff disagrees' in h for h in rec['held_back'])


def test_an_unlisted_name_is_reported_and_the_listed_one_still_shows():
    rec = tv.check_game(game(broadcastInfo__homeNetworkChannels=['Prime Video', 'SKYCAST']), ROW, [])
    assert rec['networks'] == ['Prime Video']
    assert rec['reported'] == ['unlisted network SKYCAST not shown']


def test_a_slot_rule_break_without_an_exception_is_held_back():
    rec = tv.check_game(game(broadcastInfo__homeNetworkChannels=['NETFLIX']), ROW, [])
    assert rec['networks'] == []
    assert any('Thursday night slot rule broken by Netflix' in h for h in rec['held_back'])


def test_an_exception_excuses_its_own_network_only():
    netflix = game(broadcastInfo__homeNetworkChannels=['NETFLIX'])
    excused = [{'elias': '2026100100', 'network': 'Netflix'}]
    assert tv.check_game(netflix, ROW, excused)['networks'] == ['Netflix']
    flexed = game(broadcastInfo__homeNetworkChannels=['PEACOCK', 'NETFLIX'])
    assert tv.check_game(flexed, ROW, excused)['networks'] == [], (
        'a game moved to another network must be checked again, not waved through')


def test_an_exception_for_another_game_excuses_nothing():
    netflix = game(broadcastInfo__homeNetworkChannels=['NETFLIX'])
    assert tv.check_game(netflix, ROW, [{'elias': '2026100400', 'network': 'Netflix'}])['networks'] == []


def test_every_shown_channel_carries_where_and_when_it_was_read():
    recs = tv.build_week([TNF], {'2026100100': ROW}, [], 'https://example/week-4', '2026-09-27T20:00:00Z')
    assert recs[0]['source'] == 'https://example/week-4' and recs[0]['read_at'] == '2026-09-27T20:00:00Z'


def test_a_game_missing_from_the_page_is_listed_with_no_channel():
    other = {'old_game_id': '2026100401', 'away_team': 'TEN', 'home_team': 'BAL',
             'kickoff': utc(2026, 10, 4, 17)}
    recs = tv.build_week([TNF], {'2026100100': ROW, '2026100401': other}, [], 'u', 't')
    assert recs[1] == {'elias': '2026100401', 'away': 'TEN', 'home': 'BAL', 'networks': [],
                       'held_back': ['not on the nfl.com page'], 'reported': []}


def test_a_change_between_reads_is_recorded_not_overwritten():
    first = tv.merge(None, [{'elias': 'e', 'away': 'LA', 'home': 'DEN', 'networks': ['CBS']}], 't1')
    again = tv.merge(first, [{'elias': 'e', 'away': 'LA', 'home': 'DEN', 'networks': ['CBS']}], 't2')
    assert again['changes'] == [] and again['reads'] == ['t1', 't2']
    flexed = tv.merge(again, [{'elias': 'e', 'away': 'LA', 'home': 'DEN', 'networks': ['NBC']}], 't3')
    assert flexed['changes'] == [{'elias': 'e', 'away': 'LA', 'home': 'DEN',
                                  'from': ['CBS'], 'to': ['NBC'], 'read_at': 't3'}]
    assert flexed['games'][0]['networks'] == ['NBC']


def test_the_team_table_is_all_32_teams_once_each():
    assert len(tv.TEAMS) == 32 and len(set(tv.TEAMS.values())) == 32


def test_every_committed_exception_carries_a_source_and_a_listed_network():
    entries = tv.load_exceptions()
    assert entries, 'the exceptions file is empty, so this check checked nothing'
    ids = [e['elias'] for e in entries]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize('broken', [
    {'elias': '2026100400', 'network': 'NFL Network', 'reason': 'London'},
    {'elias': '2026100400', 'network': 'NFL Network', 'reason': 'London', 'source': 'a friend said'},
    {'elias': '2026100400', 'network': 'NFL NETWORK', 'reason': 'London', 'source': 'https://x'},
])
def test_an_exception_without_a_source_or_with_an_unlisted_network_is_refused(tmp_path, broken):
    path = tmp_path / 'exceptions.json'
    path.write_text(json.dumps({'exceptions': [broken]}), encoding='utf-8')
    with pytest.raises(ValueError):
        tv.load_exceptions(path)


def _page(*games):
    blob = json.dumps({'data': list(games)}, separators=(',', ':'))
    return f'<script>self.__next_f.push([1,{json.dumps(blob)}])</script>'


def _schedule():
    return pd.DataFrame([{'week': 4, 'old_game_id': '2026100100', 'away_team': 'PIT',
                          'home_team': 'CLE', 'gameday': '2026-10-01', 'gametime': '20:15'}])


def test_a_run_writes_the_week_and_keeps_history(tmp_path, capsys):
    (tmp_path / 'exceptions.json').write_text(json.dumps({'exceptions': []}), encoding='utf-8')
    args = ['--season', '2026', '--weeks', '4']
    tv.main(args, now=utc(2026, 9, 27, 20), load=lambda s: _schedule(),
            fetch_page=lambda w, s: _page(TNF), tv_dir=tmp_path)
    tv.main(args, now=utc(2026, 9, 28, 5, 37), load=lambda s: _schedule(),
            fetch_page=lambda w, s: _page(game(broadcastInfo__homeNetworkChannels=['NETFLIX'])),
            tv_dir=tmp_path)
    saved = json.loads((tmp_path / '2026_week4.json').read_text(encoding='utf-8'))
    assert saved['reads'] == ['2026-09-27T20:00:00Z', '2026-09-28T05:37:00Z']
    assert saved['changes'][0]['from'] == ['Prime Video'] and saved['changes'][0]['to'] == []
    out = capsys.readouterr().out
    assert 'CHANGED PIT at CLE' in out and 'held back' in out


def test_an_unreachable_page_is_a_warning_and_writes_nothing(tmp_path, capsys):
    (tmp_path / 'exceptions.json').write_text(json.dumps({'exceptions': []}), encoding='utf-8')
    def refused(week, season):
        raise OSError('HTTP Error 403: Forbidden')
    assert tv.main(['--season', '2026', '--weeks', '4'], now=utc(2026, 9, 27, 20),
                   load=lambda s: _schedule(), fetch_page=refused, tv_dir=tmp_path) == 0
    assert not (tmp_path / '2026_week4.json').exists()
    assert 'WARNING week 4: nfl.com unreachable' in capsys.readouterr().out


def test_another_weeks_game_on_the_page_is_ignored(tmp_path):
    (tmp_path / 'exceptions.json').write_text(json.dumps({'exceptions': []}), encoding='utf-8')
    stray = game(week=3, externalIds=[{'source': 'elias', 'id': '2026092400'}])
    tv.main(['--season', '2026', '--weeks', '4'], now=utc(2026, 9, 27, 20), load=lambda s: _schedule(),
            fetch_page=lambda w, s: _page(TNF, stray), tv_dir=tmp_path)
    saved = json.loads((tmp_path / '2026_week4.json').read_text(encoding='utf-8'))
    assert [g['elias'] for g in saved['games']] == ['2026100100']
