"""Nothing marked `hidden` is drawn (audit 9, finding D5).

An element carrying the `hidden` attribute is hidden by the browser's own rule, `display:none`, which any author
rule that sets a display value outranks. The NFL board's "Worth a look" box did exactly that: `hidden`, a computed
display of grid, 49 px tall and empty, above the picks.

This opens every page given at 1440x900 and 375x812, with the network refused, and fails naming every element that
carries `hidden` and whose computed display is not none.

`--self-test` plants a hidden "Worth a look" box in two copies of the NHL page, which shares the stylesheet: one
as built, which must be clean, and one with the box's `[hidden]` rule taken out, which must be reported.

Usage:
  python tests/browser/check_hidden.py <page.html> ...
  python tests/browser/check_hidden.py --self-test --tmp <dir>
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
SIZES = ((1440, 900), (375, 812))
MEASURE = """() => [...document.querySelectorAll('[hidden]')]
  .filter(e => getComputedStyle(e).display !== 'none')
  .map(e => ({tag: e.tagName.toLowerCase(), id: e.id, cls: e.getAttribute('class') || '',
              display: getComputedStyle(e).display, height: Math.round(e.getBoundingClientRect().height)}))"""


async def check_pages(pages):
    report = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for path in pages:
            uri = Path(path).resolve().as_uri()
            for width, height in SIZES:
                ctx = await browser.new_context(viewport={'width': width, 'height': height})
                page = await ctx.new_page()
                await page.route(lambda u: u.startswith(('http://', 'https://')), lambda route: route.abort())
                await page.goto(uri)
                await page.wait_for_timeout(500)
                for e in await page.evaluate(MEASURE):
                    name = '#' + e['id'] if e['id'] else '.' + '.'.join(e['cls'].split())
                    report.append(f'[{Path(path).name} {width}x{height}] <{e["tag"]}> {name} is hidden but drawn: '
                                  f'display {e["display"]}, {e["height"]} px tall')
                await ctx.close()
        await browser.close()
    return report


RULE = '.board-insights[hidden]{display:none;}'
BOX = '<div class="board-insights" id="planted-insights" hidden><h3 class="board-insights-title">Worth a look</h3></div>'


def self_test(tmp):
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    nhl = tmp / 'hidden-nhl.html'
    subprocess.run([sys.executable, 'tests/browser/build_nhl.py', '--out', str(nhl)], cwd=ROOT, check=True,
                   capture_output=True)
    t = nhl.read_text(encoding='utf-8')
    if t.count(RULE) != 1 or t.count('</body>') != 1:
        return [f'self-test: {t.count(RULE)} copies of the rule and {t.count("</body>")} of </body>, expected 1 each']
    planted = t.replace('</body>', BOX + '</body>')
    good, bad = tmp / 'hidden-nhl-planted.html', tmp / 'hidden-nhl-no-rule.html'
    good.write_text(rehash(planted), encoding='utf-8')
    bad.write_text(rehash(planted.replace(RULE, '')), encoding='utf-8')
    problems = [f'self-test: the page with the rule should be clean: {r}' for r in asyncio.run(check_pages([good]))]
    if not any('#planted-insights is hidden but drawn' in r for r in asyncio.run(check_pages([bad]))):
        problems.append('self-test: the hidden box without its rule was not reported')
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
