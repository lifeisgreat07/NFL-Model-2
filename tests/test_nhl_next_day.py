"""An empty NHL day names the next day with games (Stage 77 item 35, the 2026-10-13 UI/UX audit's L6).

A day without games (Friday, Nov 20) read "No games this day." and nothing
else (measured 2026-10-14, 390 and 1440 px, both themes). It now adds
"Next games: Saturday, Nov 21, 14 games" as a button that moves the board
there, writes #board/<that day> and puts focus on its chip. The other
halves of L6 are Stage 77 item 24 (pre-launch rows).

Run with: pytest tests/test_nhl_next_day.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js').read_text(encoding='utf-8')
NODE = shutil.which('node')
GAMES = [{'day': '2026-11-19'}, {'day': '2026-11-21'}, {'day': '2026-11-21'}, {'day': '2026-11-22'}]


def next_day(days):
    if not NODE:
        pytest.skip('node not available')
    fmt = re.search(r'^const FMT_DAY = .*$', JS, re.M).group(0)
    dd = re.search(r'function dayDate\(.*?\n\}\n|^const dayDate = .*$', JS, re.S | re.M).group(0)
    fns = ''.join(re.search(r'function %s\(day\)\{.*?\n\}\n' % n, JS, re.S).group(0) for n in ('nextDay', 'nextDayHtml'))
    code = ('const DATA = {games: %s};\n' % json.dumps(GAMES) + fmt + '\n' + dd + '\n' + fns
            + 'console.log(JSON.stringify(%s.map(d => nextDayHtml(d))));' % json.dumps(days))
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_an_empty_day_names_the_next_day_with_games():
    a, b, c = next_day(['2026-11-20', '2026-11-21', '2026-11-22'])
    assert a == ('<p class="nhl-next-day">Next games: <button type="button" class="btn btn-link" '
                 'data-go-day="2026-11-21">Saturday, Nov 21, 2 games</button></p>')
    assert 'Sunday, Nov 22, 1 game<' in b, 'one game is "1 game"'
    assert c == '', 'after the last day with games there is nothing to name'


def test_the_board_shows_it_on_an_empty_day_and_the_button_goes_there():
    board = JS[JS.index('function renderBoard(){'):]
    empty = board[board.index('  if(!dayGames.length){'):]
    empty = empty[:empty.index('    return;\n  }')]
    assert "grid.innerHTML = head + nextDayHtml(currentDay) + " in empty
    assert "currentDay = go.dataset.goDay;\n      currentWeek = mondayOf(currentDay);\n      renderBoard();\n      replaceRoute('board');" in empty
