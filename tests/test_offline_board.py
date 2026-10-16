"""Installable, and the last board offline (Stage 80 item 62, the 2026-10-13 UI/UX audit's F14).

Measured 2026-10-15 on the site built from main, served over http on this
computer, at 390 and 1440 px in both themes: a page loaded once and then
reloaded with the connection off showed the browser's own "No internet"
page, every time, on all four pages; Chrome found no service worker, and
the manifest's largest icon was 180 px (it asks for 192 and 512 to offer
an install).

Now the build publishes src/site/sw.js at the site's root, named for the
build; src/core/offline.js (on all four pages) registers it and, while the
browser has no connection, says the page is this device's saved copy. A
page is asked of the network first, so a visitor with a connection never
gets an old board.

Run with: pytest tests/test_offline_board.py -v
"""
import json
import re
import shutil
import struct
import subprocess
from pathlib import Path

import pytest

from src.site import build

ROOT = Path(__file__).resolve().parents[1]
SW = (ROOT / 'src' / 'site' / 'sw.js').read_text(encoding='utf-8')
OFF = (ROOT / 'src' / 'core' / 'offline.js').read_text(encoding='utf-8')
CSS = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
MANIFEST = json.loads((ROOT / 'assets' / 'site.webmanifest').read_text(encoding='utf-8'))
NODE = shutil.which('node')


def node(code):
    if not NODE:
        pytest.skip('node not available')
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def png_size(path):
    head = path.read_bytes()[:24]
    assert head[:8] == b'\x89PNG\r\n\x1a\n', f'{path.name} is not a PNG'
    return struct.unpack('>II', head[16:24])


# ---------- installable ----------

def test_the_manifest_offers_the_two_icon_sizes_an_install_needs():
    sizes = {i['sizes']: i['src'] for i in MANIFEST['icons'] if i.get('type') == 'image/png'}
    for n in (192, 512):
        src = sizes.get(f'{n}x{n}')
        assert src, f'no {n} px icon'
        assert png_size(ROOT / 'assets' / src) == (n, n), f'{src} is not {n} px'
        assert build.SHARED_FILES.get(f'assets/{src}') == f'assets/{src}', f'the build does not publish {src}'
    assert MANIFEST.get('id') == MANIFEST['start_url'], 'an install is known by its id'


# ---------- the worker ----------

def test_every_file_the_worker_keeps_is_one_the_build_publishes():
    files = re.search(r"const FILES = \[(.*?)\];", SW, re.S).group(1)
    for f in re.findall(r"'([^']+)'", files):
        assert f in build.SHARED_FILES, f'{f} would fail the install: the build does not publish it'
    assert "const PAGES = ['./', 'nfl/', 'nhl/', 'nba/'];" in SW


WORKER_HARNESS = r"""
const on = {}, store = new Map();
let online = true, served = 0;
const cache = {put: async (k, v) => { store.set(String(k), v); }, match: async k => store.get(String(k)), addAll: async () => {}};
global.self = {addEventListener: (t, f) => { on[t] = f; }, location: {origin: 'https://x.io'},
               registration: {scope: 'https://x.io/s/'}, skipWaiting(){}, clients: {claim(){}}};
global.caches = {open: async () => cache, match: async r => store.get(String(r.url || r)), keys: async () => []};
global.fetch = async req => {
  if(!online) throw new TypeError('offline');
  served += 1;
  const ok = !/broken/.test(req.url), body = `fresh ${served}`;
  return {ok, body, clone(){ return {ok, body}; }};
};
global.Response = {error: () => ({body: 'error page'})};
"""


def worker(steps):
    """Runs src/site/sw.js with a pretend network and cache, then `steps`."""
    return node(WORKER_HARNESS + SW + r"""
const tick = () => new Promise(r => setTimeout(r, 0));
async function ask(url, mode = 'navigate'){
  let answer = null;
  on.fetch({request: {method: 'GET', url, mode}, respondWith: p => { answer = p; }});
  if(!answer) return 'not handled';
  const r = await answer; await tick();
  return r.body;
}
(async () => { const out = []; """ + steps + """ console.log(JSON.stringify(out)); })();""")


def test_with_a_connection_the_page_is_always_the_networks():
    got = worker("out.push(await ask('https://x.io/s/nfl/#board/2026_week6'));"
                 "out.push(await ask('https://x.io/s/nfl/'));")
    assert got == ['fresh 1', 'fresh 2'], 'a visitor with a connection must never get the saved copy'


def test_without_one_the_last_copy_is_shown():
    got = worker("await ask('https://x.io/s/nfl/'); await ask('https://x.io/s/');"
                 "online = false;"
                 "out.push(await ask('https://x.io/s/nfl/#board/2026_week5'));"
                 "out.push(await ask('https://x.io/s/nba/'));")
    assert got == ['fresh 1', 'fresh 2'], 'the NFL its own copy; a page never seen, the home page'


def test_a_broken_page_does_not_replace_the_good_copy():
    got = worker("await ask('https://x.io/s/nfl/');"
                 "await ask('https://x.io/s/nfl/?broken');"
                 "online = false; out.push(await ask('https://x.io/s/nfl/'));")
    assert got == ['fresh 1']


def test_with_nothing_kept_the_browser_says_so():
    assert worker("online = false; out.push(await ask('https://x.io/s/nhl/'));") == ['error page']


