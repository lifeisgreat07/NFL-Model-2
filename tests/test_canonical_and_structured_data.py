"""Each page names its one address and says what it is (Stage 47 item 12).

A canonical link tells a search engine which address is the page, so the
NFL board is not split between the root that used to hold it and nfl/
where it lives now. A JSON-LD block says what the page is: the site, a
sport's page, and on the NFL board the picks file as a dataset.

Held here: one canonical per page, absolute, matching og:url where the page
has one; the JSON-LD parses, names the same address, and on the board points
at the picks file the site build publishes; both come after the page's
Content-Security-Policy.

Run with: pytest tests/test_canonical_and_structured_data.py -v
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://lifeisgreat07.github.io/NFL-Model-2/'
PAGES = {
    'src/site/home/page.html': BASE,
    'src/dashboard/page.html': BASE + 'nfl/',
    'src/sports/nhl/pages/page.html': BASE + 'nhl/',
    'src/sports/nba/pages/page.html': BASE + 'nba/',
}


def text(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def ld(rel):
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', text(rel), re.S)
    assert len(blocks) == 1, f'{rel}: expected one JSON-LD block, found {len(blocks)}'
    return json.loads(blocks[0])


@pytest.mark.parametrize('rel,url', PAGES.items())
def test_one_absolute_canonical_per_page(rel, url):
    links = re.findall(r'<link rel="canonical" href="([^"]+)">', text(rel))
    assert links == [url], links


@pytest.mark.parametrize('rel,url', PAGES.items())
def test_og_url_and_canonical_agree(rel, url):
    og = re.findall(r'<meta property="og:url" content="([^"]+)">', text(rel))
    assert og in ([], [url]), og


@pytest.mark.parametrize('rel,url', PAGES.items())
def test_the_structured_data_parses_and_names_the_same_address(rel, url):
    data = ld(rel)
    assert data['@context'] == 'https://schema.org'
    assert data['url'] == url


def test_the_board_offers_the_picks_file_as_a_dataset():
    data = ld('src/dashboard/page.html')
    dist = data['mainEntity']['distribution']
    assert data['mainEntity']['@type'] == 'Dataset'
    assert dist['contentUrl'] == BASE + 'nfl/picks.csv' and dist['encodingFormat'] == 'text/csv'
    build = text('src/site/build.py')
    assert "shutil.copyfile(ROOT / 'picks.csv', dest / 'picks.csv')" in build, 'the dataset must be published'
    assert 'MIT License' in text('LICENSE').splitlines()[0] and data['mainEntity']['license'].endswith('/MIT')


@pytest.mark.parametrize('rel', PAGES)
def test_both_come_after_the_page_policy(rel):
    t = text(rel)
    csp = t.index('http-equiv="Content-Security-Policy"')
    assert csp < t.index('rel="canonical"') and csp < t.index('application/ld+json')
