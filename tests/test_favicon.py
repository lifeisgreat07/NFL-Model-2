"""The site's favicon (Stage 29; option B, chosen by Mark 2026-09-29).

There was none, so every tab showed the browser's blank page. The icon is
the sidebar's football on the site's darkest neutral. Three things have to
hold together for it to show: the page links it, the file is there and is
the SVG the link says, and the deploy publishes it at the path the link
names. A link that points nowhere fails silently -- the browser just shows
the blank page again -- so each is checked here rather than by looking.

Since Stage 53 the board is published at nfl/ and the icons at the site
root's assets/ (src/site/build.py's SHARED_FILES), so the links climb one
folder; the published path is where the link lands from nfl/index.html.

Run with: pytest tests/test_favicon.py -v
"""
import posixpath
import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from src.core.template_parts import JOINED_TEMPLATE
from src.site.build import SHARED_FILES

REPO = Path(__file__).resolve().parents[1]
TEMPLATE = JOINED_TEMPLATE
ICON = REPO / 'assets' / 'favicon.svg'
TOUCH = REPO / 'assets' / 'apple-touch-icon.png'
SVG = '{http://www.w3.org/2000/svg}'


def icon_links():
    head = TEMPLATE.read_text(encoding='utf-8').split('</head>')[0]
    return re.findall(r'<link rel="icon" href="([^"]+)" type="([^"]+)">', head)


def test_the_page_links_one_svg_icon_in_its_head():
    links = icon_links()
    assert links == [('../assets/favicon.svg', 'image/svg+xml')], links


def test_the_icon_is_a_square_svg_with_a_dark_tile_and_the_accent_ball():
    root = ET.parse(ICON).getroot()
    assert root.tag == f'{SVG}svg'
    assert root.get('viewBox') == '0 0 32 32', 'the favicon is not square at 32 units'
    tile = root.find(f'{SVG}rect')
    assert tile is not None and tile.get('fill') == '#0B0D10', 'the dark tile is gone'
    ball = root.find(f'.//{SVG}ellipse')
    assert ball is not None and ball.get('fill') == '#7FA8F5', 'the accent football is gone'


def published_at(href):
    """Where a link in the NFL board's head lands on the site."""
    return posixpath.normpath(posixpath.join('nfl', href))


def test_the_deploy_publishes_the_icon_where_the_link_points():
    href = icon_links()[0][0]
    assert SHARED_FILES.get(published_at(href)) == 'assets/favicon.svg', (
        f'src/site/build.py does not publish the favicon at {published_at(href)}, '
        'so the live site links an icon that is not there')


# --- the home-screen icon (Stage 34 item 31) ----------------------------------

def touch_links():
    head = TEMPLATE.read_text(encoding='utf-8').split('</head>')[0]
    return re.findall(r'<link rel="apple-touch-icon" href="([^"]+)">', head)


def png_size(data):
    """(width, height) from a PNG's IHDR, or None if it is not a PNG."""
    if data[:8] != b'\x89PNG\r\n\x1a\n' or data[12:16] != b'IHDR':
        return None
    return int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')


def test_the_page_links_one_home_screen_icon():
    """iOS ignores the SVG favicon; without this link a saved-to-home-screen
    page shows a shrunken screenshot of itself."""
    assert touch_links() == ['../assets/apple-touch-icon.png'], touch_links()


def test_the_home_screen_icon_is_a_180px_png():
    data = TOUCH.read_bytes()
    assert png_size(data) == (180, 180), png_size(data)


def test_the_deploy_publishes_the_home_screen_icon_where_the_link_points():
    href = touch_links()[0]
    assert SHARED_FILES.get(published_at(href)) == 'assets/apple-touch-icon.png', (
        f'src/site/build.py does not publish the home-screen icon at {published_at(href)}')


def test_a_file_that_is_not_a_180px_png_is_caught():
    """Synthetic, so the failing branch stays reachable."""
    assert png_size(b'GIF89a' + b'0' * 30) is None
    fake = b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\x0dIHDR' + (32).to_bytes(4, 'big') * 2
    assert png_size(fake) == (32, 32)


# --- one brand set per sport (Stage 76 item 11) --------------------------------
# The 2026-10-13 audit's C1: one football favicon, one football home-screen
# icon and one "NFL · WEEKLY PICKS" card served all four pages. Each sport
# now has its own (V6), with its sidebar's mark, and the home page's card
# carries the three marks.

