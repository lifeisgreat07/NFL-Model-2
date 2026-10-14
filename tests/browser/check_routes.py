"""A day and a club have an address (Stage 76 item 7, from the 2026-10-13 UI/UX audit).

The NHL's and NBA's routes named pages only: a day chip, a week step and the
Teams select never touched the address, and a typed #board/2026-10-13 or
#team/DET opened the bare board (measured 2026-10-14 on the built site,
390 and 1440 px, both themes). A route now carries one argument, as the
NFL's does.

This opens the NHL's sample page at 390 and 1440 px, dark and light, and
fails unless:
  - pressing another day writes #board/<that day>, and two presses add no
    history entries;
  - the page opened at #board/<day> shows that day;
  - the page opened at #team/<club> shows the Teams page on that club, and
    choosing another club writes #team/<it>.

`--self-test` makes two copies of the page, one whose chips no longer write
the address and one whose router ignores a day, and fails unless each is
reported.

Usage:
  python tests/browser/check_routes.py <nhl page.html>
  python tests/browser/check_routes.py --self-test --tmp <dir>
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
PRESSED = "() => (document.querySelector('.nhl-day-chip[aria-pressed=true]') || {dataset: {}}).dataset.day || null"
ACTIVE = "() => (document.querySelector('.page.active') || {id: ''}).id"


async def check_page(path):
    report = []
    uri = Path(path).resolve().as_uri()
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for theme in THEMES:
            for width in WIDTHS:
                where = f'[{theme} {width}]'
                ctx = await browser.new_context(viewport={'width': width, 'height': 900}, color_scheme=theme,
                                                reduced_motion='reduce')
                page = await ctx.new_page()
                await page.route(lambda u: u.startswith(('http://', 'https://')), lambda r: r.abort())
                await page.goto(uri)
                await page.wait_for_timeout(200)
                home = await page.evaluate(PRESSED)
                days = await page.evaluate("() => [...document.querySelectorAll('.nhl-day-chip')].map(c => c.dataset.day)")
                others = [d for d in days if d != home]
                if len(others) < 2:
                    report.append(f'{where} fewer than two other days to press')
                    await ctx.close()
                    continue
                length = await page.evaluate('history.length')
                for day in others[:2]:
                    await page.locator(f'.nhl-day-chip[data-day="{day}"]').click()
                    await page.wait_for_timeout(50)
                    got = await page.evaluate('location.hash')
                    if got != f'#board/{day}':
                        report.append(f'{where} pressing {day} left the address at {got!r}, not #board/{day}')
                if await page.evaluate('history.length') != length:
                    report.append(f'{where} two day chips added history entries')
                await ctx.close()

                ctx = await browser.new_context(viewport={'width': width, 'height': 900}, color_scheme=theme,
                                                reduced_motion='reduce')
                page = await ctx.new_page()
                await page.route(lambda u: u.startswith(('http://', 'https://')), lambda r: r.abort())
                await page.goto(f'{uri}#board/{others[0]}')
                await page.wait_for_timeout(200)
                shown = await page.evaluate(PRESSED)
                if shown != others[0]:
                    report.append(f'{where} #board/{others[0]} opened on {shown}')
                await ctx.close()

                ctx = await browser.new_context(viewport={'width': width, 'height': 900}, color_scheme=theme,
                                                reduced_motion='reduce')
                page = await ctx.new_page()
                await page.route(lambda u: u.startswith(('http://', 'https://')), lambda r: r.abort())
                await page.goto(uri)
                await page.wait_for_timeout(200)
                clubs = await page.evaluate("() => [...document.querySelectorAll('#team-select option')].map(o => o.value)")
                first, second = clubs[-1], clubs[-2]
                await page.goto(f'{uri}#team/{first}')
                await page.wait_for_timeout(200)
                active, value = await page.evaluate(ACTIVE), await page.evaluate("document.getElementById('team-select').value")
                if active != 'page-teams' or value != first:
                    report.append(f'{where} #team/{first} opened {active} on {value}')
                else:
                    await page.select_option('#team-select', second)
                    await page.wait_for_timeout(50)
                    got = await page.evaluate('location.hash')
                    if got != f'#team/{second}':
                        report.append(f'{where} choosing {second} left the address at {got!r}')
                await ctx.close()
        await browser.close()
    return report


#: What the item added, as it reads in the NHL's built page (the chip handler's write is
#: indented four spaces; the week step's two).
CHIP_WRITE = "    replaceRoute('board');\n"
DAY_ROUTE = "  if(head === 'board' && (known.days || []).includes(arg)) return {page: 'board', arg};\n"


def self_test(tmp):
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    page = tmp / 'routes-nhl.html'
    subprocess.run([sys.executable, 'tests/browser/build_nhl.py', '--out', str(page)], cwd=ROOT, check=True,
                   capture_output=True)
    html = page.read_text(encoding='utf-8')
    problems = []
    if html.count(CHIP_WRITE) != 1 or html.count(DAY_ROUTE) != 1:
        return [f'self-test: the page holds {html.count(CHIP_WRITE)} chip writes (expected 1) and '
                f'{html.count(DAY_ROUTE)} day routes (expected 1)']
    no_write, no_day = tmp / 'routes-nhl-no-write.html', tmp / 'routes-nhl-no-day.html'
    no_write.write_text(html.replace(CHIP_WRITE, ''), encoding='utf-8')
    no_day.write_text(html.replace(DAY_ROUTE, ''), encoding='utf-8')
    problems += [f'self-test: the real page should be clean: {r}' for r in asyncio.run(check_page(page))]
    if not any('left the address' in r for r in asyncio.run(check_page(no_write))):
        problems.append('self-test: the page whose chips write no address was not reported')
    if not any('#board/' in r and 'opened on' in r for r in asyncio.run(check_page(no_day))):
        problems.append('self-test: the page that ignores a typed day was not reported')
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
