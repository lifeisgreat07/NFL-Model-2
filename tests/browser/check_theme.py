"""The light/dark choice follows the visitor from page to page (Stage 62 items 1 and 4).

Each page had its own storage key from Stage 53 to Stage 62, so choosing
light on the NFL's page left the NHL's dark. Now every page reads and writes
`site:theme` (src/core/isolation.py's SHARED_STORAGE_KEYS). A static read can
see the key in the source; only a browser can see the choice survive the walk
from one page to the next, which is what a visitor does.

What this does, over a site built by `python -m src.site.build --out <dir>`:
serve the folder on localhost (one origin, as GitHub Pages is), then, once
with the system set to dark and once with it set to light, press the theme
button on each sport's page in turn and visit every page. Each page must show
the theme just chosen. The home page has no button; it must follow too.

--self-test builds two small sites first: one whose pages each keep their
own key (the defect before Stage 62), which the check must report, and one
that shares a key, which it must pass. A check that cannot fail proves
nothing (CLAUDE.md, mutation-test every guard).

Usage:
  python tests/browser/check_theme.py <site dir>
  python tests/browser/check_theme.py --self-test --tmp <dir>
"""
import argparse
import asyncio
import functools
import http.server
import sys
import threading
from pathlib import Path

from playwright.async_api import async_playwright

#: Every page of the built site, by its path under the site's root.
PAGES = ('', 'nfl/', 'nhl/', 'nba/')
#: The pages with a theme button. The home page has none and must still follow.
TOGGLE_PAGES = ('nfl/', 'nhl/', 'nba/')
THEME_JS = "document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark'"
# The button's own click handler, called directly: this check is about where
# the choice goes, not whether the button is on screen (check_page.py's
# target and focus rules look at that, at every width).
TOGGLE_JS = """() => {
  const b = document.querySelector('#theme-toggle, .topbar-theme');
  if(!b) return false;
  b.click();
  return true;
}"""


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(root: Path):
    handler = functools.partial(Quiet, directory=str(root))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f'http://127.0.0.1:{server.server_address[1]}/'


async def theme_of(page, url):
    await page.goto(url)
    await page.wait_for_load_state('load')
    return await page.evaluate(THEME_JS)


async def check_site(root, pages=PAGES, toggle_pages=TOGGLE_PAGES):
    report = []
    server, base = serve(Path(root))
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            for scheme in ('dark', 'light'):
                # A fresh context per system setting: nothing stored yet.
                ctx = await browser.new_context(viewport={'width': 1280, 'height': 900},
                                                color_scheme=scheme, reduced_motion='reduce')
                page = await ctx.new_page()
                await page.route(lambda u: not u.startswith(base), lambda r: r.abort())
                for start in toggle_pages:
                    before = await theme_of(page, base + start)
                    if not await page.evaluate(TOGGLE_JS):
                        report.append(f'[{scheme} system] {start or "home"}: no theme button to press')
                        continue
                    chosen = await page.evaluate(THEME_JS)
                    if chosen == before:
                        report.append(f'[{scheme} system] {start}: the button did not change the theme')
                        continue
                    for other in pages:
                        got = await theme_of(page, base + other)
                        if got != chosen:
                            report.append(f'[{scheme} system] chose {chosen} on {start}, '
                                          f'then {other or "home"} showed {got}')
                await ctx.close()
            await browser.close()
    finally:
        server.shutdown()
    return report


# ---------------------------------------------------------------- self-test
FIXTURE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{name}</title>
<script>(function(){{try{{var s=localStorage.getItem('{key}');
if(!s&&matchMedia('(prefers-color-scheme: light)').matches)s='light';
if(s==='light')document.documentElement.setAttribute('data-theme','light');}}catch(e){{}}}})();</script>
</head><body><h1>{name}</h1>{button}
<script>var b=document.getElementById('theme-toggle');if(b)b.addEventListener('click',function(){{
var n=document.documentElement.getAttribute('data-theme')==='light'?'dark':'light';
if(n==='light')document.documentElement.setAttribute('data-theme','light');
else document.documentElement.removeAttribute('data-theme');
localStorage.setItem('{key}',n);}});</script></body></html>"""
BUTTON = '<button id="theme-toggle" type="button">Theme</button>'


def build_fixture(root: Path, shared: bool) -> Path:
    for path in PAGES:
        name = path.rstrip('/') or 'home'
        key = 'site:theme' if shared else f'{name}:theme'
        folder = root / path
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'index.html').write_text(
            FIXTURE.format(name=name, key=key, button=BUTTON if path in TOGGLE_PAGES else ''),
            encoding='utf-8')
    return root


async def self_test(tmp: Path):
    failed = []
    own = await check_site(build_fixture(tmp / 'theme_own_keys', shared=False))
    print(f"self-test own-keys: {'caught' if own else 'MISSED'} ({len(own)} finding(s))")
    if not own:
        failed.append('own-keys')
    one = await check_site(build_fixture(tmp / 'theme_one_key', shared=True))
    print(f"self-test one-key: {'FALSE ALARM' if one else 'clean'} ({len(one)} finding(s))")
    if one:
        failed.append('one-key')
        for line in one:
            print('  ' + line)
    return failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('site', nargs='?', help='a folder built by python -m src.site.build --out <dir>')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--tmp', default='.')
    a = ap.parse_args()
    if a.self_test:
        failed = asyncio.run(self_test(Path(a.tmp)))
        if failed:
            print(f'SELF-TEST FAILED: {failed}')
            sys.exit(1)
        print('self-test: the check catches pages with their own keys and passes a shared one')
        return
    if not a.site:
        ap.error('give the built site folder, or --self-test')
    missing = [p or 'home' for p in PAGES if not (Path(a.site) / p / 'index.html').is_file()]
    if missing:
        print(f'{a.site}: no index.html for {missing}; build the whole site first')
        sys.exit(1)
    report = asyncio.run(check_site(a.site))
    for line in report:
        print(line)
    if report:
        print(f'{len(report)} finding(s)')
        sys.exit(1)
    print(f'{a.site}: the theme chosen on each sport\'s page holds on every page, '
          'with the system set to dark and to light')


if __name__ == '__main__':
    main()
