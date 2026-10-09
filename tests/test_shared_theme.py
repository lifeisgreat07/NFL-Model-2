"""One light/dark choice for the whole site (Stage 62 items 1 and 4).

From Stage 53 to Stage 62 each page kept its theme under its own key
('nfl_pickem_theme', 'nhl:theme', 'nba:theme') and the home page kept none,
so a visitor who chose light on one page met dark on the next. Mark,
2026-10-09: the choice is the site's. Every page now reads and writes
`site:theme`, the one entry in src/core/isolation.py's SHARED_STORAGE_KEYS,
the named exception to the rule that a sport's storage keys start with its
code.

This file holds the source: the exception is that one key and lets nothing
else through; every page's first-paint script reads it; every theme button
writes it and nothing else. tests/browser/check_theme.py holds the behaviour
in a browser (it proves itself first with --self-test), run by
.github/workflows/browser-checks.yml over the whole built site.
"""
import re
from pathlib import Path

import pytest

from src.core import isolation

ROOT = Path(__file__).resolve().parents[1]
KEY = 'site:theme'

#: Each page's first-paint script, and the key it read before Stage 62 (read
#: second, so a returning visitor keeps the choice they made). The home page
#: had no key.
FIRST_PAINT = {
    'src/dashboard/page.html': 'nfl_pickem_theme',
    'src/sports/nhl/pages/page.html': 'nhl:theme',
    'src/sports/nba/pages/page.html': 'nba:theme',
    'src/site/home/page.html': None,
}
#: Each page's theme button code.
BUTTONS = ('src/dashboard/app.js', 'src/sports/nhl/pages/nhl.js', 'src/sports/nba/pages/nba.js')
SET_ITEM = re.compile(r'''localStorage\.setItem\(\s*([^,]+?)\s*,''')


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def test_the_one_shared_key_is_the_theme():
    assert set(isolation.SHARED_STORAGE_KEYS) == {KEY}, (
        'a key shared between sports needs its own decision; the theme is the only one made')
    assert isolation.SHARED_STORAGE_KEYS[KEY].strip(), 'the exception carries its reason'


@pytest.mark.parametrize('rel', sorted(FIRST_PAINT))
def test_every_page_reads_the_shared_key_before_first_paint(rel):
    # The first-paint script is the first inline one that sets the theme.
    scripts = [s for s in re.findall(r'<script>(.*?)</script>', read(rel), re.S)
               if "setAttribute('data-theme','light')" in s]
    assert scripts, f'{rel} has no first-paint script'
    body = scripts[0]
    old = FIRST_PAINT[rel]
    if old is None:
        assert f"localStorage.getItem('{KEY}')" in body, f'{rel} does not read {KEY}'
    else:
        assert f"localStorage.getItem('{KEY}') || localStorage.getItem('{old}')" in body, (
            f'{rel} must read {KEY} first, then {old} for a choice made before Stage 62')


@pytest.mark.parametrize('rel', BUTTONS)
def test_every_theme_button_writes_the_shared_key(rel):
    src = read(rel)
    # The button's handler is the code from the first theme-button selector
    # to the end of its addEventListener call.
    start = src.index("document.querySelectorAll('#theme-toggle, .topbar-theme')")
    handler = src[start:src.index('}));', start)]
    keys = SET_ITEM.findall(handler)
    assert keys, f'{rel}: the theme button stores nothing'
    for k in keys:
        if not k.startswith(("'", '"')):
            name = k
            m = re.search(rf'''\b{re.escape(name)}\s*=\s*(['"])(.+?)\1''', src)
            assert m, f'{rel}: {name} is not a string constant'
            k = repr(m.group(2))
        assert k.strip('\'"') == KEY, f'{rel}: the theme button writes {k}, not {KEY!r}'


def test_no_page_writes_a_theme_key_of_its_own():
    """A page that went back to its own key would split the choice again,
    while still reading the shared one and passing the first-paint test."""
    for rel in BUTTONS + tuple(FIRST_PAINT):
        for m in re.finditer(r'''setItem\(\s*(['"])([^'"]*theme[^'"]*)\1''', read(rel)):
            assert m.group(2) == KEY, f'{rel} writes {m.group(2)!r}'


def test_the_exception_lets_only_its_own_key_through(tmp_path):
    js = tmp_path / 'src' / 'sports' / 'nhl' / 'page' / 'app.js'
    js.parent.mkdir(parents=True)
    js.write_text(f"localStorage.setItem('{KEY}', 'x');\nlocalStorage.setItem('theme', 'x');\n"
                  "localStorage.getItem('site:picks');\n", encoding='utf-8')
    found = isolation.name_violations(tmp_path)
    assert len(found) == 2, found
    assert any("'theme'" in f for f in found) and any("'site:picks'" in f for f in found), found
