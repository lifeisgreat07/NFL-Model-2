"""
Stage 75 item 2 (the 2026-10-13 UI/UX audit): a day-board row and its card
print the same pick.

Inside EVEN_BAND the NHL's and NBA's cards said "Too close to call · saved
pick TOR" while the row said "TOR 51%". Both now print "TOR 51% · even",
from one function, pickText. tests/browser/check_row_card.py compares them
on the NHL's sample page; the NBA has no pick to compare until opening
night, so this holds the rule in both sources: the row's pick comes from
pickText, the card's close-game headline does too, and pickText uses the
same EVEN_BAND test as the card's side().

Run with: pytest tests/test_row_card_agree.py -v
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BOARDS = {sport: REPO / 'src' / 'sports' / sport / 'pages' / f'{sport}.js' for sport in ('nhl', 'nba')}


def function(src, name):
    start = src.index(f'function {name}(')
    return src[start:src.index('\n}\n', start) + 2]


@pytest.mark.parametrize('sport', sorted(BOARDS))
def test_the_row_prints_pick_text(sport):
    body = function(BOARDS[sport].read_text(encoding='utf-8'), 'rowPick')
    assert 'pickText(g, p)' in body and '%' not in body.replace('pickText', ''), body


@pytest.mark.parametrize('sport', sorted(BOARDS))
def test_the_cards_close_game_headline_prints_pick_text(sport):
    src = BOARDS[sport].read_text(encoding='utf-8')
    assert 'Too close to call' not in src, sport
    assert '<b>${pickText(g, p).replace(\' · even\', \'\')}</b> <span class="card-hl-to">· even</span>' in src


@pytest.mark.parametrize('sport', sorted(BOARDS))
def test_even_means_what_the_card_means_by_it(sport):
    src = BOARDS[sport].read_text(encoding='utf-8')
    assert 'if(Math.abs(pHome - 50) < EVEN_BAND)' in function(src, 'side')
    assert re.search(r'Math\.abs\(lead \* 100 - 50\) < EVEN_BAND \? \' · even\'', function(src, 'pickText'))


def test_the_browser_check_runs_on_the_nhl_page():
    wf = (REPO / '.github' / 'workflows' / 'browser-checks.yml').read_text(encoding='utf-8')
    assert 'python tests/browser/check_row_card.py --self-test' in wf
    assert 'python tests/browser/check_row_card.py "$RUNNER_TEMP/states/nhl.html"' in wf
