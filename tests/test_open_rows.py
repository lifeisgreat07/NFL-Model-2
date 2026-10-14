"""
Stage 75 item 4 (the 2026-10-13 UI/UX audit): rows the reader opened stay
open when the NHL's or NBA's board is drawn again.

The theme toggle and a day chip redraw the board, and every open row
closed (2 open to 0, measured). tests/browser/check_open_rows.py measures
the NHL's sample page; the NBA has no rows to open until opening night, so
this holds both sources: one set of open rows by card id, filled and
emptied by the row's click, and read back by renderBoard before any click
handler is bound.

Run with: pytest tests/test_open_rows.py -v
"""
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BOARDS = {sport: REPO / 'src' / 'sports' / sport / 'pages' / f'{sport}.js' for sport in ('nhl', 'nba')}


def render_board(src):
    start = src.index('function renderBoard(){')
    return src[start:src.index('\n}\n', start)]


@pytest.mark.parametrize('sport', sorted(BOARDS))
def test_the_board_keeps_one_set_of_open_rows(sport):
    src = BOARDS[sport].read_text(encoding='utf-8')
    assert src.count('const OPEN_ROWS = new Set();') == 1
    assert src.index('const OPEN_ROWS = new Set();') < src.index('function renderBoard(){')


@pytest.mark.parametrize('sport', sorted(BOARDS))
def test_a_click_records_the_row_and_a_redraw_restores_it(sport):
    body = render_board(BOARDS[sport].read_text(encoding='utf-8'))
    restore = body.index("if(!OPEN_ROWS.has(btn.getAttribute('aria-controls'))) return;")
    click = body.index(f"grid.querySelectorAll('.{sport}-row').forEach(btn => btn.addEventListener('click'")
    assert restore < click, 'the rows are restored before the click handlers are bound'
    assert 'if(open) OPEN_ROWS.add(id); else OPEN_ROWS.delete(id);' in body[click:]


def test_the_browser_check_runs():
    wf = (REPO / '.github' / 'workflows' / 'browser-checks.yml').read_text(encoding='utf-8')
    assert 'python tests/browser/check_open_rows.py --self-test' in wf
    assert 'python tests/browser/check_open_rows.py "$RUNNER_TEMP/states/nhl.html"' in wf
