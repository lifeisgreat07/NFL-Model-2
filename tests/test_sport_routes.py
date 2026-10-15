"""The NHL's and NBA's pages answer to hash routes (Stage 68 item 23), and
since Stage 76 item 7 (the 2026-10-13 UI/UX audit's X6) a route carries one
argument: #board/<day> on both, #team/<club> on the NHL.

Run with: pytest tests/test_sport_routes.py -v
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ROUTES = ROOT / 'src' / 'core' / 'routes.js'
NODE = shutil.which('node')


@pytest.mark.parametrize('sport', ('nhl', 'nba'))
def test_each_sport_installs_the_shared_routes(sport):
    page = (ROOT / 'src' / 'sports' / sport / 'pages' / 'page.html').read_text(encoding='utf-8').replace('\r\n', '\n')
    # Since Stage 79 item 46 the shared accuracy component sits between them.
    assert '{% include "escape.js" %}\n{% include "routes.js" %}\n{% include "accuracy.js" %}\n' + f'{{% include "{sport}.js" %}}' in page
    js = (ROOT / 'src' / 'sports' / sport / 'pages' / f'{sport}.js').read_text(encoding='utf-8')
    assert js.count('replaceRoute = installRoutes(showPage, {') == 1 and 'function installRoutes' not in js
    site = (ROOT / 'src' / 'sports' / sport / 'site.py').read_text(encoding='utf-8')
    assert """.replace('{% include "routes.js" %}', ROUTES_JS.read_text(encoding='utf-8'))""" in site


def test_home_links_to_every_sports_methodology():
    page = (ROOT / 'src' / 'site' / 'home' / 'page.html').read_text(encoding='utf-8')
    for sport in ('nfl', 'nhl', 'nba'):
        assert f'href="{sport}/#method"' in page, sport


def run(hash_, clicks=()):
    if not NODE:
        pytest.skip('node not available')
    js = """
const listeners = {}; const shown = []; const pushed = [];
const pages = ['board', 'method', 'modellab'].map(n => ({id: 'page-' + n}));
const names = %s;
global.location = {hash: %s, pathname: '/nhl/', search: ''};
global.history = {pushState: (s, t, u) => { pushed.push(u); location.hash = u.startsWith('#') ? u : ''; }, replaceState: () => {}};
global.window = {addEventListener: (e, f) => { listeners[e] = f; }};
global.document = {querySelectorAll: s => s === '.page' ? pages : [], addEventListener: (e, f) => { listeners['doc:' + e] = f; }};
%s
installRoutes(n => shown.push(n));
const tap = n => listeners['doc:click']({target: {closest: s => names.includes(n) ? {dataset: {page: n}} : null}});
for (const c of %s) tap(c);
location.hash = '#modellab'; listeners.popstate();
location.hash = '#nonsense'; listeners.hashchange();
console.log(JSON.stringify({shown, pushed}));
""" % (json.dumps(['board', 'method', 'modellab']), json.dumps(hash_), ROUTES.read_text(encoding='utf-8'), json.dumps(list(clicks)))
    r = subprocess.run([NODE, '-e', js], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_a_link_to_a_page_opens_it_and_back_follows():
    out = run('#method', clicks=('board', 'modellab'))
    assert out['shown'][0] == 'method'
    assert out['pushed'] == ['/nhl/', '#modellab']
    assert out['shown'][-2:] == ['modellab', 'board'], 'back follows; a hash that names no page opens the board'


def test_the_bare_address_shows_the_board_without_a_route():
    out = run('')
    assert out['shown'] == ['modellab', 'board'] and out['pushed'] == []


# --- Stage 76 item 7: one argument ------------------------------------------

KNOWN = {'pages': ['board', 'teams', 'method'], 'days': ['2026-10-12', '2026-10-13'], 'teams': ['DET', 'TOR']}


def pure(calls):
    """parseHash and routeHash under node, one result per call."""
    if not NODE:
        pytest.skip('node not available')
    js = ROUTES.read_text(encoding='utf-8') + """
