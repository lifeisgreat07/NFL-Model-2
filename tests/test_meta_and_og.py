"""The page describes itself to search results and link previews.

Stage 13 (CLAUDE.md). The page had a <title> and nothing else: a search
result showed whatever text it found first, and a link pasted into a chat
showed a bare URL. It now carries a meta description and Open Graph tags
with one static image, assets/og/og-card.png, which the Pages deploy copies
to the site root.

Run with: pytest tests/test_meta_and_og.py -v
"""
import html
import re
import struct
from pathlib import Path

import pytest

from src.pipeline.template_parts import JOINED_TEMPLATE
from src.site.build import SHARED_FILES

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = JOINED_TEMPLATE
IMAGE = ROOT / 'assets' / 'og' / 'og-card.png'
SOURCE = ROOT / 'assets' / 'og' / 'og-card.html'
SITE = 'https://lifeisgreat07.github.io/NFL-Model-2/'


@pytest.fixture(scope='module')
def head():
    src = TEMPLATE.read_text(encoding='utf-8')
    return src.split('<style>')[0]


def meta(head, attr, key):
    found = re.findall(rf'<meta {attr}="{re.escape(key)}" content="([^"]*)">', head)
    assert len(found) == 1, f'expected one <meta {attr}="{key}">, found {len(found)}'
    return html.unescape(found[0])


def test_the_description_fits_a_search_result(head):
    d = meta(head, 'name', 'description')
    assert 50 <= len(d) <= 160, f'the description is {len(d)} characters; a search result cuts at about 160'


def test_the_link_preview_says_what_the_site_is(head):
    assert meta(head, 'property', 'og:type') == 'website'
    assert meta(head, 'property', 'og:title')
    assert meta(head, 'property', 'og:description') == meta(head, 'name', 'description'), (
        'the preview and the search result describe the site differently')
    assert meta(head, 'name', 'twitter:card') == 'summary_large_image'


def test_the_preview_urls_are_absolute_and_on_the_site(head):
    # The board's own address since Stage 53; the image stays at the root.
    assert meta(head, 'property', 'og:url') == SITE + 'nfl/'
    assert meta(head, 'property', 'og:image') == SITE + 'og-card.png', (
        'link-preview crawlers do not resolve a relative og:image')


def test_the_image_is_a_1200_by_630_png_and_says_so(head):
    data = IMAGE.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', 'the Open Graph image is not a PNG'
    width, height = struct.unpack('>II', data[16:24])
    assert (width, height) == (1200, 630), f'the image is {width}x{height}, not the 1200x630 previews expect'
    assert meta(head, 'property', 'og:image:width') == '1200'
    assert meta(head, 'property', 'og:image:height') == '630'
    assert len(data) < 300_000, f'the image is {len(data):,} bytes; a preview image should load at once'
    assert meta(head, 'property', 'og:image:alt'), 'the image has no text alternative'


def test_the_deploy_publishes_the_image_where_og_image_points():
    assert SHARED_FILES.get('og-card.png') == 'assets/og/og-card.png', (
        'og:image names og-card.png at the site root, and src/site/build.py does not publish it there')


def test_the_image_can_be_remade_from_its_source():
    src = SOURCE.read_text(encoding='utf-8')
    assert 'width:1200px;height:630px' in src, 'the source no longer draws a 1200x630 card'
    assert '../fonts/plus-jakarta-sans-latin-normal.woff2' in src, (
        "the source no longer uses the page's own font file")
    assert (ROOT / 'assets' / 'fonts' / 'plus-jakarta-sans-latin-normal.woff2').exists()
