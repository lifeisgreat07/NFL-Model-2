"""A placeholder tip time is not printed as a time (Stage 77 item 33, the 2026-10-13 UI/UX audit's B5).

ESPN files a game whose tip-off is not set at a placeholder hour, and the
board printed opening night's BOS at DET as "3:00 PM" from 19:00Z. A
weekday tip before 5 PM Eastern now reads "time TBD" on the row, in the
card and in the pre-season note, and on the home page's NBA card and its
next-game line; a weekend afternoon game keeps its time.
tipSet runs here under node; tests/browser/check_nba_tip.py reads the rows.

Run with: pytest tests/test_nba_tip_time.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js'
NODE = shutil.which('node')


def tip_set(starts):
    if not NODE:
        pytest.skip('node not available')
    js = JS.read_text(encoding='utf-8')
    fmt = re.search(r'^const FMT_ET_WEEKDAY_HOUR = .*$', js, re.M)
    fn = re.search(r'function tipSet\(g\)\{.*?\n\}\n', js, re.S)
    assert fmt and fn, 'tipSet is not findable -- re-anchor this guard'
    code = ("const ET = 'America/New_York';\n" + fmt.group(0) + '\n' + fn.group(0)
            + 'console.log(JSON.stringify(%s.map(s => tipSet({start: s}))));' % json.dumps(starts))
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_a_weekday_afternoon_is_a_placeholder_and_an_evening_or_a_weekend_is_not():
    starts = ['2026-10-20T19:00:00Z',   # Tue 3:00 PM EDT: opening night's placeholder
              '2026-10-20T23:00:00Z',   # Tue 7:00 PM EDT
              '2026-10-21T01:30:00Z',   # Tue 9:30 PM EDT, the next day in UTC
              '2026-10-24T19:30:00Z',   # Sat 3:30 PM EDT: a real matinee
              '2026-10-25T17:00:00Z',   # Sun 1:00 PM EDT
              '2026-12-02T20:00:00Z',   # Wed 3:00 PM EST
              '2026-12-02T22:00:00Z']   # Wed 5:00 PM EST: evening starts at 5
    assert tip_set(starts) == [False, True, True, True, True, False, True]


def test_the_row_the_card_and_the_note_all_use_it():
    js = JS.read_text(encoding='utf-8')
    row = js[js.index('function rowTime(g){'):]
    assert "  return tipSet(g) ? FMT_HOUR.format(new Date(g.start)) : 'time TBD';\n" in row[:300]
    label = js[js.index('function startLabel(g){'):]
    assert "return tipSet(g) ? `${day} · ${FMT_TIME.format(new Date(g.start))} ET` : `${day} · time TBD`;" in label[:300]
    note = js[js.index('function preseasonHtml(){'):js.index('function stateHtml(')]
    assert "tipSet(FIRST_GAME) ?" in note and 'its tip-off time still to be set' in note


def test_the_browser_check_runs():
    wf = (ROOT / '.github' / 'workflows' / 'browser-checks.yml').read_text(encoding='utf-8')
    assert 'run: python tests/browser/check_nba_tip.py --self-test --tmp "$RUNNER_TEMP/tip"\n' in wf
    assert 'run: python tests/browser/check_nba_tip.py "$RUNNER_TEMP/states/nba.html"\n' in wf


HOME = ROOT / 'src' / 'site' / 'home' / 'home.js'


def test_the_home_page_reads_a_placeholder_the_same_way():
    """The home page printed the same placeholder: "First tip-off Tue 3:00 PM"."""
    if not NODE:
        pytest.skip('node not available')
    js = HOME.read_text(encoding='utf-8')
    fmt = re.search(r'^const ET_WEEKDAY_HOUR = .*$', js, re.M)
    fn = re.search(r'function tipSet\(t\)\{.*?\n\}\n', js, re.S)
    assert fmt and fn, 'the home page has no tipSet -- re-anchor this guard'
    starts = ['2026-10-20T19:00:00Z', '2026-10-20T23:00:00Z', '2026-10-24T19:30:00Z', '2026-12-02T20:00:00Z']
    code = fmt.group(0) + '\n' + fn.group(0) + 'console.log(JSON.stringify(%s.map(s => tipSet(Date.parse(s)))));' % json.dumps(starts)
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == tip_set(starts) == [False, True, True, False]
    assert "const PLACEHOLDER_TIMES = {'tip-off': [tipClock, tipWhen]};" in js, 'the NBA card\'s day rows'
    assert "[['First tip-off', tipWhen(first)]]" in js, 'the NBA card before its first pick'
    assert "s === 'nba' ? (tonight ? tipClock(t) : tipWhen(t))" in js, 'the next-game line'
