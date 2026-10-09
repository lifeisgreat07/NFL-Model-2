"""Stage 62.2: each sport's icon at the top left of its page and on its home card.

Mark chose puck P3 and ball B2 from the "Sportalytics Icons and Wordmark"
canvas (2026-10-09). They are drawn as the NFL's football is: outline only,
1.4 stroke on a 20-unit grid, tilted -28 degrees. Each page draws its icon
twice, in the sidebar and in the phone's top bar, and the home page draws
all three on the cards. These tests hold every copy to the same drawing.

Run with: pytest tests/test_sport_icons.py -v
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    'nfl': ROOT / 'src' / 'dashboard' / 'body.html',
    'nhl': ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'body.html',
    'nba': ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'body.html',
}
HOME_JS = ROOT / 'src' / 'site' / 'home' / 'home.js'

#: The drawing's defining marks, as on the canvas.
MARKS = {
    'nfl': ['rotate(-28 10 10)', 'cx="10" cy="10" rx="8.6" ry="5.2"'],
    'nhl': ['rotate(-28 10 10)', 'cx="10" cy="8.4" rx="8.4" ry="3.2"', 'M1.6 8.4v3.2a8.4 3.2 0 0 0 16.8 0V8.4'],
    'nba': ['rotate(-28 10 10)', 'cx="10" cy="10" r="8.4"',
            'M10 1.6v16.8M1.6 10h16.8M4.1 4c2.5 2.3 3 9.2 0 12M15.9 4c-2.5 2.3-3 9.2 0 12'],
}


def brand_svgs(sport):
    html = PAGES[sport].read_text(encoding='utf-8')
    return re.findall(r'<svg class="brand-ball".*?</svg>', html, re.S)


@pytest.mark.parametrize('sport', ['nfl', 'nhl', 'nba'])
def test_the_page_draws_its_icon_in_the_sidebar_and_the_top_bar(sport):
    svgs = brand_svgs(sport)
    assert len(svgs) == 2, f'{sport}: expected the sidebar and the top bar, found {len(svgs)}'
    for svg in svgs:
        for mark in MARKS[sport]:
            assert mark in svg, f'{sport}: {mark!r} missing from {svg[:80]!r}'


def test_the_placeholders_are_gone():
    nhl, nba = ''.join(brand_svgs('nhl')), ''.join(brand_svgs('nba'))
    assert 'cx="10" cy="11.5" rx="8" ry="3.4"' not in nhl, 'the stacked-ellipse placeholder puck is back'
    assert 'r="8"/>' not in nba, 'the bare-circle placeholder ball is back'


def test_the_ball_seams_have_no_fill():
    css = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
    rule = re.search(r'\.brand-ball \.lace\{([^}]*)\}', css).group(1)
    assert 'fill:none' in rule, "the ball's curved seams would fill solid black"


def home_icon(sport):
    js = HOME_JS.read_text(encoding='utf-8')
    block = re.search(r'const ICON_PARTS = \{(.*?)\n\};', js, re.S).group(1)
    entry = re.search(rf'\n  {sport}: (.*?)(?=\n  [a-z]+: |\Z)', block, re.S)
    assert entry, f'no home icon for {sport}'
    return entry.group(1)


@pytest.mark.parametrize('sport', ['nfl', 'nhl', 'nba'])
def test_each_home_card_draws_the_same_icon_as_the_page(sport):
    drawn = home_icon(sport)
    for mark in MARKS[sport]:
        assert mark in drawn, f'{sport} home card: {mark!r} missing'


def test_the_card_puts_the_icon_beside_the_sport_name():
    js = HOME_JS.read_text(encoding='utf-8')
    assert '<span class="home-sport">${icon(sport)}${esc(name)}</span>' in js
    assert 'aria-hidden="true"' in re.search(r'function icon\(sport\)\{.*?\n\}', js, re.S).group(0), (
        'the icon repeats the name beside it, so a screen reader must skip it')
