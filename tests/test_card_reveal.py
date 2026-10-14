"""
Stage 75 item 3 (the 2026-10-13 UI/UX audit): an opened card is brought on
screen, and the NFL phone card does not repeat its row's header.

tests/browser/check_card_reveal.py measures it on the NFL page and the NHL's
sample page. The NBA has no card until opening night, so this holds the
source: every board's row handler calls revealOpened on open, revealOpened
asks for the nearest scroll, and the stylesheet keeps the cards' scroll
margin and hides the phone card's repeated header.

Run with: pytest tests/test_card_reveal.py -v
"""
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BOARDS = {
    'nfl': REPO / 'src' / 'dashboard' / 'app.js',
    'nhl': REPO / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js',
    'nba': REPO / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js',
}
STYLES = (REPO / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')


@pytest.mark.parametrize('sport', sorted(BOARDS))
def test_opening_a_row_reveals_its_card(sport):
    src = BOARDS[sport].read_text(encoding='utf-8')
    assert src.count('if(open) revealOpened(card);') == 1, sport
    helper = src[src.index('function revealOpened(panel){'):]
    helper = helper[:helper.index('\n}\n')]
    assert "block: 'nearest'" in helper and "prefers-reduced-motion: reduce" in helper, sport


@pytest.mark.parametrize('sheet, selector', [
    ('src/dashboard/styles.css', '.game-card.nfl-collapsible'),
    ('src/sports/nhl/pages/nhl.css', '.nhl-row-detail'),
    ('src/sports/nba/pages/nba.css', '.nba-row-detail'),
])
def test_the_cards_clear_the_top_bar_and_the_bottom_nav(sheet, selector):
    css = (REPO / sheet).read_text(encoding='utf-8')
    assert f'{selector}{{scroll-margin:76px 0 calc(88px + var(--safe-bottom));}}' in css


def test_the_nfl_phone_card_drops_the_rows_header():
    assert '#game-grid .game-card.nfl-collapsible > .matchup-header{display:none;}' in STYLES


def test_the_browser_check_runs():
    wf = (REPO / '.github' / 'workflows' / 'browser-checks.yml').read_text(encoding='utf-8')
    assert 'python tests/browser/check_card_reveal.py --self-test' in wf
    assert 'python tests/browser/check_card_reveal.py index.html "$RUNNER_TEMP/states/nhl.html"' in wf
