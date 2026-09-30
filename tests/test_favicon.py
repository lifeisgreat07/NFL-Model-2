"""The site's favicon (Stage 29; option B, chosen by Mark 2026-09-29).

There was none, so every tab showed the browser's blank page. The icon is
the sidebar's football on the site's darkest neutral. Three things have to
hold together for it to show: the page links it, the file is there and is
the SVG the link says, and the deploy publishes it at the path the link
names. A link that points nowhere fails silently -- the browser just shows
the blank page again -- so each is checked here rather than by looking.

Run with: pytest tests/test_favicon.py -v
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TEMPLATE = REPO / 'src' / 'dashboard_template.html'
ICON = REPO / 'assets' / 'favicon.svg'
TOUCH = REPO / 'assets' / 'apple-touch-icon.png'
DEPLOY = REPO / '.github' / 'workflows' / 'deploy-pages.yml'
SVG = '{http://www.w3.org/2000/svg}'


def icon_links():
    head = TEMPLATE.read_text(encoding='utf-8').split('</head>')[0]
    return re.findall(r'<link rel="icon" href="([^"]+)" type="([^"]+)">', head)


def test_the_page_links_one_svg_icon_in_its_head():
    links = icon_links()
    assert links == [('assets/favicon.svg', 'image/svg+xml')], links


def test_the_icon_is_a_square_svg_with_a_dark_tile_and_the_accent_ball():
    root = ET.parse(ICON).getroot()
    assert root.tag == f'{SVG}svg'
    assert root.get('viewBox') == '0 0 32 32', 'the favicon is not square at 32 units'
    tile = root.find(f'{SVG}rect')
    assert tile is not None and tile.get('fill') == '#0B0D10', 'the dark tile is gone'
    ball = root.find(f'.//{SVG}ellipse')
    assert ball is not None and ball.get('fill') == '#7FA8F5', 'the accent football is gone'


def test_the_deploy_publishes_the_icon_where_the_link_points():
    text = DEPLOY.read_text(encoding='utf-8')
    href = icon_links()[0][0]
    assert f'cp assets/favicon.svg _site/{href}' in text, (
        f'deploy-pages.yml does not copy the favicon to _site/{href}, so the '
        'live site links an icon that is not there')


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
    assert touch_links() == ['assets/apple-touch-icon.png'], touch_links()


def test_the_home_screen_icon_is_a_180px_png():
    data = TOUCH.read_bytes()
    assert png_size(data) == (180, 180), png_size(data)


def test_the_deploy_publishes_the_home_screen_icon_where_the_link_points():
    text = DEPLOY.read_text(encoding='utf-8')
    href = touch_links()[0]
    assert f'cp assets/apple-touch-icon.png _site/{href}' in text, (
        f'deploy-pages.yml does not copy the home-screen icon to _site/{href}')


def test_a_file_that_is_not_a_180px_png_is_caught():
    """Synthetic, so the failing branch stays reachable."""
    assert png_size(b'GIF89a' + b'0' * 30) is None
    fake = b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\x0dIHDR' + (32).to_bytes(4, 'big') * 2
    assert png_size(fake) == (32, 32)