def test_another_hosts_request_is_left_to_the_browser():
    got = worker("out.push(await ask('https://a.espncdn.com/i/teamlogos/nfl/500/kc.png', 'no-cors'));"
                 "out.push(await ask('https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard', 'cors'));")
    assert got == ['not handled', 'not handled']


def test_nothing_from_another_host_is_touched():
    fetch = SW[SW.index("self.addEventListener('fetch'"):]
    assert fetch.index('if(url.origin !== self.location.origin) return;') < fetch.index('e.respondWith'), \
        "ESPN's logos and live scores go to the network as before"
    assert "if(req.method !== 'GET') return;" in fetch


def test_a_new_build_drops_the_old_copies():
    act = SW[SW.index("self.addEventListener('activate'"):]
    assert "k.startsWith('sportalytics-') && k !== CACHE" in act and 'caches.delete(k)' in act
    assert 'self.clients.claim()' in act
    assert "self.skipWaiting()" in SW
    assert "const CACHE = `sportalytics-${SITE_BUILD}`;" in SW and "const SITE_BUILD = '__SITE_BUILD__';" in SW


def test_a_pages_copy_is_kept_under_its_address_without_the_route():
    fn = re.search(r'function pageKey\(.*?\n\}\n', SW, re.S).group(0)
    got = node(fn + 'console.log(JSON.stringify(["https://x.io/s/nfl/#board/2026_week6", "https://x.io/s/nhl/index.html?a=1",'
                    ' "https://x.io/s/"].map(pageKey)));')
    assert got == ['https://x.io/s/nfl/', 'https://x.io/s/nhl/', 'https://x.io/s/']


# ---------- the page ----------

def test_the_worker_is_found_from_the_pages_manifest_link():
    fn = re.search(r'function offlineBase\(.*?\n\}\n', OFF, re.S).group(0)
    got = node(fn + 'console.log(JSON.stringify(["../assets/site.webmanifest", "assets/site.webmanifest", "", null].map(offlineBase)));')
    assert got == ['../', '', None, None]


def test_it_registers_only_where_a_worker_can_run():
    run = OFF[OFF.index('(function(){'):]
    assert "(location.protocol === 'https:' || local)" in run
    assert 'navigator.serviceWorker.register(`${base}sw.js`, {scope: base || \'./\'}).catch(() => {});' in run


def test_with_no_connection_the_page_says_it_is_the_saved_copy():
    assert "OFFLINE_TEXT = \"You're offline. This is the last copy of the page saved on this device.\"" in OFF
    run = OFF[OFF.index('(function(){'):]
    assert "const off = navigator.onLine === false;" in run
    assert "note.setAttribute('role', 'status');" in run and 'note.textContent = OFFLINE_TEXT;' in run
    assert "window.addEventListener('online', show);" in run and "window.addEventListener('offline', show);" in run
    rules = re.sub(r'\s+', '', CSS)
    assert '.offline-note[hidden]{display:none;}' in rules
    assert '.offline-note{position:fixed;' in rules


# ---------- the build ----------

def site(tmp_path, nfl='<p>nfl</p>'):
    pages = {'index.html': '<p>home</p>', 'nfl/index.html': nfl, 'nhl/index.html': '<p>nhl</p>', 'nba/index.html': '<p>nba</p>'}
    for rel, body in pages.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        link = 'assets/site.webmanifest' if rel == 'index.html' else '../assets/site.webmanifest'
        (tmp_path / rel).write_text(f'<html><head><link rel="manifest" href="{link}"></head><body>{body}</body></html>',
                                    encoding='utf-8')
    return tmp_path


def test_the_build_puts_the_script_on_all_four_pages_once_and_the_worker_at_the_root(tmp_path):
    out = site(tmp_path)
    assert build.add_offline(out) == ['index.html', 'nfl/index.html', 'nhl/index.html', 'nba/index.html']
    first = (out / 'sw.js').read_text(encoding='utf-8')
    build.add_offline(out)
    for rel in ('index.html', 'nfl/index.html'):
        html = (out / rel).read_text(encoding='utf-8')
        assert html.count('<script data-site-offline>') == 1, f'{rel}: a second build replaces, not adds'
        assert html.index('data-site-offline') < html.index('</body>')
    worker = (out / 'sw.js').read_text(encoding='utf-8')
    assert '__SITE_BUILD__' not in worker and re.search(r"const SITE_BUILD = '[0-9a-f]{16}';", worker)
    assert worker == first, 'the same pages make the same worker'


def test_a_changed_page_makes_a_new_worker(tmp_path):
    a, b = tmp_path / 'a', tmp_path / 'b'
    build.add_offline(site(a))
    build.add_offline(site(b, nfl='<p>week 7</p>'))
    assert (a / 'sw.js').read_text(encoding='utf-8') != (b / 'sw.js').read_text(encoding='utf-8')


def test_a_page_without_the_manifest_link_gets_nothing(tmp_path):
    page = tmp_path / 'p.html'
    page.write_text('<html><body>x</body></html>', encoding='utf-8')
    assert not build.inject_offline(page, build.offline_block())
    assert not build.inject_offline(tmp_path / 'missing.html', build.offline_block())


def test_the_site_build_adds_it_last():
    src = Path(build.__file__).read_text(encoding='utf-8')
    assert '    add_expand(out)\n    add_offline(out)\n    return results' in src, \
        'last, so the worker is named for the pages as published'
