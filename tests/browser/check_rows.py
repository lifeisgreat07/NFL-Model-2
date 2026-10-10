"""The day boards' rows, measured in Chromium: no cell drawn over another (Stage 68 item 5).

The 2026-10-09 audit measured the NBA's pick ("—") drawn 13 px into
"Locks 5:30 PM" on a phone: the result column was a fixed 4.4rem (70 px)
and that label is 89 px, unwrapped and pushed to the column's end. This
opens the NBA page at 320, 390 and 1280 px, dark and light, with the clock
fixed before opening night (so the rows carry their "Locks …" labels),
and reports any two cells of one row whose boxes overlap, and the page
wider than the window.

`--self-test` writes the old fixed column back into a copy of the page and
fails unless the overlap is reported; the real page must come back clean.

Usage:
  python tests/browser/check_rows.py <nba page.html>
  python tests/browser/check_rows.py --self-test --tmp <dir>
"""
import argparse
import asyncio
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
WIDTHS = (320, 390, 1280)
THEMES = ('dark', 'light')
#: Before opening night, when every row of the first day says when it locks.
CLOCK = datetime(2026, 10, 10, 16, 0, tzinfo=UTC)
OVERLAP_JS = """() => {
  const out = [];
  for (const row of document.querySelectorAll('.nba-row, .nhl-row')) {
    const cells = [...row.children].filter(c => c.getBoundingClientRect().width > 0);
    for (let i = 0; i < cells.length; i++) for (let j = i + 1; j < cells.length; j++) {
      const a = cells[i].getBoundingClientRect(), b = cells[j].getBoundingClientRect();
      const x = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const y = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (x > 0.5 && y > 0.5) out.push(`${row.innerText.replace(/\\n/g, ' | ')}: ${cells[i].className} and ${cells[j].className} overlap ${x.toFixed(0)}px`);
    }
  }
  return {rows: document.querySelectorAll('.nba-row, .nhl-row').length, out,
          wide: document.documentElement.scrollWidth > window.innerWidth + 1};
}"""


async def check_page(path):
    report = []
    url = Path(path).resolve().as_uri()
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for theme in THEMES:
            for width in WIDTHS:
                where = f'[{theme} {width}]'
                ctx = await browser.new_context(viewport={'width': width, 'height': 900}, color_scheme=theme,
                                                reduced_motion='reduce')
                page = await ctx.new_page()
                await page.clock.set_fixed_time(CLOCK)
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)))
                await page.route(lambda u: u.startswith(('http://', 'https://')), lambda r: r.abort())
                await page.goto(url)
                await page.wait_for_timeout(200)
                r = await page.evaluate(OVERLAP_JS)
                if not r['rows']:
                    report.append(f'{where} no rows to measure')
                report += [f'{where} {o}' for o in r['out']]
                if r['wide']:
                    report.append(f'{where} the page is wider than the window')
                report += [f'{where} page error: {e}' for e in errors]
                await ctx.close()
        await browser.close()
    return report


#: The phone rule as it was before Stage 68 item 5, and as it is now.
OLD = 'grid-template-columns:3.7rem minmax(0, 1fr) auto 4.4rem 14px;'
NEW = 'grid-template-columns:3.7rem minmax(0, 1fr) auto minmax(4.4rem, max-content) 14px;'


async def self_test(tmp):
    real = Path(tmp) / 'nba_rows_real.html'
    r = subprocess.run([sys.executable, '-m', 'src.sports.nba.site', '--out', str(real)], cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f'could not build the NBA page: {r.stderr[-800:]}')
    html = real.read_text(encoding='utf-8')
    failed = []
    if html.count(NEW) != 1:
        print(f'self-test old-column: ANCHOR ({html.count(NEW)} matches)')
        failed.append('anchor')
    else:
        broken = Path(tmp) / 'nba_rows_old.html'
        broken.write_text(html.replace(NEW, OLD), encoding='utf-8')
        hit = [x for x in await check_page(broken) if 'overlap' in x]
        print(f"self-test old-column: {'caught' if hit else 'MISSED'} ({len(hit)} overlap(s))")
        if not hit:
            failed.append('old-column')
    report = await check_page(real)
    print(f"self-test real page: {'FALSE ALARM' if report else 'clean'} ({len(report)} finding(s))")
    for line in report[:10]:
        print('  ' + line)
    if report:
        failed.append('real')
    return failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('page', nargs='?')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--tmp', default='.')
    a = ap.parse_args()
    if a.self_test:
        failed = asyncio.run(self_test(a.tmp))
        if failed:
            print(f'SELF-TEST FAILED: {failed}')
            sys.exit(1)
        print('self-test: the old column caught, the real page clean')
        return
    if not a.page:
        ap.error('give the NBA page, or --self-test')
    report = asyncio.run(check_page(a.page))
    for line in report:
        print(line)
    if report:
        print(f'{len(report)} finding(s)')
        sys.exit(1)
    print(f'{a.page}: no row draws one cell over another at {", ".join(map(str, WIDTHS))}px in both themes')


if __name__ == '__main__':
    main()
