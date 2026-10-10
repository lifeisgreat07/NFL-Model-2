"""The NHL's and NBA's pages answer to hash routes (Stage 68 item 23).

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
    assert '{% include "escape.js" %}\n{% include "routes.js" %}\n' + f'{{% include "{sport}.js" %}}' in page
    js = (ROOT / 'src' / 'sports' / sport / 'pages' / f'{sport}.js').read_text(encoding='utf-8')
    assert js.count('installRoutes(showPage);') == 1 and 'function installRoutes' not in js
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
const buttons = %s.map(n => ({dataset: {page: n}, addEventListener: (e, f) => { listeners['click:' + n] = f; }}));
global.location = {hash: %s, pathname: '/nhl/', search: ''};
global.history = {pushState: (s, t, u) => { pushed.push(u); location.hash = u.startsWith('#') ? u : ''; }};
global.window = {addEventListener: (e, f) => { listeners[e] = f; }};
global.document = {querySelectorAll: s => s === '.page' ? pages : buttons};
%s
installRoutes(n => shown.push(n));
for (const c of %s) listeners['click:' + c]();
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
