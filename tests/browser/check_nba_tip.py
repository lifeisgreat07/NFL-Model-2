"""A placeholder tip time is not printed as a time (Stage 77 item 33, the 2026-10-13 UI/UX audit's B5).

Opening night's BOS at DET read "3:00 PM" from ESPN's 19:00Z placeholder.
A weekday tip before 5 PM Eastern now reads "time TBD" on the row and in
the card; a weekend afternoon game is real and keeps its time.

This opens the NBA page at 390 and 1280 px, dark and light, with the clock
on 2026-10-13, presses every day of every week, and fails unless each
row's time agrees with that rule worked out here from the page's own game
data, and an opened card's date line says the same.

`--self-test` puts the old time back into a copy of the page and fails
unless it is reported.

Usage:
  python tests/browser/check_nba_tip.py <nba page.html>
  python tests/browser/check_nba_tip.py --self-test --tmp <dir>
"""
import argparse
import asyncio
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
ET = ZoneInfo('America/New_York')
CLOCK = '2026-10-13T17:00:00Z'
#: The first weeks of the season, which hold the opening-night placeholder;
#: every week is too many presses for a check that runs on every PR.
WEEKS = 3


def placeholder(start):
    t = datetime.fromisoformat(start.replace('Z', '+00:00')).astimezone(ET)
    return t.weekday() < 5 and t.hour < 17


async def check_page(path):
    report, seen = [], 0
    uri = Path(path).resolve().as_uri()
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for theme in ('dark', 'light'):
            for width in (390, 1280):
                where = f'[{theme} {width}]'
                ctx = await browser.new_context(viewport={'width': width, 'height': 900}, color_scheme=theme)
                page = await ctx.new_page()
                await page.clock.set_fixed_time(CLOCK)
                await page.route(lambda u: u.startswith(('http://', 'https://')), lambda r: r.abort())
                await page.goto(uri)
                await page.wait_for_timeout(200)
                starts = await page.evaluate('() => Object.fromEntries(BD.games.map(g => [g.id, g.start || null]))')
                for _ in range(WEEKS):
                    for i in range(await page.locator('.nba-day-chip').count()):
                        await page.locator('.nba-day-chip').nth(i).click()
                        rows = await page.evaluate("""() => [...document.querySelectorAll('.nba-row')].map(r => ({
                            id: r.getAttribute('aria-controls').replace('nba-detail-', ''),
                            time: r.querySelector('.nba-row-time').textContent.trim()}))""")
                        for r in rows:
                            start = starts.get(r['id'])
                            if not start or r['time'] in ('Final', 'Live'):
                                continue
                            seen += 1
                            tbd = placeholder(start)
                            if tbd != (r['time'] == 'time TBD'):
                                report.append(f'{where} game {r["id"]} at {start} reads "{r["time"]}"')
                            if tbd:
                                await page.locator(f'.nba-row[aria-controls="nba-detail-{r["id"]}"]').click()
                                line = await page.evaluate(f"() => document.getElementById('nba-detail-{r['id']}').innerText")
                                if '· time TBD' not in line:
                                    report.append(f'{where} game {r["id"]}: its card gives a time for a placeholder start')
                    nxt = page.locator('#week-next')
                    if not await nxt.is_enabled():
                        break
                    await nxt.click()
                await ctx.close()
        await browser.close()
    if not seen:
        report.append('no NBA row with a start time was checked')
    return report


#: The rule the item added to the row, as it reads in the built page.
ROW = "  return tipSet(g) ? FMT_HOUR.format(new Date(g.start)) : 'time TBD';\n"


def self_test(tmp):
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    page = tmp / 'tip-nba.html'
    subprocess.run([sys.executable, '-m', 'src.sports.nba.site', '--out', str(page)], cwd=ROOT, check=True,
                   capture_output=True)
    html = page.read_text(encoding='utf-8')
    if html.count(ROW) != 1:
        return [f'self-test: the page holds {html.count(ROW)} row rules, expected 1']
    bad = tmp / 'tip-nba-old.html'
    bad.write_text(html.replace(ROW, "  return FMT_HOUR.format(new Date(g.start));\n"), encoding='utf-8')
    problems = [f'self-test: the real page should be clean: {r}' for r in asyncio.run(check_page(page))]
    if not any('reads "3:00 PM"' in r for r in asyncio.run(check_page(bad))):
        problems.append('self-test: the page printing the placeholder time was not reported')
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
