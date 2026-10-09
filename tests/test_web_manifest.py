"""A web app manifest beside the touch icon (Stage 47 item 14; Mark
approved it 2026-10-09).

`assets/site.webmanifest` names the site, its colours and its icons, so a
visitor who adds it to a phone's home screen gets the site's name and icon
rather than a screenshot and the page title. Every page links it, the site
build publishes it, and each page's Content-Security-Policy allows it
(`manifest-src 'self'`): the policy's `default-src 'none'` would otherwise
refuse it.

Run with: pytest tests/test_web_manifest.py -v
"""
import json
import re
from pathlib import Path

import pytest

from src.site.build import SHARED_FILES

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'assets' / 'site.webmanifest'
#: Each page template and where it is published, so its relative link can be resolved.
PAGES = {
    'src/dashboard/page.html': 'nfl/',
    'src/sports/nhl/pages/page.html': 'nhl/',
    'src/sports/nba/pages/page.html': 'nba/',
    'src/site/home/page.html': '',
}


@pytest.fixture(scope='module')
def manifest():
    return json.loads(MANIFEST.read_text(encoding='utf-8'))


def test_the_manifest_names_the_site_and_how_it_opens(manifest):
    for key in ('name', 'short_name', 'start_url', 'scope', 'display', 'background_color', 'theme_color', 'icons'):
        assert manifest.get(key), f'the manifest has no {key}'
    assert len(manifest['short_name']) <= 12, 'a home-screen label longer than this is cut off'
    assert manifest['display'] in ('standalone', 'minimal-ui', 'browser')


def test_start_and_scope_are_the_site_root_from_where_the_manifest_sits(manifest):
    """The manifest is published in assets/, and its URLs resolve against
    its own address: '../' is the site root."""
    assert manifest['start_url'] == '../' and manifest['scope'] == '../'


def test_every_icon_is_a_file_the_site_publishes(manifest):
    for icon in manifest['icons']:
        published = f"assets/{icon['src']}"
        assert published in SHARED_FILES, f'{published} is not published'
        assert (ROOT / SHARED_FILES[published]).is_file()


def test_the_colours_are_the_dark_themes_ground(manifest):
    """The splash colour is what a visitor sees before the page paints;
    the page's own first paint is the dark ground unless it was told light."""
    css = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
    n0 = re.search(r'--n0:(#[0-9A-Fa-f]{6})', css).group(1)
    assert manifest['background_color'].upper() == n0.upper() == manifest['theme_color'].upper()


def test_the_build_publishes_it():
    assert SHARED_FILES.get('assets/site.webmanifest') == 'assets/site.webmanifest'


@pytest.mark.parametrize('rel', sorted(PAGES))
def test_every_page_links_it_where_the_build_puts_it(rel):
    text = (ROOT / rel).read_text(encoding='utf-8')
    links = re.findall(r'<link rel="manifest" href="([^"]+)">', text)
    assert len(links) == 1, f'{rel}: {links}'
    published = (PAGES[rel] + links[0])
    while '/../' in '/' + published:
        published = re.sub(r'(^|/)[^/]+/\.\./', r'\1', published, count=1)
    assert published == 'assets/site.webmanifest', f'{rel} links {links[0]}, which resolves to {published}'


@pytest.mark.parametrize('rel', sorted(PAGES))
def test_every_pages_policy_lets_it_load(rel):
    text = (ROOT / rel).read_text(encoding='utf-8')
    policy = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', text).group(1)
    assert "manifest-src 'self'" in policy, f"{rel}: default-src 'none' would refuse the manifest"
