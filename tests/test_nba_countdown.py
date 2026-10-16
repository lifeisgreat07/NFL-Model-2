"""Until the first pick is saved, the NBA's note counts down to it (Stage 80 item 60, the 2026-10-13 UI/UX audit's F17).

The note said "No picks yet" and when, and nothing of how long that was.
It now leads with "First picks lock Tue, Oct 20 — 7 days" (tomorrow, today),
with the clock time only when every opening-night tip-off is set (ESPN's
own flag, nba.js tipSet), since a placeholder tip gives a wrong lock. countdownText runs here under node with
its helpers; tests/browser/check_nba_countdown.py reads the page with the
clock fixed.

Run with: pytest tests/test_nba_countdown.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js').read_text(encoding='utf-8')
NODE = shutil.which('node')


def piece(pattern):
    """One line of the script, or a function to its closing brace when the pattern spans lines."""
    m = re.search(pattern, JS, (re.S if r'\n\}' in pattern else 0) | re.M)
    assert m, f'{pattern!r} is not findable -- re-anchor this guard'
    return m.group(0) + '\n'


def countdown(games, today):
    """countdownText for a schedule of (day, start[, ESPN's time flag]) rows, the first being opening night's."""
    if not NODE:
        pytest.skip('node not available')
    code = ("const ET = 'America/New_York';\nfunction startZone(){ return 'America/New_York'; }\nfunction startMark(){ return ' ET'; }\n"
            + piece(r'^function dayDate\(day\).*$') + piece(r'^const FMT_TIP = .*$')
            + piece(r'^function tipSet\(g\)\{.*?\n\}') + piece(r'^const LOCK_RUNS_UTC = .*$') + piece(r'^const LOCK_SLACK_MS = .*$')
            + piece(r'^function lockRunFor\(startIso\)\{.*?\n\}') + piece(r'^const FMT_LOCK_DAY = .*$')
            + 'const BD = {games: %s.map(([day, start, tv]) => ({day, start, tv}))};\n' % json.dumps(games)
            + "const FIRST_GAME = BD.games[0]; const OPENING_DAY = FIRST_GAME.day;\n"
            + piece(r'^function countdownText\(today\)\{.*?\n\}')
            + 'console.log(JSON.stringify(%s.map(countdownText)));' % json.dumps(today))
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


SET = [['2026-10-20', '2026-10-20T23:00:00Z'], ['2026-10-20', '2026-10-21T01:30:00Z']]   # 7:00 and 9:30 PM ET
PLACEHOLDER = [['2026-10-20', '2026-10-20T19:00:00Z', False], ['2026-10-20', '2026-10-20T23:00:00Z', True]]
#: Opening night as it is: BOS at DET a real 3 PM on NBC, then 7:00 and 9:30 PM ET (all set by ESPN).
OPENING = [['2026-10-20', '2026-10-20T19:00:00Z', True], ['2026-10-20', '2026-10-20T23:00:00Z', True],
           ['2026-10-20', '2026-10-21T01:30:00Z', True]]


def test_it_counts_days_then_tomorrow_then_today_then_stops():
    assert countdown(SET, ['2026-10-13', '2026-10-19', '2026-10-20', '2026-10-21']) == [
        'First picks lock Tue, Oct 20, 5:30 PM ET — 7 days', 'First picks lock Tue, Oct 20, 5:30 PM ET — tomorrow',
        'First picks lock Tue, Oct 20, 5:30 PM ET — today', '']


def test_a_placeholder_tip_gives_the_day_without_a_time():
    assert countdown(PLACEHOLDER, ['2026-10-14']) == ['First picks lock Tue, Oct 20 — 6 days']


def test_a_real_afternoon_tip_gives_its_lock_time():
    """The 3 PM game locks at the noon run (16:00 UTC); the hour rule hid this time."""
    assert countdown(OPENING, ['2026-10-14']) == ['First picks lock Tue, Oct 20, 12:00 PM ET — 6 days']


def test_the_note_leads_with_it_while_there_are_no_picks():
    note = JS[JS.index('function preseasonHtml(){'):JS.index('function stateHtml(')]
    assert "if(Object.keys(BD.picks || {}).length || !FIRST_GAME) return '';" in note
    assert "const countdown = countdownText(todayEt());" in note
    assert '<div class="nba-preseason" role="note">${countdown ? `<p class="nba-countdown">${escapeHtml(countdown)}</p>` : \'\'}' in note


def test_the_browser_check_runs():
    wf = (ROOT / '.github' / 'workflows' / 'browser-checks.yml').read_text(encoding='utf-8')
    assert 'run: python tests/browser/check_nba_countdown.py --self-test --tmp "$RUNNER_TEMP/countdown"\n' in wf
    assert 'run: python tests/browser/check_nba_countdown.py "$RUNNER_TEMP/states/nba.html"\n' in wf
