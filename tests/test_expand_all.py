"""Expand all / Collapse all (Mark's request, 2026-10-15; he chose option B).

Measured 2026-10-15 on the site built from main, at 390 and 1440 px in both
themes: opening every game of a day took a press per row (16 on the NHL's
Tuesday, Oct 13; 15 on the NFL's phone Week 5), and each press scrolled
the page to the card it opened.

Now an outlined button on its own line under the header (the NHL's and
NBA's Day Board at every width; the NFL's phone rows, where a wide screen
already shows every card) opens every shown game at once and then says
Collapse all. src/core/expand.js presses each row as a reader would, so the
page's own handler opens its card and remembers it, and keeps the page
where it was while it does.

Run with: pytest tests/test_expand_all.py -v
"""
import inspect
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.site import build

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'src' / 'core' / 'expand.js').read_text(encoding='utf-8')
SPORT_JS = {s: (ROOT / 'src' / 'sports' / s / 'pages' / f'{s}.js').read_text(encoding='utf-8') for s in ('nhl', 'nba')}
BODY = (ROOT / 'src' / 'dashboard' / 'body.html').read_text(encoding='utf-8')
CSS = re.sub(r'\s+', '', (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8'))
NODE = shutil.which('node')


def node(code):
    if not NODE:
        pytest.skip('node not available')
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def pure():
    return JS[:JS.index('(function(){')]


def rows(states):
    """Pretend rows: shown (offsetParent) and each one's aria-expanded."""
    return ('[' + ','.join(f'{{offsetParent: {"null" if not shown else "{}"}, getAttribute: () => {json.dumps(open_)}}}'
                           for shown, open_ in states) + ']')


def test_the_button_says_expand_until_every_shown_game_is_open():
    got = node(pure() + 'console.log(JSON.stringify(['
               f'expandLabel({rows([(True, "false"), (True, "true")])}),'
               f'expandLabel({rows([(True, "true"), (True, "true")])}),'
               'expandLabel([])]));')
    assert got == ['Expand all', 'Collapse all', 'Expand all']


def test_only_the_rows_shown_count():
    scope = ('{querySelectorAll: () => ' + rows([(True, 'false'), (False, 'false'), (True, 'true')]) + '}')
    assert node(pure() + f'console.log(JSON.stringify(expandRows({scope}).length));') == 2, \
        "the NFL's phone rows are in the page at 1440 too, hidden"


def test_each_row_is_pressed_as_a_reader_would_and_the_page_stays_put():
    run = JS[JS.index('(function(){'):]
    assert "rows.forEach(r => { if((r.getAttribute('aria-expanded') === 'true') !== open) r.click(); });" in run, \
        "the page's own handler opens each card and remembers it"
    assert run.index('Element.prototype.scrollIntoView = function(){};') < run.index('r.click()') \
        < run.index('Element.prototype.scrollIntoView = keep;'), 'no row brings its card on screen while all open'
    assert 'window.scrollTo(x, y);' in run


def test_a_row_pressed_by_hand_keeps_the_word_right():
    run = JS[JS.index('(function(){'):]
    assert "if(e.target.closest && e.target.closest('button.game-row')) setTimeout(sync, 0);" in run
    assert 'new MutationObserver(' in run, 'a board drawn again draws its button afresh'
    assert 'btn.hidden = rows.length < 2;' in run, 'one game needs no button'
    assert "btn.setAttribute('aria-expanded', String(label === 'Collapse all'));" in run


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_a_day_board_has_it_under_its_header(sport):
    src = SPORT_JS[sport]
    assert ("const EXPAND_BAR = '<div class=\"expand-bar\"><button type=\"button\" class=\"btn btn-secondary expand-all\" "
            "data-expand-all aria-expanded=\"false\" hidden>") in src
    board = src[src.index('function renderBoard('):]
    assert board.index('accSummaryHtml(accGames(gradedToday), dayGames.length)\n') < board.index('+ EXPAND_BAR\n') < board.index(f'<ul class="{sport}-rows">')


def test_the_nfl_has_it_on_a_phone_only():
    bar = '<div class="expand-bar nfl-phone-only"><button type="button" class="btn btn-secondary expand-all" data-expand-all'
    assert bar in BODY and BODY.index(bar) < BODY.index('<p class="board-note" id="board-tv-note"') < BODY.index('<div class="game-grid" id="game-grid"></div>')
    assert '.expand-bar.nfl-phone-only{display:none;}' in CSS
    assert '@media(max-width:640px){.expand-bar.nfl-phone-only{display:flex;}}' in CSS
    assert '.share-btn,.fav-star,.expand-bar{display:none!important;}' in CSS, 'not on paper'


def test_the_build_puts_the_script_on_the_sport_pages_with_the_button(tmp_path):
    page = '<html><body><button data-expand-all></button></body></html>'
    for s in ('nfl', 'nhl', 'nba'):
        (tmp_path / s).mkdir()
        (tmp_path / s / 'index.html').write_text(page, encoding='utf-8')
    (tmp_path / 'index.html').write_text(page, encoding='utf-8')
    assert build.add_expand(tmp_path) == ['nfl/index.html', 'nhl/index.html', 'nba/index.html']
    build.add_expand(tmp_path)
    assert (tmp_path / 'nhl' / 'index.html').read_text(encoding='utf-8').count('<script data-site-expand>') == 1
    assert 'data-site-expand' not in (tmp_path / 'index.html').read_text(encoding='utf-8')
    other = tmp_path / 'x.html'
    other.write_text('<html><body>x</body></html>', encoding='utf-8')
    assert not build.inject_expand(other, build.expand_block())
    assert 'add_expand(out)' in inspect.getsource(build.build_site)
