"""The NBA's chrome says what the NHL's and the NFL's say (Stage 77 item 22, the 2026-10-13 UI/UX audit's B2).

The NBA's phone top bar said "NBA" where the NHL's says "Daily NHL picks,
graded", and its bottom nav said "Method" and "Checks" where the other two
sports keep "Methodology" and "Checking the AI's work" under More; the
full names do not fit a bottom-nav button (120 px of text in an 88 px
button at 390). The NBA now has the same subtitle and the same More sheet.

Run with: pytest tests/test_nba_chrome.py -v
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BODY = {s: (ROOT / 'src' / 'sports' / s / 'pages' / 'body.html').read_text(encoding='utf-8') for s in ('nhl', 'nba')}
NFL_BODY = (ROOT / 'src' / 'dashboard' / 'body.html').read_text(encoding='utf-8')


def labels(html):
    """data-page -> the label each phone-nav control gives it (bottom row and More sheet)."""
    out = {}
    for page, text in re.findall(r'class="bnav-(?:btn|more-item)[^"]*" data-page="([a-z]+)">.*?<span[^>]*>([^<]+)</span>', html):
        out[page] = text
    return out


@pytest.mark.parametrize('sport', ('nhl', 'nba'))
def test_the_top_bar_says_daily_picks_graded(sport):
    assert f'<span class="topbar-sub">Daily {sport.upper()} picks, graded</span>' in BODY[sport]


def test_the_nba_names_each_page_as_the_other_sports_do():
    nba, nhl, nfl = labels(BODY['nba']), labels(BODY['nhl']), labels(NFL_BODY)
    assert nba, 'no phone-nav labels found -- re-anchor this guard'
    for page, text in nba.items():
        known = {d[page] for d in (nhl, nfl) if page in d}
        assert not known or text in known, f'{page} is "{text}" on the NBA, {sorted(known)} elsewhere'
    assert 'Method<' not in BODY['nba'].replace('Methodology<', '') and '>Checks<' not in BODY['nba']


def test_the_long_names_sit_under_more_as_they_do_on_the_nhl():
    for sport in ('nhl', 'nba'):
        sheet = BODY[sport][BODY[sport].index('id="bnav-more-sheet"'):]
        assert 'data-page="method"' in sheet and 'data-page="reliability"' in sheet, sport
        assert 'id="bnav-more-btn"' in BODY[sport], sport
    js = (ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js').read_text(encoding='utf-8')
    assert "const OVERFLOW_PAGES = ['method', 'reliability'];" in js
    show = js[js.index('function showPage(name, opts){'):]
    assert "if(more) more.classList.toggle('active', OVERFLOW_PAGES.includes(name));" in show[:900]
    assert 'setMoreSheetOpen(false);' in show[:900], 'a page change closes the sheet'
    assert "if(moreBtn) moreBtn.addEventListener('click', e => {" in js and "if(e.key === 'Escape') setMoreSheetOpen(false);" in js
