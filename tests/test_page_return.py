"""Arriving on a page and coming back to one (Stage 76 item 10, the 2026-10-13 UI/UX audit's N12).

A link that opened a page left focus on <body>, where a tap on the nav
focused the page's heading, and the heading wore a 2px ring as though it
could be pressed. Back from the NFL's Methodology put the Week Board at the
top though it was left at 800 px; on the NHL, Back and Forward both landed
at 0. Now a link focuses the heading as a tap does, the heading has no ring,
the NFL pushes its entry before the page change scrolls to the top, and the
shared router keeps each entry's scroll in its state and puts it back.

tests/browser/check_page_return.py measures it on the NFL page and the NHL's
sample page; this holds the sources, the NBA's included.

Run with: pytest tests/test_page_return.py -v
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from src.core.template_parts import JOINED_TEMPLATE

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')
ROUTES = ROOT / 'src' / 'core' / 'routes.js'


def router(hash_, steps):
    """The shared router under node, with a scroll position. Steps:
    ['scroll', y], ['tap', page], ['pop', hash, state]."""
    if not NODE:
        pytest.skip('node not available')
    js = """
const listeners = {}; const shown = []; const scrolled = []; const log = [];
global.location = {hash: %s, pathname: '/nhl/', search: ''};
global.history = {state: null, scrollRestoration: 'auto',
  pushState: (s, t, u) => { log.push(['push', u, s]); history.state = s; location.hash = u.startsWith('#') ? u : ''; },
  replaceState: (s, t, u) => { log.push(['replace', u === undefined ? null : u, s]); history.state = s; }};
global.window = {scrollY: 0, addEventListener: (e, f, o) => { listeners[e] = f; },
                 scrollTo: (x, y) => { scrolled.push(y); window.scrollY = y; }};
global.document = {querySelectorAll: s => s === '.page' ? ['board', 'standings', 'method'].map(n => ({id: 'page-' + n})) : [],
                   querySelector: () => ({id: 'page-board'}),
                   addEventListener: (e, f, capture) => { listeners['doc:' + e] = f; listeners['doc:' + e + ':capture'] = capture === true; }};
%s
installRoutes((n, o) => shown.push([n, !!(o && o.focus)]));
for (const s of %s){
  if(s[0] === 'scroll') window.scrollY = s[1];
  if(s[0] === 'tap') listeners['doc:click']({target: {closest: () => ({dataset: {page: s[1]}})}});
  if(s[0] === 'pop'){ location.hash = s[1]; history.state = s[2]; listeners.popstate(); }
}
console.log(JSON.stringify({shown, scrolled, log, capture: listeners['doc:click:capture'], restoration: history.scrollRestoration}));
""" % (json.dumps(hash_), ROUTES.read_text(encoding='utf-8'), json.dumps(steps))
    r = subprocess.run([NODE, '-e', js], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_a_link_focuses_the_pages_heading_as_a_tap_does():
    assert router('#method', [])['shown'] == [['method', True]]
    assert router('', [['pop', '#standings', None]])['shown'] == [['standings', True]]


def test_a_tap_saves_the_scroll_it_leaves_before_it_pushes_on_the_capture_phase():
    out = router('', [['scroll', 800], ['tap', 'standings']])
    assert out['capture'] is True, "the push must come before the button's own handler scrolls to the top"
    assert out['log'] == [['replace', None, {'y': 800}], ['push', '#standings', {'y': 0}]]
    assert out['restoration'] == 'manual'


def test_back_and_forward_put_each_page_where_it_was_left():
    out = router('', [['pop', '', {'y': 800}], ['pop', '#method', {'y': 1500}], ['pop', '#standings', None]])
    assert out['scrolled'] == [800, 1500], 'an entry with no scroll kept is left at the top showPage gives it'


def test_the_nfl_pushes_before_the_page_changes_and_a_link_focuses():
    src = JOINED_TEMPLATE.read_text(encoding='utf-8').replace('\r\n', '\n')
    body = src[src.index('function goToPage(page){'):src.index('function replaceRoute(page){')]
    assert body.index('history.pushState(null, \'\', url);') < body.index('setActivePage(page, {focus:true});')
    assert '  if(location.hash) applyRoute(parseRoute(location.hash, routeKnown), {focus:true});\n' in src


def test_a_focused_heading_wears_no_ring():
    css = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
    assert '  h2[tabindex="-1"]:focus{outline:none;}\n' in css
    assert css.index('[tabindex]:focus-visible{') < css.index('h2[tabindex="-1"]:focus{outline:none;}')


def test_the_browser_check_runs():
    wf = (ROOT / '.github' / 'workflows' / 'browser-checks.yml').read_text(encoding='utf-8')
    assert 'run: python tests/browser/check_page_return.py --self-test --tmp "$RUNNER_TEMP/pagereturn"\n' in wf
    assert 'run: python tests/browser/check_page_return.py index.html "$RUNNER_TEMP/states/nhl.html"\n' in wf
