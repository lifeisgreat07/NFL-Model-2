"""A game has an address on every sport (Stage 76 item 9, the 2026-10-13 UI/UX audit's F4).

#game/<id> opens the board on that game's week or day, with its card open
(its row, on a phone or a day board) and on screen. On the NFL a game's
address is its week and its two clubs, #game/2026_week6-SEA-DEN, so nothing
in the data has to carry an id; on the NHL and NBA it is the game's id from
the schedule. A game that does not exist opens the board.

tests/browser/check_routes.py opens a game on the NFL page and the NHL's
sample page; the NBA has no rows before opening night, so its wiring is held
here by source.

Run with: pytest tests/test_game_routes.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.core.template_parts import JOINED_TEMPLATE

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')
ROUTES = ROOT / 'src' / 'core' / 'routes.js'


def node(js):
    if not NODE:
        pytest.skip('node not available')
    r = subprocess.run([NODE, '-e', js], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def nfl_src():
    return JOINED_TEMPLATE.read_text(encoding='utf-8').replace('\r\n', '\n')


def test_the_nfl_reads_and_writes_a_game():
    code = re.search(r'const ROUTE_PAGES = .*?\nfunction experimentSlug\(.*?\n\}\n', nfl_src(), re.S)
    assert code, 'the route functions are not findable -- re-anchor this guard'
    known = {'weeks': ['2026_week6'], 'teams': ['DEN'], 'experiments': [], 'games': ['2026_week6-SEA-DEN']}
    out = node(code.group(0) + """
const K = %s;
console.log(JSON.stringify([parseRoute('#game/2026_week6-SEA-DEN', K), parseRoute('#game/2026_week6-SEA-KC', K),
  parseRoute('#game/2026_week6-SEA-DEN', {weeks: [], teams: [], experiments: []}),
  routeHash({page: 'board', week: '2026_week6', game: '2026_week6-SEA-DEN'}),
  gameKey('2026_week6', {away: 'SEA', home: 'DEN'})]));
""" % json.dumps(known))
    assert out == [{'page': 'board', 'week': '2026_week6', 'game': '2026_week6-SEA-DEN'}, {'page': 'board'},
                   {'page': 'board'}, '#game/2026_week6-SEA-DEN', '2026_week6-SEA-DEN']


def test_the_nfl_cards_carry_their_key_and_a_route_opens_one():
    src = nfl_src()
    assert 'card.dataset.game = gameKey(currentBoardWeek, sorted[i]);' in src
    assert 'const games = weekKeysSorted.flatMap(k => ((weeks[k] || {}).games || []).map(g => gameKey(k, g)));' in src
    apply = src[src.index('function applyRoute(r, opts){'):src.index('function openGame(key){')]
    assert '  if(r.game) openGame(r.game);\n' in apply
    body = src[src.index('function openGame(key){'):src.index('(function wireRoutes(){')]
    assert "if(!card && currentFilter !== 'all'){" in body, 'a filter that hides the game is cleared'
    assert "const phone = row && row.offsetParent;" in body
    assert "if(phone && row.getAttribute('aria-expanded') !== 'true') row.click();" in body
    assert "(phone ? row : card).scrollIntoView({block:'start'});" in body, 'on a phone the row, which names the game, goes to the top'
    assert "history.replaceState(null, '', want);" in body, 'the address keeps the game'


def test_the_nfl_card_scrolls_to_a_margin_on_a_desktop():
    css = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
    assert '  .game-card{scroll-margin-top:var(--s5);}\n' in css
    assert css.index('.game-card{scroll-margin-top:var(--s5);}') < css.index('.game-card.nfl-collapsible{scroll-margin:')
    assert '    #game-grid .nfl-row{scroll-margin-top:76px;}' in css, 'the phone row clears the top bar'


def test_the_shared_router_reads_and_writes_a_game():
    out = node(ROUTES.read_text(encoding='utf-8') + """
const K = {pages: ['board', 'method'], days: [], games: ['2026020001']};
console.log(JSON.stringify([parseHash('#game/2026020001', K), parseHash('#game/999', K),
  routeHash({page: 'board', game: '2026020001'})]));
""")
    assert out == [{'page': 'board', 'game': '2026020001'}, {'page': 'board'}, '#game/2026020001']


def test_the_shared_router_opens_a_game_on_load_and_on_back():
    out = node("""
const listeners = {}; const opened = []; const shown = [];
global.location = {hash: '#game/2026020001', pathname: '/nhl/', search: ''};
global.history = {pushState: () => {}, replaceState: () => {}};
global.window = {addEventListener: (e, f) => { listeners[e] = f; }};
global.document = {querySelectorAll: s => s === '.page' ? [{id: 'page-board'}] : [], addEventListener: () => {},
                   querySelector: () => ({id: 'page-board'})};
""" + ROUTES.read_text(encoding='utf-8') + """
installRoutes(n => shown.push(n), {known: () => ({games: ['2026020001', '2026020002']}), open: id => opened.push(id)});
location.hash = '#game/2026020002'; listeners.popstate();
location.hash = '#game/nope'; listeners.popstate();
console.log(JSON.stringify({opened, shown}));
""")
    assert out['opened'] == ['2026020001', '2026020002']


@pytest.mark.parametrize('sport, data', [('nhl', 'DATA'), ('nba', 'BD')])
def test_each_day_board_opens_the_games_day_with_its_row_open(sport, data):
    js = (ROOT / 'src' / 'sports' / sport / 'pages' / f'{sport}.js').read_text(encoding='utf-8')
    start = js.index('  open: id => {')
    body = js[start:js.index('\n  },\n', start)]
    assert f'const g = {data}.games.find(x => x.id === id);' in body
    assert 'currentWeek = mondayOf(g.day);' in body and 'currentDay = g.day;' in body
    assert body.index(f'OPEN_ROWS.add(`{sport}-detail-${{id}}`);') < body.index('renderBoard();')
    assert 'if(card) revealOpened(card);' in body
    assert f'games: {data}.games.map(g => g.id)' in js


def test_the_browser_check_runs():
    wf = (ROOT / '.github' / 'workflows' / 'browser-checks.yml').read_text(encoding='utf-8')
    assert 'run: python tests/browser/check_game_route.py --self-test --tmp "$RUNNER_TEMP/gameroute"\n' in wf
    assert 'run: python tests/browser/check_game_route.py index.html "$RUNNER_TEMP/states/nhl.html"\n' in wf
