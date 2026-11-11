"""The day boards share one copy of what they have in common (Stage 87 item 1).

The NHL's and NBA's pages carried 29 byte-identical top-level functions, one
copy in each sport's script, so a fix to one board could miss the other.
They live in src/core/day_board.js, which both pages include ahead of their
own script in the same <script> element.

Run with: pytest tests/test_day_board.py -v
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / 'src' / 'core' / 'day_board.js'
FN = re.compile(r'^function (\w+)\(.*?\n\}\n', re.S | re.M)


def functions(path):
    return {m.group(1): m.group(0) for m in FN.finditer(path.read_text(encoding='utf-8').replace('\r\n', '\n'))}


def own(sport):
    return functions(ROOT / 'src' / 'sports' / sport / 'pages' / f'{sport}.js')


def test_no_function_is_copied_between_the_day_boards():
    nhl, nba = own('nhl'), own('nba')
    copied = sorted(n for n in nhl if n in nba and nhl[n] == nba[n])
    assert copied == [], f'move these to src/core/day_board.js: {copied}'


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_no_sport_redefines_a_shared_function(sport):
    shared = set(functions(BOARD))
    assert len(shared) >= 20, 'the shared script holds the boards\' common functions'
    assert sorted(shared & set(own(sport))) == [], 'a second definition would replace the shared one on that page'


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_each_page_includes_it_ahead_of_its_own_script(sport):
    page = (ROOT / 'src' / 'sports' / sport / 'pages' / 'page.html').read_text(encoding='utf-8').replace('\r\n', '\n')
    assert '{% include "day_board.js" %}\n{% include "' + sport + '.js" %}' in page
    site = (ROOT / 'src' / 'sports' / sport / 'site.py').read_text(encoding='utf-8')
    assert "'day_board.js': DAY_BOARD_JS" in site
