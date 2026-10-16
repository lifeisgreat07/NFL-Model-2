"""The phone's More sheet reads as a dialog, and the menu is one skip away (Stage 78 item 43, the 2026-10-13 UI/UX audit's C4).

At 390 px, on every sport, the open More sheet had no scrim and no close
button, and a keyboard reached the bottom menu only after every row (25 Tab
presses on the NFL, 18 on the NHL, 19 on the NBA, measured 2026-10-14). Now
the sheet dims the page behind it (a tap there closes it), carries a close
button that returns focus to More, and a second skip link, "Skip to the
menu", reaches the menu in three presses. On the NHL and NBA a skip link
moves focus itself: followed as a link, its hash reached the router, which
opened the board and added a history entry.

Run with: pytest tests/test_more_sheet.py -v
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BODIES = {'nfl': ROOT / 'src' / 'dashboard' / 'body.html',
          'nhl': ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'body.html',
          'nba': ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'body.html'}
SCRIPTS = {'nfl': ROOT / 'src' / 'dashboard' / 'app.js',
           'nhl': ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js',
           'nba': ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js'}
CSS = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')


@pytest.mark.parametrize('sport', BODIES)
def test_the_sheet_has_a_close_button_and_a_scrim(sport):
    body = BODIES[sport].read_text(encoding='utf-8')
    sheet = body[body.index('<div id="bnav-more-sheet" class="bnav-more-sheet" inert>'):]
    assert sheet.split('\n')[1].strip().startswith('<button type="button" class="bnav-more-close" aria-label="Close the menu">')
    after = sheet[sheet.index('</div>\n</div>') + len('</div>\n</div>'):]
    assert re.match(r'\s*<!--[^>]*-->\s*<div class="bnav-scrim" aria-hidden="true"></div>', after), 'the scrim follows the sheet'


@pytest.mark.parametrize('sport', BODIES)
def test_the_menu_is_one_skip_away(sport):
    body = BODIES[sport].read_text(encoding='utf-8')
    first = body.index('<a href="#main-content" class="skip-link">')
    assert body.index('<a href="#bottom-nav" class="skip-link skip-link-nav">Skip to the menu</a>') < body.index('<main')
    assert body.index('<a href="#bottom-nav"') > first
    assert '<nav class="bottom-nav" id="bottom-nav" tabindex="-1" aria-label="Mobile navigation">' in body


@pytest.mark.parametrize('sport', SCRIPTS)
def test_the_close_button_closes_and_hands_focus_back(sport):
    js = SCRIPTS[sport].read_text(encoding='utf-8')
    hook = re.search(r"querySelector\('#bnav-more-sheet \.bnav-more-close'\).*?\}\);", js, re.S)
    assert hook and 'focus()' in hook.group(0) and ('setMoreSheetOpen(false)' in hook.group(0) or 'closeMoreSheet()' in hook.group(0))


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_a_skip_link_does_not_reach_the_router(sport):
    js = SCRIPTS[sport].read_text(encoding='utf-8')
    hook = js[js.index("document.querySelectorAll('.skip-link').forEach(a => a.addEventListener('click', e => {"):]
    hook = hook[:hook.index('}));')]
    assert 'e.preventDefault();' in hook and 'target.focus();' in hook


def test_the_scrim_shows_only_with_the_sheet_and_the_skip_link_only_with_the_menu():
    assert '.bnav-more-sheet.open + .bnav-scrim{opacity:1; pointer-events:auto;}' in CSS
    assert re.search(r'\.bnav-scrim\{[^}]*opacity:0; pointer-events:none;', CSS)
    assert '  .skip-link-nav{display:none;}' in CSS
    assert '    .bottom-nav{display:block;}\n    .skip-link-nav{display:block;}\n' in CSS
