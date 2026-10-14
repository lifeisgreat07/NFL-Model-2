"""Open rows stay open when a day board is drawn again (Stage 75 item 4, from the 2026-10-13 UI/UX audit).

The theme toggle redraws the NHL's and NBA's boards, and so does a day chip:
two open rows became none after either (measured 2026-10-13 on the NHL's
sample week, 390 and 1440 px, both themes). renderBoard now keeps the open
rows by game and opens them again.

This opens the NHL's sample page at 390 and 1440 px, dark and light, finds
a day with two games, opens both, then (1) toggles the theme and (2) presses
another day and comes back, and fails unless both rows are open each time.

`--self-test` deletes the restore from a copy of the page and fails unless
the closed rows are reported.

Usage:
  python tests/browser/check_open_rows.py <nhl page.html>
  python tests/browser/check_open_rows.py --self-test --tmp <dir>
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
OPEN_JS = "() => [...document.querySelectorAll('.nhl-row, .nba-row')].filter(r => r.getAttribute('aria-expanded') === 'true' && !document.getElementById(r.getAttribute('aria-controls')).hidden).length"


async def check_page(path):
    report = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for theme in THEMES:
            for width in WIDTHS:
                where = f'[{theme} {width}]'
                ctx = await browser.new_context(viewport={'width': width, 'height': 900}, color_scheme=theme,
                                                reduced_motion='reduce')
                page = await ctx.new_page()
                await page.route(lambda u: u.startswith(('http://', 'https://')), lambda r: r.abort())
                await page.goto(Path(path).resolve().as_uri())
                await page.wait_for_timeout(200)
                chips = page.locator('.nhl-day-chip, .nba-day-chip')
                day = None
                for i in range(await chips.count()):
                    await chips.nth(i).click()
                    await page.wait_for_timeout(50)
                    if await page.locator('.nhl-row, .nba-row').count() >= 2:
                        day = i
                        break
                if day is None:
                    report.append(f'{where} no day with two games to open')
                    await ctx.close()
                    continue
                await page.evaluate("() => { const r = [...document.querySelectorAll('.nhl-row, .nba-row')]; r[0].click(); r[1].click(); }")
                await page.wait_for_timeout(50)
                if await page.evaluate(OPEN_JS) != 2:
                    report.append(f'{where} two rows did not open')
                await page.locator('.topbar-theme, .theme-toggle').filter(visible=True).first.click()
                await page.wait_for_timeout(100)
                n = await page.evaluate(OPEN_JS)
                if n != 2:
                    report.append(f'{where} after the theme toggle {n} of 2 rows are open')
                await chips.nth((day + 1) % await chips.count()).click()
                await page.wait_for_timeout(50)
                await chips.nth(day).click()
                await page.wait_for_timeout(50)
                n = await page.evaluate(OPEN_JS)
                if n != 2:
                    report.append(f'{where} after another day and back {n} of 2 rows are open')
                await ctx.close()
        await browser.close()
    return report


#: The restore the item added, as it reads in the NHL's built page.
RESTORE = """  grid.querySelectorAll('.nhl-row').forEach(btn => {
    if(!OPEN_ROWS.has(btn.getAttribute('aria-controls'))) return;
    btn.setAttribute('aria-expanded', 'true');
    document.getElementById(btn.getAttribute('aria-controls')).hidden = false;
  });
"""


def self_test(tmp):
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    page = tmp / 'open-rows-nhl.html'
    subprocess.run([sys.executable, 'tests/browser/build_nhl.py', '--out', str(page)], cwd=ROOT, check=True,
                   capture_output=True)
    html = page.read_text(encoding='utf-8')
    if html.count(RESTORE) != 1:
        return [f'self-test: the page holds {html.count(RESTORE)} copies of the restore, expected 1']
    bad = tmp / 'open-rows-nhl-old.html'
    bad.write_text(html.replace(RESTORE, ''), encoding='utf-8')
    problems = [f'self-test: the real page should be clean: {r}' for r in asyncio.run(check_page(page))]
    if not any('rows are open' in r for r in asyncio.run(check_page(bad))):
        problems.append('self-test: the page without the restore was not reported')
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('page', nargs='?')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--tmp')
    a = ap.parse_args()
    report = self_test(a.tmp) if a.self_test else asyncio.run(check_page(a.page))
    for line in report:
        print(line)
    print('OK' if not report else f'{len(report)} problem(s)')
    return 1 if report else 0


if __name__ == '__main__':
    sys.exit(main())
