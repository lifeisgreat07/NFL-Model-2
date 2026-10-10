"""The page-header contract on the NHL's and NBA's pages too (Stage 68 item 13).

tests/test_page_header.py holds the NFL's pages to one rule: every page's
eyebrow is the sidebar group its nav button sits in, and its title is that
button's label. It read the NFL's template only, and both day boards broke
the rule: their eyebrow said "Day by Day" under groups called "This Week"
(NHL) and "This Season" (NBA). The NBA's group is now "This Week", like the
other two sports', and both eyebrows say so.

Run with: pytest tests/test_page_header_sports.py -v
"""
import re
from pathlib import Path

import pytest

from tests.test_page_header import header_problems, sidebar_groups, strip_comments

ROOT = Path(__file__).resolve().parents[1]
BODIES = {'nhl': ROOT / 'src/sports/nhl/pages/body.html', 'nba': ROOT / 'src/sports/nba/pages/body.html'}
PAGES = {'nhl': 9, 'nba': 4}


def page_heads(src):
    """{page id: (html before the .page-head, the head's html)}, at any indent."""
    out = {}
    for m in re.finditer(r'<section class="page[^"]*" id="page-([^"]+)">(.*?)</section>', strip_comments(src), re.S):
        body = m.group(2)
        h = re.search(r'<div class="page-head">(.*?<div class="desc">.*?</div>)', body, re.S)
        out[m.group(1)] = (body[:h.start()] if h else body, h.group(1) if h else None)
    return out


@pytest.mark.parametrize('sport', BODIES)
def test_every_page_header_agrees_with_the_sidebar(sport):
    src = BODIES[sport].read_text(encoding='utf-8')
    problems = header_problems(sidebar_groups(src), page_heads(src))
    assert not problems, f'{sport}: page headers and the sidebar disagree:\n  ' + '\n  '.join(problems)


@pytest.mark.parametrize('sport', BODIES)
def test_the_scan_found_every_page(sport):
    assert len(page_heads(BODIES[sport].read_text(encoding='utf-8'))) == PAGES[sport]


def test_the_first_group_has_one_name_in_every_sport():
    nfl = sidebar_groups((ROOT / 'src/dashboard/body.html').read_text(encoding='utf-8'))[0][0]
    for sport, path in BODIES.items():
        assert sidebar_groups(path.read_text(encoding='utf-8'))[0][0] == nfl, sport
