"""A game under way says Live, not Locked (Stage 77 item 25, the 2026-10-13 UI/UX audit's copy row 14).

On the NHL board for 2026-10-13 eight games the last run caught mid-game
read "Live | NJD @ DET | NJD 51% | Locked": the time cell said Live and the
status cell said Locked. The status cell now says Live on a picked game
under way, and the time cell keeps the start time instead of saying Live a
second time; a game under way with no pick still says Live in its time cell
and "No pick" in its status. The live score waits for the daily run to
write one (Stage 80 item 61). Both sports' row functions run here under node.

Run with: pytest tests/test_live_row.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')
START = '2026-10-13T22:00:00Z'
STUBS = ("const ET = 'America/New_York';\n"
         "const FMT_HOUR = new Intl.DateTimeFormat('en-US', {hour: 'numeric', minute: '2-digit', timeZone: ET});\n"
         "const lockRunFor = () => null; const LOCK_SLACK_MS = 0;\n"
         "const beforeLaunch = () => false; const tipSet = () => true;\n")


def rows(sport, games):
    if not NODE:
        pytest.skip('node not available')
    js = (ROOT / 'src' / 'sports' / sport / 'pages' / f'{sport}.js').read_text(encoding='utf-8')
    res = re.search(r'function rowResult\(g, p, nowMs\)\{.*?\n\}\n', js, re.S)
    tim = re.search(r'function rowTime\(g, p\)\{.*?\n\}\n', js, re.S)
    assert res and tim, f'the {sport} row functions are not findable -- re-anchor this guard'
    code = (STUBS + res.group(0) + tim.group(0)
            + 'console.log(JSON.stringify(%s.map(([g, p]) => [rowTime(g, p), rowResult(g, p, 0)])));'
            % json.dumps(games))
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_a_picked_game_under_way_says_live_once(sport):
    out = rows(sport, [[{'status': 'in_progress', 'start': START}, {'result': 'pending'}]])
    assert out == [['6:00 PM', {'text': 'Live', 'cls': 'live'}]]


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_an_unpicked_game_under_way_and_the_other_states_are_unchanged(sport):
    out = rows(sport, [[{'status': 'in_progress', 'start': START}, None],
                       [{'status': 'scheduled', 'start': START}, {'result': 'pending'}],
                       [{'status': 'final', 'start': START}, {'result': 'pending'}]])
    assert [o[0] for o in out][:2] == ['Live', '6:00 PM']
    assert [o[1]['text'] for o in out] == ['No pick', 'Locked', 'Grading']


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_live_wears_the_accent(sport):
    css = (ROOT / 'src' / 'sports' / sport / 'pages' / f'{sport}.css').read_text(encoding='utf-8')
    # Since Stage 78 item 38 Live alone keeps the accent; Locked went quiet.
    assert f'.{sport}-row-result.live{{color:var(--accent);}}' in css
