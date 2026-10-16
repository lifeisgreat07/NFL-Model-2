"""A card's markers sit on its bar's own axis (Stage 75 item 1, from the 2026-10-13 UI/UX audit).

The card's split bar draws the away team first, `100 - lead` wide, so the
split sits at the away team's share from the left. Every marker was placed
at `left: <home share>%`, the other way round: on SEA at DEN (DEN 44.3%) the
split was at 116.0 px of a 208.3 px track and the Model B marker at 92.3 px
(measured 2026-10-13 at 1440x900). The same component is copied into the
NHL's and NBA's cards.

This opens each page at 390 and 1440 px, dark and light, presses every day
chip and opens every row, and for every card it can see measures the split
(the second segment's left edge) against the centre of the lead model's
marker: Model B's, or Model A's when a card has no Model B. They must be
within 1 px. A page with no card to measure is a failure, not a pass.

`--self-test` writes the old marker position back into a copy of the NFL
page and fails unless the gap is reported.

Usage:
  python tests/browser/check_card_axis.py <page.html> [<page.html> ...]
  python tests/browser/check_card_axis.py --self-test --tmp <dir>
"""
import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
WIDTHS = (390, 1440)
THEMES = ('dark', 'light')
TOLERANCE = 1.0
ROWS = '.nfl-row, .nhl-row, .nba-row'
#: How many rows can be seen, and a click on the n-th of them.
OPEN_ROWS_JS = f"() => [...document.querySelectorAll('{ROWS}')].filter(r => r.offsetParent).length"
CLICK_ROW_JS = f"""(n) => {{
  const r = [...document.querySelectorAll('{ROWS}')].filter(r => r.offsetParent)[n];
  if (r && r.getAttribute('aria-expanded') !== 'true') r.click();
}}"""
MEASURE_JS = """() => {
  const out = [];
  for (const viz of document.querySelectorAll('.card-viz')) {
    const segs = viz.querySelectorAll('.tele-bar-seg');
    if (segs.length < 2 || viz.getBoundingClientRect().width === 0) continue;
    const mk = viz.querySelector('.card-mk[data-series="b"]') || viz.querySelector('.card-mk[data-series="a"]');
    const split = segs[1].getBoundingClientRect().left;
    if (!mk) { out.push({label: viz.querySelector('.card-scale').getAttribute('aria-label'), split, centre: null}); continue; }
    const r = mk.getBoundingClientRect();
    out.push({label: viz.querySelector('.card-scale').getAttribute('aria-label'), split, centre: (r.left + r.right) / 2});
  }
  return out;
}"""


async def measure(page):
    """Every card on the page: each day chip pressed, then each visible row
    opened in turn and the cards measured after every open (a board may
    close one row when it opens another)."""
    seen = {}

    async def collect():
        for m in await page.evaluate(MEASURE_JS):
            seen[(m['label'], round(m['split']))] = m

    chips = page.locator('.nhl-day-chip, .nba-day-chip')
    for i in range(max(await chips.count(), 1)):
        if await chips.count():
            await chips.nth(i).click()
            await page.wait_for_timeout(50)
        await collect()
        rows = await page.evaluate(OPEN_ROWS_JS)
        for n in range(rows):
            await page.evaluate(CLICK_ROW_JS, n)
            await page.wait_for_timeout(20)
            await collect()
    return list(seen.values())


async def check_pages(paths):
    report = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for path in paths:
            for theme in THEMES:
                for width in WIDTHS:
                    where = f'[{Path(path).parent.name}/{Path(path).name} {theme} {width}]'
                    ctx = await browser.new_context(viewport={'width': width, 'height': 900},
                                                    color_scheme=theme, reduced_motion='reduce')
                    page = await ctx.new_page()
                    errors = []
                    page.on('pageerror', lambda e: errors.append(str(e)))
                    await page.route(lambda u: u.startswith(('http://', 'https://')), lambda r: r.abort())
                    await page.goto(Path(path).resolve().as_uri())
                    await page.wait_for_timeout(300)
                    cards = await measure(page)
                    print(f'{where} {len(cards)} cards measured')
                    if not cards:
                        report.append(f'{where} no card to measure')
                    for c in cards:
                        if c['centre'] is None:
                            report.append(f'{where} {c["label"]}: no Model B or Model A marker')
                        elif abs(c['centre'] - c['split']) > TOLERANCE:
                            report.append(f'{where} {c["label"]}: split at {c["split"]:.1f}, '
                                          f'lead marker at {c["centre"]:.1f} ({abs(c["centre"] - c["split"]):.1f} px)')
                    report += [f'{where} page error: {e}' for e in errors]
                    await ctx.close()
        await browser.close()
    return report


#: The marker position before Stage 75 item 1, and now.
OLD = 'left:${vals[k]}%;'
NEW = 'left:${100 - vals[k]}%;'


def self_test(tmp):
    """The old position written back into a built NFL page must be reported."""
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, '-m', 'src.site.build', '--out', str(tmp / 'axis-site')],
                   cwd=ROOT, check=True, capture_output=True)
    out = tmp / 'axis-site' / 'nfl' / 'index.html'
    html = out.read_text(encoding='utf-8')
    if html.count(NEW) != 1:
        return [f'self-test: the page holds {html.count(NEW)} copies of the marker position, expected 1']
    bad = tmp / 'axis-nfl-old.html'
    bad.write_text(html.replace(NEW, OLD), encoding='utf-8')
    clean = asyncio.run(check_pages([out]))
    broken = asyncio.run(check_pages([bad]))
    problems = [f'self-test: the real page should be clean: {r}' for r in clean]
    if not any('lead marker at' in r for r in broken):
        problems.append('self-test: the old marker position was not reported')
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pages', nargs='*')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--tmp')
    a = ap.parse_args()
    report = self_test(a.tmp) if a.self_test else asyncio.run(check_pages(a.pages))
    for line in report:
        print(line)
    print('OK' if not report else f'{len(report)} problem(s)')
    return 1 if report else 0


if __name__ == '__main__':
    sys.exit(main())
