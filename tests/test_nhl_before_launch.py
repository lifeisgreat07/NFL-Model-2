"""A game played before the first pick was saved says "Before launch" (Stage 77 item 24, the 2026-10-13 UI/UX audit's copy row 13).

The NHL board's rows for the season's first days read "— | No pick", which
reads as a pick the model skipped. Those games started before the model
saved its first pick at all, so the row now says "Before launch" and its
pick cell is empty; a later game the model did miss still says "No pick".
The functions run here under node against a stand-in for the page's data.

Run with: pytest tests/test_nhl_before_launch.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js'
NODE = shutil.which('node')
FIRST = '2026-10-06T22:07:32Z'


def run(games):
    if not NODE:
        pytest.skip('node not available')
    js = JS.read_text(encoding='utf-8')
    first = re.search(r'^const FIRST_SAVED = .*$', js, re.M)
    pre = re.search(r'function beforeLaunch\(g\)\{.*?\n\}\n', js, re.S)
    res = re.search(r'function rowResult\(g, p, nowMs\)\{.*?\n\}\n', js, re.S)
    pick = re.search(r'function rowPick\(g, p\)\{.*?\n\}\n', js, re.S)
    assert first and pre and res and pick, 'the row functions are not findable -- re-anchor this guard'
    code = ('const DATA = {picks: {x: {saved: %s}, y: {saved: null}}};\n' % json.dumps(FIRST)
            + 'const lockRunFor = () => null; const LOCK_SLACK_MS = 0; const pickText = () => "P";\n'
            + first.group(0) + '\n' + pre.group(0) + res.group(0) + pick.group(0)
            + 'console.log(JSON.stringify(%s.map(g => [rowPick(g, null), rowResult(g, null, 0).text])));'
            % json.dumps(games))
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_a_game_before_the_first_saved_pick_says_before_launch():
    games = [{'status': 'final', 'start': '2026-10-05T23:00:00Z'},
             {'status': 'in_progress', 'start': '2026-10-06T22:00:00Z'}]
    assert run(games) == [['', 'Before launch'], ['', 'Before launch']]


def test_a_game_after_it_without_a_pick_still_says_no_pick():
    games = [{'status': 'final', 'start': '2026-10-06T23:00:00Z'},
             {'status': 'final', 'start': None}]
    assert run(games) == [['—', 'No pick'], ['—', 'No pick']]


def test_the_card_note_reads_the_same_test():
    js = JS.read_text(encoding='utf-8')
    card = js[js.index('function waitingCard(g){'):]
    assert "note = beforeLaunch(g) ? 'Before the first pick was saved.'" in card[:400]
