"""No chart text under 11 px on any sport's page (Stage 79 item 45, the 2026-10-13 UI/UX audit's N9 and V3).

This opens the NFL page on Season Accuracy and Model Lab, the NHL's sample
page on Accuracy and the NBA page on Checking the AI's work, at 390 and
1440 px, dark and light, and fails unless every SVG chart that holds text is
an svg.chart (the one chart style in styles.css), no chart text renders under
11 px once its viewBox is scaled to the page, the NFL's trend draws its 50%
reference, and no script error is thrown. Before the item the NFL's trend
printed 9 px text at 1440 px, its calibration chart 9 px at both widths and
its reliability diagram one label at 10.5 px.

`--self-test` puts a copy of the NFL page's chart text back to 9 units and
fails unless it is reported.

Usage:
  python tests/browser/check_chart_text.py <nfl page.html> <nhl page.html> <nba page.html>
  python tests/browser/check_chart_text.py --self-test --tmp <dir>
"""
import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
#: Each sport's pages with charts, by the id the router opens.
PAGES = {'NFL': ('accuracy', 'modellab'), 'NHL': ('accuracy',), 'NBA': ('reliability',)}
MEASURE = """() => {
  const page = document.querySelector('.page.active');
  const charts = [...page.querySelectorAll('svg')].filter(s => s.querySelector('text') && s.getClientRects().length);
  const sizes = [];
  for (const svg of charts) {
    const m = svg.getScreenCTM(), scale = m ? Math.hypot(m.a, m.b) : 1;
    for (const t of svg.querySelectorAll('text')) {
      if (!t.getClientRects().length) continue;
      sizes.push({px: parseFloat(getComputedStyle(t).fontSize) * scale, text: t.textContent.trim().slice(0, 30)});
    }
  }
  sizes.sort((a, b) => a.px - b.px);
  return {charts: charts.length, unstyled: charts.filter(s => !s.classList.contains('chart')).length,
          smallest: sizes[0] || null,
          trendRef: !!page.querySelector('svg.chart[aria-label^="Line chart of running accuracy by week"] .chart-ref')}; }"""


async def check_pages(nfl, nhl, nba):
    report = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for sport, path in (('NFL', nfl), ('NHL', nhl), ('NBA', nba)):
            for page_id in PAGES[sport]:
                for theme in ('dark', 'light'):
                    for width in (390, 1440):
                        where = f'[{sport} {page_id} {theme} {width}]'
                        ctx = await browser.new_context(viewport={'width': width, 'height': 900}, color_scheme=theme)
                        page = await ctx.new_page()
                        errors = []
                        page.on('pageerror', lambda e: errors.append(str(e)))
                        await page.clock.set_fixed_time('2026-10-13T17:00:00Z')
                        await page.route(lambda u: u.startswith(('http://', 'https://')), lambda r: r.abort())
                        await page.goto(Path(path).resolve().as_uri() + '#' + page_id)
                        await page.wait_for_timeout(400)
                        m = await page.evaluate(MEASURE)
                        await ctx.close()
                        if errors:
                            report.append(f'{where} script error: {errors[0]}')
                        if not m['charts']:
                            report.append(f'{where} no chart with text found')
                            continue
                        if m['unstyled']:
                            report.append(f'{where} {m["unstyled"]} chart(s) outside the chart style (no class "chart")')
                        if m['smallest'] and m['smallest']['px'] < 10.95:
                            report.append(f'{where} chart text at {m["smallest"]["px"]:.1f} px ("{m["smallest"]["text"]}")')
                        if sport == 'NFL' and page_id == 'accuracy' and not m['trendRef']:
                            report.append(f'{where} the trend draws no 50% reference')
        await browser.close()
    return report


#: The chart style's text rule, as it reads in every built page.
RULE = '.chart text{font-size:var(--fs-11); fill:var(--text-2);}'


def self_test(tmp):
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, '-m', 'src.site.build', '--out', str(tmp / 'chart-site')], cwd=ROOT,
                   check=True, capture_output=True)
    subprocess.run([sys.executable, 'tests/browser/build_nhl.py', '--out', str(tmp / 'chart-nhl.html')],
                   cwd=ROOT, check=True, capture_output=True)
    nfl, nhl, nba = tmp / 'chart-site' / 'nfl' / 'index.html', tmp / 'chart-nhl.html', tmp / 'chart-site' / 'nba' / 'index.html'
    html = nfl.read_text(encoding='utf-8')
    if html.count(RULE) != 1:
        return [f'self-test: the NFL page holds {html.count(RULE)} copies of the chart text rule, expected 1']
    bad = tmp / 'chart-nfl-9.html'
    bad.write_text(html.replace(RULE, RULE.replace('var(--fs-11)', '9px')), encoding='utf-8')
    problems = [f'self-test: the real pages should be clean: {r}' for r in asyncio.run(check_pages(nfl, nhl, nba))]
    if not any(r.startswith('[NFL') and 'chart text at 9' in r for r in asyncio.run(check_pages(bad, nhl, nba))):
        problems.append('self-test: the NFL page with 9 px chart text was not reported')
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
