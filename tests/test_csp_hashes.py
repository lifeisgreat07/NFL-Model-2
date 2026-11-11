"""
Stage 88 item 5 (the 2026-11-02 review): the pages' Content-Security-Policy
lists the hash of each inline script instead of 'unsafe-inline'.

A browser then runs the scripts the build wrote and nothing else: an inline
script or event handler injected through a data field is refused (checked in
Chromium for the PR). So no page carries an inline handler; buttons carry
`data-act` and logos `data-hide-on-error`, and each page's script attaches
the listeners.

Run with: pytest tests/test_csp_hashes.py -v
"""
import base64
import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.core import csp
from src.site import build

ROOT = Path(__file__).resolve().parents[1]
POLICY = ("default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self'")


def page(*scripts, head=''):
    meta = f'<meta http-equiv="Content-Security-Policy" content="{POLICY}">'
    return f'<html><head>{meta}{head}</head><body>' + ''.join(scripts) + '</body></html>'


def sha(text):
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode('utf-8')).digest()).decode() + "'"


def script_src(html):
    (m,) = csp.CSP_RE.finditer(html)
    (src,) = re.findall(r'script-src ([^;]*)', m.group('policy'))
    return src.split()


# --- the hardening ---------------------------------------------------------------

def test_each_runnable_inline_script_is_named_by_its_hash():
    a, b = 'const x = 1;\n', "document.title = 'é';"
    html = csp.harden(page(f'<script>{a}</script>', f'<script type="module">{b}</script>'))
    assert script_src(html) == [sha(a), sha(b)]
    assert "'unsafe-inline'" in html.split('style-src', 1)[1], 'styles keep unsafe-inline'


def test_data_blocks_and_external_scripts_are_not_listed():
    data = '<script type="application/ld+json">{"a": 1}</script><script type="application/json">[1]</script>'
    html = csp.harden(page('<script>run()</script>', head=data + '<script src="x.js"></script>'))
    assert script_src(html) == [sha('run()')]


def test_a_page_with_no_script_runs_none_and_a_repeat_is_named_once():
    assert script_src(csp.harden(page())) == ["'none'"]
    assert script_src(csp.harden(page('<script>a()</script>', '<script>a()</script>'))) == [sha('a()')]


def test_hardening_again_recomputes_from_the_page_as_it_stands():
    once = csp.harden(page('<script>a()</script>'))
    twice = csp.harden(once.replace('</body>', '<script>b()</script></body>'))
    assert script_src(twice) == [sha('a()'), sha('b()')]
    assert csp.harden(once) == once


@pytest.mark.parametrize('bad, says', [
    (page('<button onclick="go()">x</button>'), 'inline event handler'),
    (page('<script>el.innerHTML = `<img src=x onerror="hide(this)">`</script>'), 'inline event handler'),
    ('<html><body><script>a()</script></body></html>', 'found 0'),
    (page() + page(), 'found 2'),
])
def test_a_page_that_cannot_be_hardened_is_refused(bad, says):
    with pytest.raises(csp.CSPError, match=says):
        csp.harden(bad)


def test_javascript_that_only_looks_like_a_handler_is_not_refused():
    js = 'const one = 1; img.onerror = () => hide(img); if (a<b && onload) x();'
    assert script_src(csp.harden(page(f'<script>{js}</script>'))) == [sha(js)]


# --- every page writer hardens ----------------------------------------------------

def check_written(html):
    assert "script-src 'unsafe-inline'" not in html
    assert script_src(html) == list(dict.fromkeys(sha(s) for s in csp.inline_scripts(html)))
    assert len(script_src(html)) >= 1


def test_the_nhl_and_nba_pages_are_hardened():
    from src.sports.nba import site as nba
    from src.sports.nhl import site as nhl
    now = datetime.now(UTC)
    check_written(nba.render(nba.payload(now)))
    check_written(nhl.render(nhl.payload(nhl.current_season(now), now)))


def test_the_home_page_is_hardened():
    from src.site import home
    check_written(home.render(home.facts(ROOT, datetime.now(UTC))))


