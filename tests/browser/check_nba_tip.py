"""A tip time is printed unless ESPN says it is not set (Stage 77 item 33, as corrected 2026-10-15).

Item 33 (the 2026-10-13 audit's B5) took opening night's BOS at DET at
"3:00 PM" for a placeholder and printed a weekday tip before 5 PM Eastern as
"time TBD". The game is a real 3 PM matinee on NBC, and ESPN marks its time
as set. The board now reads ESPN's own flag (`tv`, the competition's
timeValid): only a game whose flag is false reads "time TBD", on the row
and in its card.

This opens the NBA page at 390 and 1280 px, dark and light, with the clock
on 2026-10-13, presses every day of the first weeks, and fails unless each
row's time agrees with the page's own game data, and an opened card's date
line says the same.

`--self-test` checks two copies of the page: one with the hour rule put
back, which must be reported for hiding a set time, and one with a game's
flag set false, which must read "time TBD".

Usage:
  python tests/browser/check_nba_tip.py <nba page.html>
  python tests/browser/check_nba_tip.py --self-test --tmp <dir>
"""
import argparse
import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
CLOCK = '2026-10-13T17:00:00Z'
#: The first weeks of the season, which hold opening night's 3 PM game;
#: every week is too many presses for a check that runs on every PR.
WEEKS = 3


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
                games = await page.evaluate('() => Object.fromEntries(BD.games.map(g => [g.id, {start: g.start || null, tbd: g.tv === false}]))')
                for _ in range(WEEKS):
                    for i in range(await page.locator('.nba-day-chip').count()):
                        await page.locator('.nba-day-chip').nth(i).click()
                        rows = await page.evaluate("""() => [...document.querySelectorAll('.nba-row')].map(r => ({
                            id: r.getAttribute('aria-controls').replace('nba-detail-', ''),
                            time: r.querySelector('.nba-row-time').textContent.trim()}))""")
                        for r in rows:
                            g = games.get(r['id']) or {}
                            start = g.get('start')
                            if not start or r['time'] in ('Final', 'Live'):
                                continue
                            seen += 1
                            tbd = g['tbd']
                            if tbd != (r['time'] == 'time TBD'):
                                report.append(f'{where} game {r["id"]} at {start} reads "{r["time"]}"')
                            if tbd:
                                await page.locator(f'.nba-row[aria-controls="nba-detail-{r["id"]}"]').click()
                                line = await page.evaluate(f"() => document.getElementById('nba-detail-{r['id']}').innerText")
                                if '· time TBD' not in line:
                                    report.append(f'{where} game {r["id"]}: its card gives a time ESPN says is not set')
                    nxt = page.locator('#week-next')
                    if not await nxt.is_enabled():
                        break
                    await nxt.click()
                await ctx.close()
        await browser.close()
    if not seen:
        report.append('no NBA row with a start time was checked')
    return report


#: The rule, as it reads in the built page, and the hour rule it replaced.
RULE = "  return Boolean(g.start) && g.tv !== false;\n"
HOUR_RULE = ("  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-US', {weekday: 'short', hour: 'numeric', "
             "hourCycle: 'h23', timeZone: ET}).formatToParts(new Date(g.start)).map(x => [x.type, x.value]));\n"
             "  return Boolean(g.start) && (parts.weekday === 'Sat' || parts.weekday === 'Sun' || Number(parts.hour) >= 17);\n")
DATA = re.compile(r'(<script id="nba-data" type="application/json">)(.*?)(</script>)', re.S)


def flag_first_game(html):
    """The page with the first still-to-be-played game that has a start marked by ESPN as not set."""
    m = DATA.search(html)
    data = json.loads(m.group(2))
    # Only a game still to be played: the check skips rows reading 'Final' or 'Live',
    # so flagging one of those could never be seen (it broke on NBA opening night).
    first = next(g for g in data['board']['games'] if g.get('start') and g.get('status') == 'scheduled')
    first['tv'] = False
    body = json.dumps(data).replace('<', '\\u003c')
    return html[:m.start(2)] + body + html[m.end(2):], first['id']


def self_test(tmp):
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    page = tmp / 'tip-nba.html'
    subprocess.run([sys.executable, '-m', 'src.sports.nba.site', '--out', str(page)], cwd=ROOT, check=True,
                   capture_output=True)
    html = page.read_text(encoding='utf-8')
    if html.count(RULE) != 1:
        return [f'self-test: the page holds {html.count(RULE)} tip rules, expected 1']
    problems = [f'self-test: the real page should be clean: {r}' for r in asyncio.run(check_page(page))]
    hour = tmp / 'tip-nba-hour-rule.html'
    hour.write_text(html.replace(RULE, HOUR_RULE), encoding='utf-8')
    if not any('reads "time TBD"' in r for r in asyncio.run(check_page(hour))):
        problems.append('self-test: the page with the hour rule back, hiding a set 3 PM time, was not reported')
    flagged_html, gid = flag_first_game(html)
    flagged = tmp / 'tip-nba-flagged.html'
    flagged.write_text(flagged_html, encoding='utf-8')
    problems += [f'self-test: the flagged page should be clean: {r}' for r in asyncio.run(check_page(flagged))]
    printed = tmp / 'tip-nba-flag-ignored.html'
    printed.write_text(flagged_html.replace(RULE, "  return Boolean(g.start);\n"), encoding='utf-8')
    if not any(f'game {gid} ' in r for r in asyncio.run(check_page(printed))):
        problems.append(f'self-test: game {gid}, flagged not set, printed a time and was not reported')
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
