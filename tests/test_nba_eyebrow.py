"""The NBA board's eyebrow names the week it shows (Stage 77 item 32, the 2026-10-13 UI/UX audit's B1).

It said "This Week" over "Week of Oct 19" on the 13th: the board opens on
the week of the first games before opening night, and the eyebrow was fixed
text. weekEyebrow runs here under node; tests/browser/check_nba_eyebrow.py
drives the page with the clock fixed.

Run with: pytest tests/test_nba_eyebrow.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NBA = ROOT / 'src' / 'sports' / 'nba' / 'pages'
NODE = shutil.which('node')


def eyebrows(pairs):
    if not NODE:
        pytest.skip('node not available')
    js = NBA.joinpath('nba.js').read_text(encoding='utf-8')
    # dayDate and dayIso are one line each; weekEyebrow runs to its closing brace.
    helpers = ''.join(line + '\n' for line in js.splitlines() if re.match(r'function (dayDate|dayIso)\(', line))
    eyebrow = re.search(r'function weekEyebrow\(.*?\n\}\n', js, re.S)
    assert helpers.count('function ') == 2 and eyebrow, 'the helpers are not findable -- re-anchor this guard'
    code = helpers + eyebrow.group(0) + 'console.log(JSON.stringify(%s.map(([w, t]) => weekEyebrow(w, t))));' % json.dumps(pairs)
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_the_eyebrow_says_which_week_it_is():
    assert eyebrows([['2026-10-12', '2026-10-12'], ['2026-10-19', '2026-10-12'], ['2026-10-26', '2026-10-12'],
                     ['2026-10-05', '2026-10-12'], ['2027-01-04', '2026-12-28']]) == [
        'This Week', 'Next Week', 'Coming Up', 'Earlier', 'Next Week']


def test_the_board_writes_it_every_time_it_draws():
    js = NBA.joinpath('nba.js').read_text(encoding='utf-8')
    body = js[js.index('function renderBoard(){'):]
    assert "document.querySelector('#page-board .page-eyebrow').textContent = weekEyebrow(currentWeek, mondayOf(todayEt()));" in body
    # The eyebrow keeps its plain markup, which tests/test_page_header_sports.py reads.
    assert '<div class="page-eyebrow">This Week</div>' in NBA.joinpath('body.html').read_text(encoding='utf-8')


def test_the_browser_check_runs():
    wf = (ROOT / '.github' / 'workflows' / 'browser-checks.yml').read_text(encoding='utf-8')
    assert 'run: python tests/browser/check_nba_eyebrow.py --self-test --tmp "$RUNNER_TEMP/eyebrow"\n' in wf
    assert 'run: python tests/browser/check_nba_eyebrow.py "$RUNNER_TEMP/states/nba.html"\n' in wf
