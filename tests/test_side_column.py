"""A column beside the day board at 1280 px and wider (Stage 79 item 48, the 2026-10-13 UI/UX audit's B3 and L3).

The NBA gets the NHL's column (Stage 68 item 37): who is out for each game
with a saved pick, from the injury report that pick read, and the day
before's record; and both columns are capped at the window's height,
scrolling inside. The NBA has no saved picks before opening night, so its
column is run here under node with synthetic ones;
tests/browser/check_side_column.py measures both pages.

Run with: pytest tests/test_side_column.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NBA = ROOT / 'src' / 'sports' / 'nba' / 'pages'
NHL = ROOT / 'src' / 'sports' / 'nhl' / 'pages'
NODE = shutil.which('node')


def side(games, picks, day):
    if not NODE:
        pytest.skip('node not available')
    js = NBA.joinpath('nba.js').read_text(encoding='utf-8')
    one = lambda name: re.search(rf'^function {name}\(.*$', js, re.M).group(0) + '\n'
    fmt = re.search(r'^const FMT_DAY = .*$', js, re.M).group(0) + '\n'
    esc = (ROOT / 'src' / 'core' / 'escape.js').read_text(encoding='utf-8')
    block = re.search(r'^const ALL_BY_DAY = \{\};\n.*?\nfunction sideHtml\(day, byDay\)\{.*?\n\}\n', js, re.S | re.M)
    assert block, 'the column is not findable -- re-anchor this guard'
    code = (esc + one('dayDate') + fmt + 'const BD = %s;\n' % json.dumps({'games': games, 'picks': picks}) + block.group(0)
            + 'const byDay = {}; BD.games.forEach(g => (byDay[g.day] ||= []).push(g));\n'
            + 'console.log(JSON.stringify(sideHtml(%s, byDay)));' % json.dumps(day))
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


GAMES = [{'id': '1', 'day': '2026-10-21', 'away': 'BOS', 'home': 'NY'},
         {'id': '2', 'day': '2026-10-21', 'away': 'LAL', 'home': 'GS'},
         {'id': '3', 'day': '2026-10-20', 'away': 'PHI', 'home': 'DET'}]


def test_who_is_out_comes_from_each_saved_picks_report():
    picks = {'1': {'avail': {'read': True}, 'out': {'away': ["O'Neal"], 'home': []}},
             '2': {'avail': {'read': False}},
             '3': {'result': 'correct'}}
    html = side(GAMES, picks, '2026-10-21')
    assert 'BOS at NY' in html and 'BOS: O&#39;Neal' in html and 'NY: nobody listed out' in html
    assert 'The injury report was not read when this pick was saved.' in html
    assert '<b>1–0</b> on Tuesday, Oct 20' in html


def test_before_a_pick_is_saved_it_says_so():
    html = side(GAMES, {}, '2026-10-21')
    assert 'No pick is saved for this day yet.' in html and 'No graded pick on Tuesday, Oct 20.' in html


def test_the_board_draws_it_and_both_columns_are_capped():
    js = NBA.joinpath('nba.js').read_text(encoding='utf-8')
    body = js[js.index('function renderBoard(){'):]
    assert "  if(side) side.innerHTML = sideHtml(currentDay, byDay);\n" in body
    assert body.index('sideHtml(currentDay, byDay)') < body.index('if(!dayGames.length){'), 'a day with no games gets its column too'
    assert '<aside class="nba-side" id="nba-side" aria-label="This day at a glance"></aside>' in NBA.joinpath('body.html').read_text(encoding='utf-8')
    for path, sel in ((NBA / 'nba.css', '.nba-side{'), (NHL / 'nhl.css', '.nhl-side{')):
        css = path.read_text(encoding='utf-8')
        rule = css[css.index('@media (min-width:1280px){'):]
        rule = rule[rule.index(sel):]
        assert 'max-height:calc(100vh - var(--s8)); overflow:auto;' in rule[:200], path.name


def test_the_browser_check_runs():
    wf = (ROOT / '.github' / 'workflows' / 'browser-checks.yml').read_text(encoding='utf-8')
    assert 'run: python tests/browser/check_side_column.py --self-test --tmp "$RUNNER_TEMP/side"\n' in wf
    assert 'run: python tests/browser/check_side_column.py "$RUNNER_TEMP/states/nba.html" "$RUNNER_TEMP/states/nhl.html"\n' in wf
