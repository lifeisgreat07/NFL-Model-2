"""Small things the pages now say the same way (Stage 68 item 18c: U16, U17, U18, U20, U28).

Run with: pytest tests/test_one_product_details.py -v
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGES = {'nfl': 'src/dashboard/body.html', 'home': 'src/site/home/page.html',
         'nhl': 'src/sports/nhl/pages/body.html', 'nba': 'src/sports/nba/pages/body.html'}


def text(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


@pytest.mark.parametrize('page', PAGES)
def test_every_theme_button_has_a_sun_and_a_moon(page):
    t = text(PAGES[page])
    assert t.count('class="icon-sun"') == t.count('class="icon-moon"') >= 1
    css = text('src/dashboard/styles.css')
    assert '[data-theme="light"] .icon-sun{display:none;}' in css and '.icon-moon{display:none;}' in css


def test_the_nhl_teams_page_sits_with_standings_and_ratings():
    t = text(PAGES['nhl'])
    order = [m.group(1) for m in re.finditer(r'data-page="(\w+)"|nav-group-label">([^<]+)<', t) if m.group(1)]
    labels = [m.group(1) for m in re.finditer(r'nav-group-label">([^<]+)<', t)]
    side = t[t.index('class="side-nav"'):t.index('</nav>', t.index('class="side-nav"'))]
    this_week = side[side.index('This Week'):side.index('Track Record')]
    assert 'data-page="teams"' in this_week and labels[:2] == ['This Week', 'Track Record'] and order


@pytest.mark.parametrize('sport', ('nhl', 'nba'))
def test_the_foot_says_when_in_et_and_the_board_says_which_model_picks(sport):
    js = text(f'src/sports/{sport}/pages/{sport}.js')
    assert "document.getElementById('built-line').textContent = `Updated ${" in js and "} ET`;" in js
    assert 'The pick is Model B&#39;s when the market posted a price, and Model A&#39;s when it did not.' in text(PAGES[sport])


def test_the_nfl_lock_proof_reads_in_et():
    js = text('src/dashboard/app.js')
    body = js[js.index('function lockUtc('):js.index('function lockCommitLink(')]
    assert "timeZone: 'America/New_York'" in body and "' ET'" in body and 'UTC' not in body.split('{', 1)[1]
