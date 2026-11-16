"""No day-board row cuts its game on a phone (audit 9, finding D12).

At 375 px the NHL's game cell was 87 to 95 px wide for a final game needing 96 to 99, so four of a day's fourteen
rows ended "SEA 1 @ CA…", losing the home score; the NBA's rows wrap at the @ instead. This opens each page at
360, 375 and 390 px, opens every day it holds games for by its address (#board/<day>), and fails naming every row
whose game cell is wider inside than out (scrollWidth over clientWidth), which is what a cut looks like.

`--self-test` writes the NHL's old cell back into a copy of its sample page and fails unless the cut is reported.

Usage:
  python tests/browser/check_row_cut.py <page.html> ...
  python tests/browser/check_row_cut.py --self-test --tmp <dir>
"""
import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests/browser, when imported from elsewhere
from page_edit import rehash

ROOT = Path(__file__).resolve().parents[2]
WIDTHS = (360, 375, 390)
CELLS = """() => [...document.querySelectorAll('.nhl-row-game, .nba-row-game')]
  .filter(e => e.getBoundingClientRect().width > 0)
  .map(e => ({text: e.innerText.trim(), scroll: e.scrollWidth, client: e.clientWidth}))"""
#: Every day the page holds games for: the week the page opens on can be all unplayed games, which carry no score
#: and so are never cut, while the finished days behind it are where the cut was.
DAYS = """() => typeof DATA !== 'undefined' && Array.isArray(DATA.games)
  ? [...new Set(DATA.games.map(g => g.day))].sort()
  : [...new Set([...document.querySelectorAll('[data-day]')].map(b => b.dataset.day))]"""


async def check_pages(pages):
    report = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for path in pages:
            for width in WIDTHS:
                ctx = await browser.new_context(viewport={'width': width, 'height': 800})
                page = await ctx.new_page()
                await page.route(lambda u: u.startswith(('http://', 'https://')), lambda route: route.abort())
                uri = Path(path).resolve().as_uri()
                await page.goto(uri)
                await page.wait_for_timeout(300)
                seen = 0
                for day in await page.evaluate(DAYS):
                    # By the day's address: an element's data-day is not always its chip.
                    await page.goto(f'{uri}#board/{day}')
                    await page.reload()
                    await page.wait_for_timeout(300)
                    for c in await page.evaluate(CELLS):
                        seen += 1
                        if c['scroll'] > c['client'] + 1:
                            report.append(f'[{Path(path).name} {width}px {day}] "{c["text"]}" is cut: '
                                          f'{c["scroll"]} px in {c["client"]}')
                if not seen:
                    report.append(f'[{Path(path).name} {width}px] no game rows found')
                await ctx.close()
        await browser.close()
    return report


FIXED = '.nhl-row-game{white-space:normal; overflow:visible;}'


def self_test(tmp):
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    nhl = tmp / 'cut-nhl.html'
    subprocess.run([sys.executable, 'tests/browser/build_nhl.py', '--out', str(nhl)], cwd=ROOT, check=True,
                   capture_output=True)
    t = nhl.read_text(encoding='utf-8')
    if t.count(FIXED) != 1:
        return [f'self-test: {t.count(FIXED)} copies of the phone rule, expected 1']
    cut = tmp / 'cut-nhl-old.html'
    cut.write_text(rehash(t.replace(FIXED, '')), encoding='utf-8')
    problems = [f'self-test: the real page should be clean: {r}' for r in asyncio.run(check_pages([nhl]))]
    if not any(' is cut: ' in r for r in asyncio.run(check_pages([cut]))):
        problems.append('self-test: the old cell was not reported')
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