def test_the_nfl_page_is_hardened_before_it_is_written():
    src = (ROOT / 'src' / 'sports' / 'nfl' / 'generate_dashboard.py').read_text(encoding='utf-8')
    assert src.index('    html = page_render.finish(read_template(), fills)') < src.index(
        "    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:")
    # The shared renderer's finish hashes the scripts in (Stage 87 item 3).
    core = (ROOT / 'src' / 'core' / 'page_render.py').read_text(encoding='utf-8')
    assert '    return csp.harden(fill(strip_page_comments(template), fills))\n' in core


def test_the_site_build_rehardens_after_its_last_injection(tmp_path):
    (tmp_path / 'nba').mkdir()
    (tmp_path / 'nba' / 'index.html').write_text(page('<script>a()</script>', '<script>b()</script>'),
                                               encoding='utf-8')
    (tmp_path / 'redirect.html').write_text('<html><body>no policy</body></html>', encoding='utf-8')
    assert build.add_csp(tmp_path) == ['nba/index.html']
    assert script_src((tmp_path / 'nba' / 'index.html').read_text(encoding='utf-8')) == [sha('a()'), sha('b()')]
    src = Path(build.__file__).read_text(encoding='utf-8')
    body = src[src.index('def build_site('):src.index('def report(')]
    assert body.index('    add_expand(out)\n') < body.index('    add_csp(out)\n') < body.index('    add_offline(out)\n')


def test_the_offline_script_is_hashed_and_the_worker_is_named_for_the_hardened_pages(tmp_path):
    for rel in ('index.html', 'nfl/index.html', 'nhl/index.html', 'nba/index.html'):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(page('<script>a()</script>', head='<link rel="manifest" href="assets/site.webmanifest">'),
                                    encoding='utf-8')
    build.add_csp(tmp_path)
    build.add_offline(tmp_path)
    html = (tmp_path / 'nba' / 'index.html').read_text(encoding='utf-8')
    assert script_src(html) == list(dict.fromkeys(sha(s) for s in csp.inline_scripts(html)))
    assert len(script_src(html)) == 2, 'the page script and the offline script'
    digest = hashlib.sha256()
    for rel in ('index.html', 'nfl/index.html', 'nhl/index.html', 'nba/index.html'):
        digest.update((tmp_path / rel).read_bytes())
    assert digest.hexdigest()[:16] in (tmp_path / 'sw.js').read_text(encoding='utf-8')


# --- no inline handlers anywhere a page is made from --------------------------------

SOURCES = [p for p in (ROOT / 'src').rglob('*') if p.suffix in ('.html', '.js') and p.is_file()]


def test_no_page_source_carries_an_inline_handler():
    found = [f'{p.relative_to(ROOT).as_posix()}: {m.group(0)}' for p in SOURCES
             for m in csp.HANDLER_RE.finditer(p.read_text(encoding='utf-8'))]
    assert found == []


def test_every_nfl_button_action_is_one_the_page_knows():
    app = (ROOT / 'src' / 'dashboard' / 'app.js').read_text(encoding='utf-8')
    table = app[app.index('const ACTIONS = {'):app.index('};', app.index('const ACTIONS = {'))]
    known = set(re.findall(r"^  '([a-z-]+)': ", table, re.M))
    used = set(re.findall(r'data-act="([a-z-]+)"', (ROOT / 'src' / 'dashboard' / 'body.html').read_text(encoding='utf-8')))
    used |= set(re.findall(r"act: '([a-z-]+)'", app))
    assert used and used <= known, used - known
    assert "document.addEventListener('click', e => {" in app and 'ACTIONS[b.dataset.act](b)' in app


@pytest.mark.parametrize('rel', ['src/dashboard/app.js', 'src/sports/nba/pages/nba.js', 'src/sports/nhl/pages/nhl.js'])
def test_each_page_with_logos_hides_a_broken_one_by_listener(rel):
    js = (ROOT / rel).read_text(encoding='utf-8')
    assert 'data-hide-on-error' in js
    assert ("document.addEventListener('error', e => {\n  const t = e.target;\n"
            "  if (t instanceof HTMLImageElement && t.hasAttribute('data-hide-on-error')) t.style.display = 'none';\n"
            "}, true);") in js