console.log(JSON.stringify(%s.map(([f, a, b]) => f === 'parse' ? parseHash(a, b) : routeHash(a))));
""" % json.dumps(calls)
    r = subprocess.run([NODE, '-e', js], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_a_route_names_a_day_or_a_club_and_falls_back_to_the_page_without_it():
    nba = {'pages': ['board', 'method'], 'days': ['2026-10-20']}
    out = pure([['parse', '#board/2026-10-13', KNOWN], ['parse', '#board/1999-01-01', KNOWN],
                ['parse', '#team/DET', KNOWN], ['parse', '#team/XYZ', KNOWN], ['parse', '#team/DET', nba],
                ['parse', '#teams', KNOWN], ['parse', '', KNOWN], ['parse', '#nonsense', KNOWN],
                ['parse', '#board%2F2026-10-12', KNOWN]])
    assert out == [{'page': 'board', 'arg': '2026-10-13'}, {'page': 'board'},
                   {'page': 'teams', 'arg': 'DET'}, {'page': 'teams'}, None,
                   {'page': 'teams'}, {'page': 'board'}, None,
                   {'page': 'board', 'arg': '2026-10-12'}]


def test_route_hash_writes_what_parse_hash_reads():
    out = pure([['hash', {'page': 'board', 'arg': '2026-10-13'}], ['hash', {'page': 'board'}],
                ['hash', {'page': 'teams', 'arg': 'DET'}], ['hash', {'page': 'teams'}], ['hash', {'page': 'method'}]])
    assert out == ['#board/2026-10-13', '', '#team/DET', '#teams', '#method']


def routed(hash_, steps):
    """installRoutes with a sport's argument under node. `steps` are
    ['tap', page], ['set', page, value] (a chip or a club, then replace),
    ['route', page] (a data-route button), ['click-elsewhere'], or ['pop', hash]. Returns what was shown, applied, pushed and replaced."""
    if not NODE:
        pytest.skip('node not available')
    js = """
const listeners = {}; const shown = []; const applied = []; const pushed = []; const replaced = [];
const pages = ['board', 'teams', 'method'].map(n => ({id: 'page-' + n}));
let active = 'board';

global.location = {hash: %s, pathname: '/nhl/', search: ''};
const go = u => { location.hash = u.startsWith('#') ? u : ''; };
global.history = {state: null,
  pushState: (s, t, u) => { history.state = s; pushed.push(u); go(u); },
  // A replace with no URL keeps the address: it only writes the entry's state (its scroll).
  replaceState: (s, t, u) => { history.state = s; if(u === undefined) return; replaced.push(u); go(u); }};
global.window = {addEventListener: (e, f) => { listeners[e] = f; }};
global.document = {querySelectorAll: s => s === '.page' ? pages : [],
                   querySelector: s => ({id: 'page-' + active}),
                   addEventListener: (e, f) => { listeners['doc:' + e] = f; }};
