"""Every sport page's tabs: one order, one name, one address (audit 9 D14).

src/core/page_tabs.py holds the list. Each sport's sidebar shows the tabs it has in that order under those
names, at those addresses (the NFL's two older ids go through the router's ROUTE_ADDRESS); the phone bar holds
the rest of them, and its More sheet the same five in every sport; each page's heading is its tab's name. The
NFL's old addresses, #teamdive and #changelog, still open their pages on any sport and are replaced by the
new ones.

Run with: pytest tests/test_page_tabs.py -v
"""
import html
import json
import re
import subprocess
from pathlib import Path

import pytest

from src.core.page_tabs import BOARD, MORE, OLD_ADDRESSES, TABS, address
from tests.optional import require_tool

ROOT = Path(__file__).resolve().parents[1]
BODIES = {'nfl': ROOT / 'src' / 'dashboard' / 'body.html', 'nhl': ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'body.html',
          'nba': ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'body.html'}
APP_PAGES = (ROOT / 'src' / 'dashboard' / 'app_pages.js').read_text(encoding='utf-8')
ROUTES = (ROOT / 'src' / 'core' / 'routes.js').read_text(encoding='utf-8')


def buttons(t, cls):
    return [(address(page), html.unescape(re.sub(r'<[^>]+>', '', inner)).strip())
            for page, inner in re.findall(rf'<button class="{cls}[^"]*" data-page="([a-z]+)"[^>]*>(.*?)</button>', t, re.S)]


def want(sport, t, short=False):
    have = {address(p) for p in re.findall(r'<section class="page[^"]*" id="page-([a-z]+)"', t)}
    return [(a, s if short else (BOARD[sport] if a == 'board' else name)) for a, name, s in TABS if a in have]


@pytest.mark.parametrize('sport', BODIES)
def test_the_sidebar_shows_the_shared_tabs_in_the_shared_order_under_the_shared_names(sport):
    t = BODIES[sport].read_text(encoding='utf-8')
    assert buttons(t, 'nav-btn') == want(sport, t)


@pytest.mark.parametrize('sport', BODIES)
def test_the_phone_bar_and_its_more_sheet_hold_the_rest_in_the_same_order(sport):
    t = BODIES[sport].read_text(encoding='utf-8')
    every = want(sport, t, short=True)
    assert buttons(t, 'bnav-btn') == [x for x in every if x[0] not in MORE]
    assert buttons(t, 'bnav-more-item') == [x for x in every if x[0] in MORE]
    assert [a for a, _ in buttons(t, 'bnav-more-item')] == list(MORE), f'{sport}: the More sheet lacks a page'


@pytest.mark.parametrize('sport', BODIES)
def test_each_pages_heading_is_its_tabs_name(sport):
    t = BODIES[sport].read_text(encoding='utf-8')
    for page in re.findall(r'<button class="nav-btn[^"]*" data-page="([a-z]+)"', t):
        sec = re.search(rf'<section class="page[^"]*" id="page-{page}"[^>]*>.*?<h2>(.*?)</h2>', t, re.S)
        name = dict(buttons(t, 'nav-btn'))[address(page)]
        assert sec and html.unescape(sec.group(1)) == name, f'{sport} {page}: heading {sec and sec.group(1)!r}, tab {name!r}'


def js_object(src, name):
    m = re.search(rf'const {name} = \{{(.*?)\}};', src)
    assert m, name
    return dict(re.findall(r"(\w+):\s*'(\w+)'", m.group(1)))


def test_both_routers_know_the_old_addresses_this_list_names():
    assert js_object(APP_PAGES, 'ROUTE_ADDRESS') == OLD_ADDRESSES, "the NFL's router and page_tabs.py disagree"
    assert js_object(ROUTES, 'ROUTE_OLD') == OLD_ADDRESSES, "the NHL's and NBA's router and page_tabs.py disagree"


def test_an_old_address_opens_its_page_on_the_other_sports_too():
    node = require_tool('node')
    fns = re.search(r'const ROUTE_OLD = .*?\nfunction routeHash\(r\)\{.*?\n\}\n', ROUTES, re.S).group(0)
    known = {'pages': ['board', 'teams', 'changes', 'method']}
    src = fns + (f"const K = {json.dumps(known)};\n"
                 "process.stdout.write(JSON.stringify(['#teamdive', '#changelog', '#teams', '#team/BOS', '#changes']"
                 ".map(h => parseHash(h, K))));")
    got = json.loads(subprocess.run([node, '-e', src], capture_output=True, text=True, encoding='utf-8', check=True).stdout)
    assert got == [{'page': 'teams'}, {'page': 'changes'}, {'page': 'teams'}, {'page': 'teams'}, {'page': 'changes'}]


def test_arriving_at_an_old_address_replaces_it_with_the_new():
    assert ("  const old = /^#(teamdive|changelog)$/.exec(location.hash || '');\n"
            "  if(old) history.replaceState(null, '', routeUrl({page: old[1]}));\n") in APP_PAGES
    assert "    if(ROUTE_OLD[location.hash.replace(/^#/, '')]) history.replaceState(null, '', url(first.page));\n" in ROUTES
