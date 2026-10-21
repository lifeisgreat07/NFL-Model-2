"""Until the first pick is saved, the NBA's note counts down to it (Stage 80 item 60, the 2026-10-13 UI/UX audit's F17).

This opens the NBA page at 390 and 1280 px, dark and light, with the clock
fixed a week before opening night, the day before, the morning of and the
day after, and fails unless the note's first line reads "First picks lock
<opening night> — 7 days", "— tomorrow", "— today", and is gone the day
after. Opening night is read from the page's own schedule.

`--self-test` takes the countdown out of a copy of the page and fails
unless it is reported.

Usage:
  python tests/browser/check_nba_countdown.py <nba page.html>
  python tests/browser/check_nba_countdown.py --self-test --tmp <dir>
"""
import argparse
import asyncio
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pre_opening import pre_opening

ROOT = Path(__file__).resolve().parents[2]
#: Days before opening night (Eastern), and what the countdown ends with.
MOMENTS = ((7, '— 7 days'), (1, '— tomorrow'), (0, '— today'), (-1, None))
LINE = "() => { const c = document.querySelector('.nba-countdown'); return c ? c.textContent.trim() : null; }"


async def check_page(path):
    report = []
    uri = pre_opening(path).resolve().as_uri()
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        probe = await browser.new_page()
        await probe.goto(uri)
        opening = date.fromisoformat(await probe.evaluate('() => OPENING_DAY'))
        await probe.close()
        label = f'{opening:%a}, {opening:%b} {opening.day}'
        for before, ending in MOMENTS:
            # 17:00 UTC is 1 PM Eastern on the same calendar day, before any lock.
            clock = datetime(*(opening - timedelta(days=before)).timetuple()[:3], 17).isoformat() + 'Z'
            if before == 0:
                clock = clock.replace('T17:', 'T13:')   # 9 AM Eastern on the day itself
            for theme in ('dark', 'light'):
                for width in (390, 1280):
                    where = f'[{clock[:10]} {theme} {width}]'
                    ctx = await browser.new_context(viewport={'width': width, 'height': 900}, color_scheme=theme)
                    page = await ctx.new_page()
                    await page.clock.set_fixed_time(clock)
                    await page.route(lambda u: u.startswith(('http://', 'https://')), lambda r: r.abort())
                    await page.goto(uri)
                    await page.wait_for_timeout(200)
                    line = await page.evaluate(LINE)
                    if ending is None:
                        if line:
                            report.append(f'{where} the day after opening night the note still counts down: "{line}"')
                    elif not line or not line.startswith(f'First picks lock {label}') or not line.endswith(ending):
                        report.append(f'{where} the note reads {line!r}, not "First picks lock {label} ... {ending}"')
                    await ctx.close()
        await browser.close()
    return report


#: The note's first line, as it reads in the built page.
LEAD = "${countdown ? `<p class=\"nba-countdown\">${escapeHtml(countdown)}</p>` : ''}"


def self_test(tmp):
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    page = tmp / 'countdown-nba.html'
    subprocess.run([sys.executable, '-m', 'src.sports.nba.site', '--out', str(page)], cwd=ROOT, check=True,
                   capture_output=True)
    html = page.read_text(encoding='utf-8')
    if html.count(LEAD) != 1:
        return [f'self-test: the page holds {html.count(LEAD)} countdown lines, expected 1']
    bad = tmp / 'countdown-nba-old.html'
    bad.write_text(html.replace(LEAD, ''), encoding='utf-8')
    problems = [f'self-test: the real page should be clean: {r}' for r in asyncio.run(check_page(page))]
    if not any("the note reads None" in r for r in asyncio.run(check_page(bad))):
        problems.append('self-test: the page without the countdown was not reported')
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