const tap = (attr, n) => listeners['doc:click']({target: {closest: s => ({dataset: {[attr]: n}})}});
%s
const state = {board: undefined, teams: 'ANA'};
const replace = installRoutes(n => { shown.push(n); active = n; }, {
  known: () => ({days: ['2026-10-12', '2026-10-13'], teams: ['DET', 'TOR']}),
  current: page => state[page],
  apply: (page, value) => { applied.push([page, value === undefined ? null : value]); if(page in state && (value || page === 'board')) state[page] = value; },
});
for (const s of %s){
  if(s[0] === 'tap'){ tap('page', s[1]); shown.push(s[1]); active = s[1]; }
  if(s[0] === 'route'){ tap('route', s[1]); shown.push(s[1]); active = s[1]; }
  if(s[0] === 'click-elsewhere'){ listeners['doc:click']({target: {closest: s => null}}); }
  if(s[0] === 'set'){ state[s[1]] = s[2]; replace(s[1]); }
  if(s[0] === 'pop'){ location.hash = s[1]; listeners.popstate(); }
}
console.log(JSON.stringify({shown, applied, pushed, replaced}));
""" % (json.dumps(hash_), ROUTES.read_text(encoding='utf-8'), json.dumps(steps))
    r = subprocess.run([NODE, '-e', js], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_a_typed_day_or_club_opens_on_it():
    assert routed('#board/2026-10-13', [])['applied'] == [['board', '2026-10-13']]
    out = routed('#team/DET', [])
    assert out['applied'] == [['teams', 'DET']] and out['shown'] == ['teams']
    out = routed('#board/1999-01-01', [])
    assert out['applied'] == [] and out['shown'] == [], 'a day that does not exist opens the board as it is'


def test_a_chip_or_a_club_replaces_the_address_and_a_page_change_pushes():
    out = routed('', [['set', 'board', '2026-10-12'], ['set', 'board', '2026-10-13'], ['tap', 'teams'],
                      ['set', 'teams', 'TOR']])
    assert out['replaced'] == ['#board/2026-10-12', '#board/2026-10-13', '#team/TOR']
    assert out['pushed'] == ['#team/ANA'], 'only the page change adds a history entry'


def test_a_replace_for_a_page_not_on_screen_writes_nothing():
    assert routed('', [['set', 'teams', 'TOR']])['replaced'] == []


def test_back_to_the_bare_address_puts_the_board_back_as_it_opened():
    out = routed('', [['set', 'board', '2026-10-12'], ['pop', '']])
    assert out['applied'][-1] == ['board', None] and out['shown'][-1] == 'board'


@pytest.mark.parametrize('sport', ('nhl', 'nba'))
def test_a_day_chip_and_a_week_step_write_the_day(sport):
    js = (ROOT / 'src' / 'sports' / sport / 'pages' / f'{sport}.js').read_text(encoding='utf-8')
    chip = js.index(f"document.querySelectorAll('.{sport}-day-chip').forEach(btn => btn.addEventListener('click'")
    assert "    renderBoard();\n    replaceRoute('board');\n" in js[chip:chip + 300]
    step = js.index('function stepWeek(by){')
    assert "  renderBoard();\n  replaceRoute('board');\n}" in js[step:step + 300]
    assert js.index('let replaceRoute = () => {};') < js.index('function renderBoard(){')
    assert 'known: () => ({days: WEEK_KEYS.flatMap(weekDays)' in js


def test_the_nhl_club_select_writes_the_club():
    js = (ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js').read_text(encoding='utf-8')
    change = js.index("select.addEventListener('change', () => {")
    assert "      renderTeams();\n      replaceRoute('teams');\n" in js[change:change + 300]
    assert "teams: Object.keys(DATA.teams)" in js


def test_the_browser_check_runs():
    wf = (ROOT / '.github' / 'workflows' / 'browser-checks.yml').read_text(encoding='utf-8')
    assert 'run: python tests/browser/check_routes.py --self-test --tmp "$RUNNER_TEMP/routes"\n' in wf
    assert 'run: python tests/browser/check_routes.py "$RUNNER_TEMP/states/nhl.html"\n' in wf


# --- Stage 76 item 8: every button that opens a page goes through the router --

def test_a_button_drawn_after_load_or_outside_the_nav_still_pushes_its_page():
    """The router listens on the document, so the NHL side column's buttons,
    drawn again with every board, and the NBA's data-route button push their
    page as a nav button does; a click on anything else pushes nothing."""
    out = routed('', [['click-elsewhere'], ['route', 'method'], ['tap', 'board']])
    assert out['pushed'] == ['#method', '/nhl/']


def test_the_router_listens_on_the_document_not_per_button():
    src = ROUTES.read_text(encoding='utf-8')
    assert "document.addEventListener('click', e => {" in src
    assert "e.target.closest('[data-page], [data-route]')" in src
    assert "querySelectorAll('[data-page]').forEach" not in src


def test_the_nba_backtest_button_names_its_route():
    js = (ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js').read_text(encoding='utf-8')
    assert '<button type="button" class="nba-to-lab" data-route="modellab">' in js
