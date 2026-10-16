"""The NHL board's eyebrow names the week it shows, as the NBA's does (Stage 77 item 32's rule).

It said "This Week" over any week the stepper reached. It now says This
Week only for the week holding today (Eastern), Next Week for the one after,
Coming Up for later weeks and Earlier for past ones.

The browser checks' NHL page holds one sample week (Monday 2026-10-05 to
Sunday the 11th, tests/browser/build_nhl.py), so the clock is moved instead
of the stepper: fixed in the week before it, the week of it, the week after
and two weeks before, at 390 and 1280 px, dark and light. The eyebrow must
agree with the week the stepper's own label names, and once more after a
step either way where one is possible.

`--self-test` puts the old fixed eyebrow back into a copy of the page and
fails unless it is reported.

Usage:
  python tests/browser/check_nhl_eyebrow.py <nhl page.html>
  python tests/browser/check_nhl_eyebrow.py --self-test --tmp <dir>
"""
import argparse
import asyncio
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
WIDTHS = (390, 1280)
THEMES = ('dark', 'light')
#: 17:00 UTC is 1 PM Eastern, the same calendar day in both zones. Against the
#: sample week of Oct 5 these read Next Week, This Week, Earlier and Coming Up.
CLOCKS = ('2026-09-30T17:00:00Z', '2026-10-07T17:00:00Z', '2026-10-14T17:00:00Z', '2026-09-23T17:00:00Z')
SHOWN = """() => ({eyebrow: document.querySelector('#page-board .page-eyebrow').textContent.trim(),
  label: document.getElementById('week-step-label').textContent.trim()})"""


def expected(label, today):
    """What the eyebrow should say for 'Week of Oct 5 · ...' seen on `today`."""
    monday = datetime.strptime(label.split(' · ')[0].replace('Week of ', '') + f' {today.year}', '%b %d %Y').date()
    this = today - timedelta(days=today.weekday())
    if monday == this:
        return 'This Week'
    if monday == this + timedelta(days=7):
        return 'Next Week'
    return 'Coming Up' if monday > this else 'Earlier'


async def check_page(path):
    report = []
    seen = set()
    uri = Path(path).resolve().as_uri()
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for clock in CLOCKS:
            today = date.fromisoformat(clock[:10])
            for theme in THEMES:
                for width in WIDTHS:
                    where = f'[{clock[:10]} {theme} {width}]'
                    ctx = await browser.new_context(viewport={'width': width, 'height': 900}, color_scheme=theme)
                    page = await ctx.new_page()
                    await page.clock.set_fixed_time(clock)
                    await page.route(lambda u: u.startswith(('http://', 'https://')), lambda r: r.abort())
                    await page.goto(uri)
                    await page.wait_for_timeout(200)
                    for step in (None, '#week-next', '#week-prev'):
                        if step:
                            button = page.locator(step)
                            if not await button.is_enabled():
                                continue
                            await button.click()
                            await page.wait_for_timeout(50)
                        shown = await page.evaluate(SHOWN)
                        want = expected(shown['label'], today)
                        seen.add(want)
                        if shown['eyebrow'] != want:
                            report.append(f'{where} "{shown["eyebrow"]}" over "{shown["label"]}", not "{want}"')
                    await ctx.close()
        await browser.close()
    missing = {'This Week', 'Next Week', 'Coming Up', 'Earlier'} - seen
    if missing:
        report.append(f'the clocks never reached {sorted(missing)} -- the sample week moved; move CLOCKS with it')
    return report


#: The line that keeps the eyebrow in step, as it reads in the built page.
WRITE = "  document.querySelector('#page-board .page-eyebrow').textContent = weekEyebrow(currentWeek, mondayOf(todayEt()));\n"


def self_test(tmp):
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    page = tmp / 'eyebrow-nhl.html'
    subprocess.run([sys.executable, 'tests/browser/build_nhl.py', '--out', str(page)], cwd=ROOT, check=True,
                   capture_output=True)
    html = page.read_text(encoding='utf-8')
    if html.count(WRITE) != 1:
        return [f'self-test: the page holds {html.count(WRITE)} eyebrow writes, expected 1']
    bad = tmp / 'eyebrow-nhl-old.html'
    bad.write_text(html.replace(WRITE, ''), encoding='utf-8')
    problems = [f'self-test: the real page should be clean: {r}' for r in asyncio.run(check_page(page))]
    if not any('"This Week" over' in r for r in asyncio.run(check_page(bad))):
        problems.append('self-test: the page with the fixed eyebrow was not reported')
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
