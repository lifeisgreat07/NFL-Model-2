"""A column beside the day board at 1280 px and wider (Stage 79 item 48, the 2026-10-13 UI/UX audit's B3 and L3).

The NBA's board sat at 760 px in a 1124 px column with nothing beside it at
1440; the NHL's column (Stage 68 item 37) had no height cap, so a long day
ran past the sticky top. This opens the NBA page and the NHL's sample page
at 1279, 1280 and 1440 px, dark and light, and fails unless the column is
hidden below 1280 and, at 1280 and wider, sits beside the board without
overlapping it, starts within the window and is no taller than the window
less 40 px (it scrolls inside itself past that). The NBA's must say who is
out; the clock is fixed before opening night, so it says no pick is saved.

`--self-test` takes the column's markup out of a copy of the NBA page and
the height cap out of a copy of the NHL page, and fails unless both are
reported.

Usage:
  python tests/browser/check_side_column.py <nba page.html> <nhl page.html>
  python tests/browser/check_side_column.py --self-test --tmp <dir>
"""
import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
CLOCK = '2026-10-13T17:00:00Z'
MEASURE = """(sel) => { const s = document.querySelector(sel), g = document.getElementById('game-grid');
  if(!s) return null;
  const cs = getComputedStyle(s), r = s.getBoundingClientRect(), b = g.getBoundingClientRect();
  return {shown: cs.display !== 'none', left: r.left, right: r.right, top: r.top, height: r.height,
          cap: cs.maxHeight, overflow: cs.overflowY, boardRight: b.right, text: s.innerText}; }"""


async def check_pages(nba, nhl):
    report = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for sport, path, sel in (('NBA', nba, '#nba-side'), ('NHL', nhl, '#nhl-side')):
            uri = Path(path).resolve().as_uri()
            for theme in ('dark', 'light'):
                for width in (1279, 1280, 1440):
                    # A short window, so a column without its cap runs past it.
                    height = 480 if sport == 'NHL' else 900
                    where = f'[{sport} {theme} {width}x{height}]'
                    ctx = await browser.new_context(viewport={'width': width, 'height': height}, color_scheme=theme)
                    page = await ctx.new_page()
                    await page.clock.set_fixed_time(CLOCK)
                    await page.route(lambda u: u.startswith(('http://', 'https://')), lambda r: r.abort())
                    await page.goto(uri)
                    await page.wait_for_timeout(200)
                    m = await page.evaluate(MEASURE, sel)
                    await ctx.close()
                    if m is None:
                        report.append(f'{where} the page has no column beside the board')
                        continue
                    if width < 1280:
                        if m['shown']:
                            report.append(f'{where} the column shows below 1280 px')
                        continue
                    if not m['shown']:
                        report.append(f'{where} the column is hidden')
                        continue
                    if m['left'] < m['boardRight']:
                        report.append(f'{where} the column overlaps the board ({m["left"]:.0f} < {m["boardRight"]:.0f})')
                    if m['height'] > height - 40 + 1:
                        report.append(f'{where} the column is {m["height"]:.0f} px tall in a {height} px window')
                    if sport == 'NBA' and 'who is out' not in m['text'].lower():
                        report.append(f'{where} the column does not say who is out')
        await browser.close()
    return report


NBA_ASIDE = '      <aside class="nba-side" id="nba-side" aria-label="This day at a glance"></aside>\n'
NHL_CAP = 'max-height:calc(100vh - var(--s8)); overflow:auto;'


def self_test(tmp):
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    nba, nhl = tmp / 'side-nba.html', tmp / 'side-nhl.html'
    subprocess.run([sys.executable, '-m', 'src.sports.nba.site', '--out', str(nba)], cwd=ROOT, check=True, capture_output=True)
    subprocess.run([sys.executable, 'tests/browser/build_nhl.py', '--out', str(nhl)], cwd=ROOT, check=True, capture_output=True)
    a, b = nba.read_text(encoding='utf-8'), nhl.read_text(encoding='utf-8')
    if a.count(NBA_ASIDE) != 1 or b.count(NHL_CAP) != 1:
        return [f'self-test: {a.count(NBA_ASIDE)} NBA columns and {b.count(NHL_CAP)} NHL caps, expected 1 each']
    nba_bad, nhl_bad = tmp / 'side-nba-old.html', tmp / 'side-nhl-old.html'
    nba_bad.write_text(a.replace(NBA_ASIDE, ''), encoding='utf-8')
    nhl_bad.write_text(b.replace(NHL_CAP, ''), encoding='utf-8')
    problems = [f'self-test: the real pages should be clean: {r}' for r in asyncio.run(check_pages(nba, nhl))]
    bad = asyncio.run(check_pages(nba_bad, nhl_bad))
    if not any(r.startswith('[NBA') and 'no column' in r for r in bad):
        problems.append('self-test: the NBA page without its column was not reported')
    if not any(r.startswith('[NHL') and 'px tall' in r for r in bad):
        problems.append('self-test: the NHL column without its cap was not reported')
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pages', nargs='*')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--tmp')
    a = ap.parse_args()
    report = self_test(a.tmp) if a.self_test else asyncio.run(check_pages(*a.pages))
    for line in report:
        print(line)
    print('OK' if not report else f'{len(report)} problem(s)')
    return 1 if report else 0


if __name__ == '__main__':
    sys.exit(main())
