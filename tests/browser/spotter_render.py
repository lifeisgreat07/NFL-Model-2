"""Spotter's pictures of the built site (Stage 43 item 2).

Takes the pages a change touches as the visitor sees them and writes one
PNG for each page, viewport and theme, plus `renders.json` naming them. The
render job runs it once over the pull request's head and once over its base,
so a reader can look at what changed and not only at a state.

    python tests/browser/spotter_render.py --site <built site dir> \\
        --pages nfl,nhl --label head --out <dir> --clock 2026-10-17T12:00:00Z

What makes two renders of the same page the same picture:

* the clock is fixed (`--clock`), so a countdown or a "today" in the page
  reads the same in the head's render and the base's;
* the time zone is UTC and the locale en-US;
* motion is reduced and the network blocked except the local server, so a
  logo that loads on one run and not the next cannot move the layout;
* the viewport is one of two, named in every file: 390x844 (a phone) and
  1440x900 (a desktop), each in the light and the dark theme.

No pixel is compared. The pictures are for reading (decision record 0007);
a pixel gate fails on font hinting and antialiasing, which is why the
browser checks decided against one.

A render fails, so the run fails, rather than writing a picture of nothing:
a page that does not answer 200, a page that throws, or a picture too small
to be a page.
"""
import argparse
import asyncio
import functools
import http.server
import json
import sys
import threading
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

#: (width, height), the two sizes every comment names.
VIEWPORTS = ((390, 844), (1440, 900))
SCHEMES = ('light', 'dark')
#: Where each page is served under the site's root (src/agents/spotter_pages.py
#: holds the same map for the files that feed them).
SITE_PATH = {'home': '', 'nfl': 'nfl/', 'nhl': 'nhl/', 'nba': 'nba/'}
#: A picture under this is a blank page, not a render of one.
MIN_BYTES = 8_000
#: A full-page picture is taken past the bottom of the viewport, where a panel the
#: page parks just off-screen (the phone's More sheet) would show as if it were
#: open. Fixed elements entirely outside the viewport at rest are hidden first,
#: and how many is written in the manifest.
PARK_JS = """
() => {
  let n = 0;
  for (const el of document.querySelectorAll('body *')) {
    if (getComputedStyle(el).position !== 'fixed') continue;
    const r = el.getBoundingClientRect();
    if (r.top >= innerHeight || r.bottom <= 0 || r.left >= innerWidth || r.right <= 0) {
      el.style.visibility = 'hidden';
      n += 1;
    }
  }
  return n;
}
"""


def picture_name(page: str, width: int, height: int, scheme: str, label: str) -> str:
    """`nfl-390x844-dark-head.png`: everything a reader needs to cite it."""
    return f'{page}-{width}x{height}-{scheme}-{label}.png'


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(root: Path):
    handler = functools.partial(Quiet, directory=str(root))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f'http://127.0.0.1:{server.server_address[1]}/'


async def render(site: Path, pages: list[str], label: str, out: Path, clock: datetime) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    server, base = serve(site)
    made: list[dict] = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            for page_name in pages:
                if not (site / SITE_PATH[page_name] / 'index.html').exists():
                    # The base has no such page when the change adds it.
                    made.append({'page': page_name, 'label': label, 'missing': True})
                    continue
                for width, height in VIEWPORTS:
                    for scheme in SCHEMES:
                        ctx = await browser.new_context(
                            viewport={'width': width, 'height': height}, color_scheme=scheme,
                            reduced_motion='reduce', locale='en-US', timezone_id='UTC',
                            device_scale_factor=1, has_touch=width < 768, is_mobile=width < 768)
                        await ctx.clock.set_fixed_time(clock)
                        page = await ctx.new_page()
                        errors: list[str] = []
                        page.on('pageerror', lambda e, errors=errors: errors.append(str(e)))
                        await page.route(lambda u: not u.startswith(base), lambda r: r.abort())
                        resp = await page.goto(base + SITE_PATH[page_name])
                        if resp is None or resp.status != 200:
                            raise SystemExit(f'{page_name}: the page answered {resp.status if resp else "nothing"}')
                        await page.wait_for_load_state('load')
                        await page.evaluate('document.fonts.ready')
                        parked = await page.evaluate(PARK_JS)
                        name = picture_name(page_name, width, height, scheme, label)
                        shot = await page.screenshot(path=str(out / name), full_page=True)
                        if errors:
                            raise SystemExit(f'{name}: the page threw: {errors[0]}')
                        if len(shot) < MIN_BYTES:
                            raise SystemExit(f'{name}: {len(shot)} bytes, too small to be a page')
                        made.append({'page': page_name, 'label': label, 'viewport': f'{width}x{height}',
                                     'theme': scheme, 'file': name, 'bytes': len(shot), 'parked': parked})
                        await ctx.close()
            await browser.close()
    finally:
        server.shutdown()
    return made


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else '')
    ap.add_argument('--site', required=True, type=Path, help='a site built by src/site/build.py')
    ap.add_argument('--pages', required=True, help='comma-separated: home, nfl, nhl, nba')
    ap.add_argument('--label', required=True, choices=('head', 'base'))
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--clock', required=True, help='the instant the page believes it is, ISO 8601 with Z')
    args = ap.parse_args(argv)
    pages = [p for p in args.pages.split(',') if p]
    unknown = [p for p in pages if p not in SITE_PATH]
    if unknown:
        print(f'unknown page(s): {", ".join(unknown)}', file=sys.stderr)
        return 2
    clock = datetime.fromisoformat(args.clock.replace('Z', '+00:00'))
    made = asyncio.run(render(args.site, pages, args.label, args.out, clock))
    (args.out / f'renders-{args.label}.json').write_text(json.dumps(made, indent=1) + '\n', encoding='utf-8')
    print(f'{sum(1 for m in made if "file" in m)} pictures, {sum(1 for m in made if m.get("missing"))} page(s) absent')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
