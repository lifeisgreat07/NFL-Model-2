"""The NHL board's column at 1280 px and wider (Stage 68 item 37, option C1, Mark 2026-10-10).

Run with: pytest tests/test_nhl_side_column.py -v
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / 'src' / 'sports' / 'nhl' / 'pages'


def test_the_column_is_beside_the_board_and_only_at_1280():
    body = (PAGES / 'body.html').read_text(encoding='utf-8')
    wrap = body[body.index('<div class="nhl-board-wrap">'):]
    assert wrap.index('id="game-grid"') < wrap.index('<aside class="nhl-side" id="nhl-side"')
    css = (PAGES / 'nhl.css').read_text(encoding='utf-8').replace('\r\n', '\n')
    assert '.nhl-side{display:none;}\n@media (min-width:1280px){' in css
    assert 'grid-template-columns:minmax(0, 760px) 300px;' in css


def test_it_follows_the_selected_day():
    js = (PAGES / 'nhl.js').read_text(encoding='utf-8')
    board = js[js.index('function renderBoard('):js.index('function stepWeek(')]
    assert 'side.innerHTML = sideHtml(currentDay, byDay);' in board
    side = js[js.index('function sideHtml('):js.index('const ALL_BY_DAY')]
    for part in ('goalieText(g.away, gl.away)', "p.result === 'correct' || p.result === 'wrong'", 'odds(t.playoff_pct)',
                 'data-page="standings"'):
        assert part in side, part
