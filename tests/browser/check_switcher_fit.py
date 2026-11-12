"""The sport switcher fits its sidebar with the league marks in it (Stage 102; Mark, 2026-11-11: "the slider needs
to fit with the logos now").

Each sport page's sidebar switcher holds Home and three sports, each sport now led by its league's mark. This opens
every page given at 1080, 1280 and 1440 px, dark and light, with each mark answered by a blank 32 px image (the
runner may not reach ESPN, and a mark that fails hides itself, which would make the pills fit by losing what is
being measured). It fails unless, in the sidebar, every pill lies inside the switcher, no pill's name is cut
(its content no wider than the pill), and every sport's mark is drawn, at least 12 px wide.

`--self-test` puts the pills' wider spacing back in a copy of the NHL page and fails unless the overflow is reported.

Usage:
  python tests/browser/check_switcher_fit.py <page.html> ...
  python tests/browser/check_switcher_fit.py --self-test --tmp <dir>
"""
import argparse
import asyncio
import base64
import subprocess
import sys
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests/browser, when imported from elsewhere
from page_edit import rehash

ROOT = Path(__file__).resolve().parents[2]
# A transparent 32x32 PNG, so a mark's box is laid out as a loaded mark's would be.
BLANK = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAGklEQVR42u3BAQEAAACCIP+vbkhAAQAAAO8GECAAAcm1w7EAAAAASUVORK5CYII=')
MEASURE = """() => { const nav = document.querySelector('.sidebar .sport-switch');
  if(!nav || getComputedStyle(nav).display === 'none') return null;
  const n = nav.getBoundingClientRect();
  return {navRight: n.right, navLeft: n.left, pills: [...nav.querySelectorAll('a')].map(a => {
    const r = a.getBoundingClientRect(), m = a.querySelector('.lgm');
    const img = m && [...m.querySelectorAll('img')].find(i => getComputedStyle(i).display !== 'none');
    return {name: a.textContent.trim(), left: r.left, right: r.right, scroll: a.scrollWidth, client: a.clientWidth,
            mark: img ? img.getBoundingClientRect().width : (m ? 0 : null)}; })}; }"""


async def check_pages(pages):
    report = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for path in pages:
            uri = Path(path).resolve().as_uri()
            for theme in ('dark', 'light'):
                for width in (1080, 1280, 1440):
                    where = f'[{Path(path).name} {theme} {width}]'
                    ctx = await browser.new_context(viewport={'width': width, 'height': 800}, color_scheme=theme)
                    page = await ctx.new_page()

                    async def answer(route):
                        if '/teamlogos/leagues/' in route.request.url:
                            await route.fulfill(body=BLANK, content_type='image/png')
                        else:
                            await route.abort()
                    await page.route(lambda u: u.startswith(('http://', 'https://')), answer)
                    await page.goto(uri)
                    await page.wait_for_timeout(300)
                    m = await page.evaluate(MEASURE)
                    await ctx.close()
                    if m is None:
                        report.append(f'{where} no sidebar switcher is shown')
                        continue
                    for pill in m['pills']:
                        if pill['left'] < m['navLeft'] - 0.5 or pill['right'] > m['navRight'] + 0.5:
                            report.append(f'{where} {pill["name"]} lies outside the switcher '
                                          f'({pill["right"]:.0f} > {m["navRight"]:.0f})')
                        if pill['scroll'] > pill['client'] + 1:
                            report.append(f'{where} {pill["name"]} is cut ({pill["scroll"]} px in {pill["client"]})')
                        if pill['name'] != 'Home' and (pill['mark'] is None or pill['mark'] < 12):
                            report.append(f'{where} {pill["name"]} has no mark drawn')
        await browser.close()
    return report


TIGHT = '.sidebar .sport-switch a{gap:3px; padding:0 var(--s1); font-size:var(--fs-12);}'
LOOSE = '.sidebar .sport-switch a{gap:var(--s2); padding:0 var(--s3); font-size:var(--fs-13);}'


def self_test(tmp):
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    nhl = tmp / 'fit-nhl.html'
    subprocess.run([sys.executable, 'tests/browser/build_nhl.py', '--out', str(nhl)], cwd=ROOT, check=True,
                   capture_output=True)
    t = nhl.read_text(encoding='utf-8')
    if t.count(TIGHT) != 1:
        return [f'self-test: {t.count(TIGHT)} copies of the sidebar pill rule, expected 1']
    loose = tmp / 'fit-nhl-loose.html'
    loose.write_text(rehash(t.replace(TIGHT, LOOSE)), encoding='utf-8')
    problems = [f'self-test: the real page should be clean: {r}' for r in asyncio.run(check_pages([nhl]))]
    if not any('outside the switcher' in r or 'is cut' in r for r in asyncio.run(check_pages([loose]))):
        problems.append('self-test: the pills at their old spacing were not reported')
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
