"""The NHL and the NBA draw the race, the trend and the calibration diagram (Stage 79 item 46, the 2026-10-13 UI/UX audit's L5 and B4).

This opens the NHL's sample page on Accuracy and the NBA page on Checking
the AI's work, at 390 and 1440 px, dark and light, and fails unless each
shows the scoreboard with its three forecasts and both charts, no script
error is thrown, no chart text is under 11 px, and every chart stays inside
its own box. On the NHL (graded picks) the diagram has a dot; on the NBA
(nothing graded before opening night, the clock fixed there) each chart
says so inside its frame.

`--self-test` takes the component out of a copy of the NHL page, as before
the item, and fails unless it is reported.

Usage:
  python tests/browser/check_accuracy.py <nhl page.html> <nba page.html>
  python tests/browser/check_accuracy.py --self-test --tmp <dir>
"""
import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
MEASURE = """() => { const page = document.querySelector('.page.active');
  const charts = [...page.querySelectorAll('.acc-chart')];
  const texts = charts.flatMap(c => [...c.querySelectorAll('svg text')]);
  return {rows: page.querySelectorAll('.scoreboard .score-row').length, charts: charts.length,
          dots: page.querySelectorAll('.acc-chart svg circle').length,
          empties: [...page.querySelectorAll('.acc-chart .acc-empty')].map(t => t.textContent),
          smallest: texts.length ? Math.min(...texts.map(t => parseFloat(getComputedStyle(t).fontSize))) : null,
          overflow: charts.filter(c => c.querySelector('svg').getBoundingClientRect().right > c.getBoundingClientRect().right + 1).length}; }"""


async def check_pages(nhl, nba):
    report = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for sport, path, page_id in (('NHL', nhl, 'accuracy'), ('NBA', nba, 'reliability')):
            for theme in ('dark', 'light'):
                for width in (390, 1440):
                    where = f'[{sport} {theme} {width}]'
                    ctx = await browser.new_context(viewport={'width': width, 'height': 900}, color_scheme=theme)
                    page = await ctx.new_page()
                    errors = []
                    page.on('pageerror', lambda e: errors.append(str(e)))
                    await page.clock.set_fixed_time('2026-10-13T17:00:00Z')
                    await page.route(lambda u: u.startswith(('http://', 'https://')), lambda r: r.abort())
                    await page.goto(Path(path).resolve().as_uri() + '#' + page_id)
                    await page.wait_for_timeout(300)
                    m = await page.evaluate(MEASURE)
                    await ctx.close()
                    if errors:
                        report.append(f'{where} script error: {errors[0]}')
                    if m['rows'] != 3 or m['charts'] != 2:
                        report.append(f'{where} {m["rows"]} scoreboard rows and {m["charts"]} charts, not 3 and 2')
                        continue
                    if m['smallest'] is not None and m['smallest'] < 11:
                        report.append(f'{where} chart text at {m["smallest"]} px')
                    if m['overflow']:
                        report.append(f'{where} {m["overflow"]} chart(s) run past their box')
                    if sport == 'NHL' and not m['dots']:
                        report.append(f'{where} the diagram has no dot for the graded picks')
                    if sport == 'NBA' and len(m['empties']) != 2:
                        report.append(f'{where} {len(m["empties"])} charts say inside their frame that nothing is graded, not 2')
        await browser.close()
    return report


#: The component's call on the NHL's Accuracy page, as it reads in the built page.
CALL = '    ${accuracyHtml(accGames(graded))}\n'


def self_test(tmp):
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    nhl, nba = tmp / 'acc-nhl.html', tmp / 'acc-nba.html'
    subprocess.run([sys.executable, 'tests/browser/build_nhl.py', '--out', str(nhl)], cwd=ROOT, check=True, capture_output=True)
    subprocess.run([sys.executable, '-m', 'src.sports.nba.site', '--out', str(nba)], cwd=ROOT, check=True, capture_output=True)
    html = nhl.read_text(encoding='utf-8')
    if html.count(CALL) != 1:
        return [f'self-test: the NHL page holds {html.count(CALL)} calls, expected 1']
    bad = tmp / 'acc-nhl-old.html'
    bad.write_text(html.replace(CALL, ''), encoding='utf-8')
    problems = [f'self-test: the real pages should be clean: {r}' for r in asyncio.run(check_pages(nhl, nba))]
    if not any(r.startswith('[NHL') and 'scoreboard rows' in r for r in asyncio.run(check_pages(bad, nba))):
        problems.append('self-test: the NHL page without the component was not reported')
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
