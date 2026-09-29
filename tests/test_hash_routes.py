"""Pages, Week Board weeks, teams and Model Lab experiments have addresses.

Stage 13 (CLAUDE.md). Nothing on the page could be linked to: every nav
control was a button with no href and no hash was read except `#picks=`
share links, so "look at Kansas City" or "week 2's board" could not be sent
to anyone, and the back button left the site. Routes:

    #board, #board/2026_week2, #team/KC, #modellab/<experiment slug>,
    #ratings, #picks, #accuracy, #teamdive, #modellab, #method,
    #changelog, #reliability

parseRoute, routeHash and experimentSlug are executed under node. The
wiring (pushState on a page change, replaceState on a week or team change,
popstate, the load-time read, share links left alone) is held by source
guards, because it needs a browser.

Run with: pytest tests/test_hash_routes.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'src' / 'dashboard_template.html'
NODE = shutil.which('node')

KNOWN = {'weeks': ['2026_week1', '2026_week2'], 'teams': ['KC', 'LA'],
         'experiments': ['qb-feature-trailing-epa-dropback']}
HASHES = ['', '#', '#board', '#board/2026_week2', '#board/1999_week1', '#team/KC',
          '#team/ZZZ', '#team/', '#ratings', '#modellab/qb-feature-trailing-epa-dropback',
          '#modellab/no-such-row', '#part-method', '#picks=abc', '#ratings&picks=abc',
          '#board/2026_week2&picks=abc',
          '#team/%E0%A4', '#Ratings', 'board']
ROUTES = [{'page': 'board'}, {'page': 'board', 'week': '2026_week2'}, {'page': 'teamdive', 'team': 'KC'},
          {'page': 'teamdive'}, {'page': 'modellab', 'experiment': 'qb-feature-trailing-epa-dropback'},
          {'page': 'method'}]
NAMES = ['QB feature (trailing EPA/dropback)', 'Ridge alpha tuning (200 -> 15)',
         '  Early-season QB-change interaction term  ', 'x' * 80]


@pytest.fixture(scope='module')
def src():
    return TEMPLATE.read_text(encoding='utf-8').replace('\r\n', '\n')


@pytest.fixture(scope='module')
def run(src):
    if not NODE:
        pytest.skip('node not available')
    code = re.search(r'const ROUTE_PAGES = .*?\nfunction experimentSlug\(.*?\n\}\n', src, re.S)
    assert code, 'the route functions are not findable -- re-anchor this guard'
    js = (code.group(0) +
          f'\nconst K={json.dumps(KNOWN)};'
          f'process.stdout.write(JSON.stringify({{'
          f'parsed: {json.dumps(HASHES)}.map(h => parseRoute(h, K)),'
          f'hashes: {json.dumps(ROUTES)}.map(r => routeHash(r)),'
          f'slugs: {json.dumps(NAMES)}.map(experimentSlug),'
          f'pages: ROUTE_PAGES}}));')
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    out['parsed'] = dict(zip(HASHES, out['parsed']))
    return out


def test_an_empty_address_is_the_week_board(run):
    assert run['parsed'][''] == {'page': 'board'}
    assert run['parsed']['#'] == {'page': 'board'}


def test_a_week_a_team_and_an_experiment_are_read(run):
    p = run['parsed']
    assert p['#board/2026_week2'] == {'page': 'board', 'week': '2026_week2'}
    assert p['#team/KC'] == {'page': 'teamdive', 'team': 'KC'}
    assert p['#modellab/qb-feature-trailing-epa-dropback'] == {
        'page': 'modellab', 'experiment': 'qb-feature-trailing-epa-dropback'}
    assert p['#ratings'] == {'page': 'ratings'}
    assert p['board'] == {'page': 'board'}, 'a hash without its "#" is still read'


def test_an_unknown_week_team_or_row_opens_the_page_without_it(run):
    p = run['parsed']
    assert p['#board/1999_week1'] == {'page': 'board'}
    assert p['#team/ZZZ'] == {'page': 'teamdive'} and p['#team/'] == {'page': 'teamdive'}
    assert p['#modellab/no-such-row'] == {'page': 'modellab'}
    assert p['#team/%E0%A4'] == {'page': 'teamdive'}, 'a malformed escape must not throw'


def test_share_links_and_page_anchors_are_not_routes(run):
    p = run['parsed']
    assert p['#picks=abc'] is None and p['#ratings&picks=abc'] is None, (
        'a share link read as a route would switch pages under readSharedPicksFromUrl')
    # readSharedPicksFromUrl matches picks= after '#' OR '&', so a share
    # payload can follow a route-shaped head. Without the explicit guard this
    # one reads as {page: 'board'} and switches pages under the shared view.
    assert p['#board/2026_week2&picks=abc'] is None
    assert p['#part-method'] is None, (
        "Methodology's own jump links change the hash; reading one as a route would leave the page")
    assert p['#Ratings'] is None, 'routes are lower case; anything else is not one'


def test_route_hash_writes_what_parse_route_reads(run):
    assert run['hashes'] == ['#board', '#board/2026_week2', '#team/KC', '#teamdive',
                             '#modellab/qb-feature-trailing-epa-dropback', '#method']


def test_experiment_slugs_are_plain_and_short(run):
    assert run['slugs'][0] == 'qb-feature-trailing-epa-dropback'
    assert run['slugs'][1] == 'ridge-alpha-tuning-200-15'
    assert run['slugs'][2] == 'early-season-qb-change-interaction-term'
    assert len(run['slugs'][3]) <= 48 and not run['slugs'][3].endswith('-')


def test_every_page_a_nav_control_opens_has_a_route(run, src):
    targets = set(re.findall(r'data-page="([a-z0-9_-]+)"', src))
    assert targets and set(run['pages']) == targets, (
        f'ROUTE_PAGES {sorted(run["pages"])} is not the set of pages the navs open {sorted(targets)}')


def test_the_navs_record_the_page_in_the_address(src):
    assert "btn.addEventListener('click', ()=> goToPage(btn.dataset.page));" in src, (
        'a nav click no longer goes through goToPage, so the address and Back stop following it')
    body = re.search(r'function goToPage\(page\)\{.*?\n\}', src, re.S).group(0)
    assert 'history.pushState(' in body, 'a page change must add a history entry, or Back leaves the site'
    assert re.search(r'if\(inSharedView\(\)\) return;', body), (
        'a page change during a shared view would overwrite the share link in the address')


def test_a_week_or_team_change_replaces_rather_than_adds(src):
    wire = re.search(r'\(function wireRoutes\(\)\{.*?\n\}\)\(\);', src, re.S)
    assert wire, 'wireRoutes is gone -- re-anchor this guard'
    code = wire.group(0)
    assert "week.addEventListener('change', ()=> replaceRoute('board'))" in code
    assert "team.addEventListener('change', ()=> replaceRoute('teamdive'))" in code
    body = re.search(r'function replaceRoute\(page\)\{.*?\n\}', src, re.S).group(0)
    assert 'history.replaceState(' in body and 'pushState' not in body, (
        'stepping through weeks must not add a history entry per week')


def test_back_forward_and_a_pasted_address_are_followed(src):
    code = re.search(r'\(function wireRoutes\(\)\{.*?\n\}\)\(\);', src, re.S).group(0)
    assert "window.addEventListener('popstate', ()=> applyRoute(parseRoute(location.hash, routeKnown), {focus:true}));" in code
    assert 'if(location.hash) applyRoute(parseRoute(location.hash, routeKnown));' in code, (
        'a link with a route in it no longer opens that route on load')


def test_stage8_design_no_longer_claims_navigation_stubs(src):
    doc = (ROOT / 'docs' / 'design' / 'STAGE8-DESIGN.md').read_text(encoding='utf-8')
    assert 'stubs are already wired' not in doc, (
        'STAGE8-DESIGN.md says openTeam/openWeek stubs are wired; neither ever existed')
    assert 'function openTeam' not in src and 'function openWeek' not in src
