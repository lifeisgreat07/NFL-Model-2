"""A tip time is printed unless ESPN says it is not set (Stage 77 item 33, as corrected 2026-10-15).

Item 33 (the 2026-10-13 audit's B5) took opening night's BOS at DET at
"3:00 PM" (19:00Z) for ESPN's placeholder and printed any weekday tip
before 5 PM Eastern as "time TBD". It is a real matinee on NBC; ESPN marks
the time as set, and Christmas Day's noon and 2:30 games too. The rule
also hid the opening-night lock countdown, which waits for every opening
game's time.

ESPN's own flag is read instead: the competition's `timeValid`, kept by
the schedule as `time_valid`, written to the daily run's schedule file,
and handed to the board as `tv` and to the home page as `unset` (the
starts flagged false). Only an explicit false reads "time TBD"; a schedule
file written before the field existed prints its times.
tipSet runs here under node; tests/browser/check_nba_tip.py reads the rows.

Run with: pytest tests/test_nba_tip_time.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from src.site import home as home_py
from src.sports.nba import page_inputs, site
from src.sports.nba import schedule as nba

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js'
HOME = ROOT / 'src' / 'site' / 'home' / 'home.js'
NODE = shutil.which('node')
OPENING = '2026-10-20T19:00:00Z'   # BOS at DET, Tue 3:00 PM EDT: a real time


def event(gid, start, time_valid='absent'):
    comp = {'type': {'abbreviation': 'STD'}, 'neutralSite': False, 'venue': {'fullName': 'Arena'},
            'competitors': [{'homeAway': 'home', 'team': {'abbreviation': 'DET'}},
                            {'homeAway': 'away', 'team': {'abbreviation': 'BOS'}}],
            'status': {'type': {'name': 'STATUS_SCHEDULED'}}}
    if time_valid != 'absent':
        comp['timeValid'] = time_valid
    return {'id': gid, 'date': start, 'season': {'year': 2027, 'type': 2}, 'competitions': [comp]}


def test_the_schedule_keeps_espns_flag():
    df = nba.to_schedule([('2026-10-20', event('1', '2026-10-20T19:00Z', True)),
                          ('2026-10-20', event('2', '2026-10-20T23:00Z', False)),
                          ('2026-10-20', event('3', '2026-10-21T01:30Z'))], 2026)
    flags = dict(zip(df['game_id'], df['time_valid']))
    assert [bool(flags['1']), bool(flags['2'])] == [True, False] and pd.isna(flags['3'])
    assert str(df['time_valid'].dtype) == 'boolean'
    assert 'time_valid' in nba.EXTRA_COLUMNS


def test_the_schedule_file_and_the_board_carry_it():
    df = nba.to_schedule([('2026-10-20', event('1', '2026-10-20T19:00Z', True)),
                          ('2026-10-20', event('2', '2026-10-20T23:00Z', False)),
                          ('2026-10-20', event('3', '2026-10-21T01:30Z'))], 2026)
    rows = {r['game_id']: r for r in page_inputs.schedule_json(df, '2026-10-15')['games']}
    assert [rows[g]['time_valid'] for g in '123'] == [True, False, None]
    assert [site.slim_game(rows[g])['tv'] for g in '123'] == [True, False, None]
    json.dumps(rows)   # plain values, writable as they are


def tip_set(games):
    if not NODE:
        pytest.skip('node not available')
    js = JS.read_text(encoding='utf-8')
    fn = re.search(r'function tipSet\(g\)\{.*?\n\}\n', js, re.S)
    assert fn, 'tipSet is not findable -- re-anchor this guard'
    r = subprocess.run([NODE, '-e', fn.group(0) + 'console.log(JSON.stringify(%s.map(tipSet)));' % json.dumps(games)],
                       capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_only_espns_false_reads_tbd():
    assert tip_set([{'start': OPENING, 'tv': True},                  # opening night's real 3 PM
                    {'start': '2026-12-25T17:00:00Z', 'tv': True},   # Christmas noon
                    {'start': '2026-10-20T23:00:00Z', 'tv': False},  # an evening ESPN has not set
                    {'start': OPENING},                              # a file from before the flag
                    {'start': None, 'tv': True}]) == [True, True, False, True, False]


def test_the_row_the_card_and_the_note_all_use_it():
    js = JS.read_text(encoding='utf-8')
    row = js[js.index('function rowTime(g, p){'):]
    assert "  return tipSet(g) ? FMT_HOUR.format(new Date(g.start)) : 'time TBD';\n" in row[:300]
    label = js[js.index('function startLabel(g){'):]
    # " ET" is startMark()'s, the time-zone setting's (Stage 80 item 57).
    assert "return tipSet(g) ? `${day} · ${FMT_TIME.format(new Date(g.start))}${startMark()}` : `${day} · time TBD`;" in label[:300]
    note = js[js.index('function preseasonHtml(){'):js.index('function stateHtml(')]
    assert "tipSet(FIRST_GAME) ?" in note and 'its tip-off time still to be set' in note
    assert 'FMT_ET_WEEKDAY_HOUR' not in js, 'the hour rule is back'


def test_the_browser_check_runs():
    wf = (ROOT / '.github' / 'workflows' / 'browser-checks.yml').read_text(encoding='utf-8')
    assert 'run: python tests/browser/check_nba_tip.py --self-test --tmp "$RUNNER_TEMP/tip"\n' in wf
    assert 'run: python tests/browser/check_nba_tip.py "$RUNNER_TEMP/states/nba.html"\n' in wf


def test_the_home_page_lists_the_unset_starts(tmp_path):
    folder = tmp_path / 'results' / 'nba'
    folder.mkdir(parents=True)
    games = [{'game_id': '1', 'start_utc': OPENING, 'game_type': 'regular', 'status': 'scheduled', 'time_valid': True},
             {'game_id': '2', 'start_utc': '2026-10-20T23:00:00Z', 'game_type': 'regular', 'status': 'scheduled',
              'time_valid': False},
             {'game_id': '3', 'start_utc': '2026-10-21T01:30:00Z', 'game_type': 'regular', 'status': 'scheduled'}]
    (folder / 'schedule_2026.json').write_text(json.dumps({'as_of': '2026-10-15', 'games': games}), encoding='utf-8')
    f = home_py.nba_facts(tmp_path, pd.Timestamp('2026-10-15T12:00:00Z').to_pydatetime())
    assert f['unset'] == ['2026-10-20T23:00:00Z']


def test_the_home_page_reads_them_the_same_way():
    """The home page printed opening night as "First tip-off Tue · time TBD"."""
    if not NODE:
        pytest.skip('node not available')
    js = HOME.read_text(encoding='utf-8')
    unset = re.search(r'^const UNSET_TIPS = .*$', js, re.M)
    fn = re.search(r'^function tipSet\(t\)\{.*\}$', js, re.M)
    assert unset and fn, 'the home page has no tipSet -- re-anchor this guard'
    starts = [OPENING, '2026-10-20T23:00:00Z', '2026-12-25T17:00:00Z']
    code = ('const HOME = {nba: {unset: ["2026-10-20T23:00:00Z"]}};\n' + unset.group(0) + '\n' + fn.group(0)
            + '\nconsole.log(JSON.stringify(%s.map(s => tipSet(Date.parse(s)))));' % json.dumps(starts))
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == [True, False, True]
    assert "const PLACEHOLDER_TIMES = {'tip-off': [tipClock, tipWhen]};" in js, 'the NBA card\'s day rows'
    assert "[['First tip-off', tipWhen(first)]]" in js, 'the NBA card before its first pick'
    assert "s === 'nba' ? (tonight ? tipClock(t) : tipWhen(t))" in js, 'the next-game line'