SPORT_PAGES = {'nfl': REPO / 'src' / 'dashboard' / 'page.html',
               'nhl': REPO / 'src' / 'sports' / 'nhl' / 'pages' / 'page.html',
               'nba': REPO / 'src' / 'sports' / 'nba' / 'pages' / 'page.html'}
OWN_ICON = {'nfl': 'favicon.svg', 'nhl': 'favicon-nhl.svg', 'nba': 'favicon-nba.svg'}
OWN_TOUCH = {'nfl': 'apple-touch-icon.png', 'nhl': 'apple-touch-icon-nhl.png', 'nba': 'apple-touch-icon-nba.png'}
OG_PAGES = {'home': REPO / 'src' / 'site' / 'home' / 'page.html', **SPORT_PAGES}


def head_of(page):
    """A page's <head>; the NFL's comes from its joined template."""
    path = JOINED_TEMPLATE if page == 'nfl' else OG_PAGES[page]
    return path.read_text(encoding='utf-8').split('</head>')[0]


@pytest.mark.parametrize('sport', sorted(SPORT_PAGES))
def test_each_sport_links_its_own_icons_and_the_deploy_publishes_them(sport):
    head = head_of(sport)
    icon, touch = OWN_ICON[sport], OWN_TOUCH[sport]
    assert re.findall(r'<link rel="icon" href="([^"]+)"', head) == [f'../assets/{icon}']
    assert re.findall(r'<link rel="apple-touch-icon" href="([^"]+)">', head) == [f'../assets/{touch}']
    assert SHARED_FILES.get(f'assets/{icon}') == f'assets/{icon}'
    assert SHARED_FILES.get(f'assets/{touch}') == f'assets/{touch}'
    assert png_size((REPO / 'assets' / touch).read_bytes()) == (180, 180)


def test_the_mark_differs_per_sport_on_the_same_tile():
    shapes = {}
    for sport, name in OWN_ICON.items():
        root = ET.parse(REPO / 'assets' / name).getroot()
        assert root.get('viewBox') == '0 0 32 32', name
        tile = root.find(f'{SVG}rect')
        assert tile is not None and tile.get('fill') == '#0B0D10' and tile.get('rx') == '7', name
        filled = [e for e in root.iter() if e.get('fill') == '#7FA8F5']
        assert filled, f'{name} has no mark in the accent'
        shapes[sport] = tuple(ET.tostring(e) for e in root.find(f'{SVG}g').iter())
    assert len(set(shapes.values())) == 3, 'two sports share a mark'
    assert len({(REPO / 'assets' / t).read_bytes() for t in OWN_TOUCH.values()}) == 3, 'two sports share a home-screen icon'


def og_image(page):
    found = re.findall(r'<meta property="og:image" content="https://lifeisgreat07\.github\.io/NFL-Model-2/([^"]+)">',
                       head_of(page))
    assert len(found) == 1, (page, found)
    return found[0]


def test_each_page_previews_with_its_own_card():
    images = {page: og_image(page) for page in OG_PAGES}
    assert images == {'home': 'og-home.png', 'nfl': 'og-card.png', 'nhl': 'og-nhl.png', 'nba': 'og-nba.png'}
    for name in images.values():
        source = SHARED_FILES.get(name)
        assert source and source.startswith('assets/og/'), f'{name} is not published at the site root'
        data = (REPO / source).read_bytes()
        assert data[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', data[16:24]) == (1200, 630), name
        assert len(data) < 300_000, name
        html = (REPO / source).with_suffix('.html').read_text(encoding='utf-8')
        assert 'width:1200px;height:630px' in html, f'{name} has no source to remake it from'


def test_the_home_card_carries_the_three_marks_and_each_sport_card_its_own():
    marks = {name: (REPO / 'assets' / 'og' / name).read_text(encoding='utf-8').count('<svg class="mark"')
             for name in ('og-home.html', 'og-card.html', 'og-nhl.html', 'og-nba.html')}
    assert marks == {'og-home.html': 3, 'og-card.html': 1, 'og-nhl.html': 1, 'og-nba.html': 1}
    for name, word in (('og-card.html', 'NFL'), ('og-nhl.html', 'NHL'), ('og-nba.html', 'NBA')):
        assert f'<div class="eyebrow">{word} · ' in (REPO / 'assets' / 'og' / name).read_text(encoding='utf-8')
