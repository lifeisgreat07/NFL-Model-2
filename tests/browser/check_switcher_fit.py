"""The sport menu fits, with the league marks and the records in it (Stage 102; Mark, 2026-11-11: "the slider
needs to fit with the logos now"; since audit 9 D3, Mark's M1 B on 2026-11-16, a menu).

Each sport page's switcher is a menu: a button naming the page, and a list of Home and every sport, each sport
led by its league's mark and ending with its season record. This opens every page given in the sidebar at 1080,
1280 and 1440 px and in the phone strip at 375 px, dark and light, with each mark answered by a blank 32 px
image (the runner may not reach ESPN, and a mark that fails hides itself, which would make a row fit by losing
what is being measured), and every record slot filled with the widest plausible record ("888-888": the build
fills them, and a page built without the site build has none). It opens the menu with a click and fails unless
every row lies inside the menu's panel and the screen, no row's name or record is cut (its content no wider
than the row), every sport's mark is drawn at least 12 px wide, and the middle of each row is that row (not
covered by the page). The button must fit too.

`--self-test` narrows the sidebar panel and pushes the phone panel off the screen in copies of the NHL page and
fails unless both are reported.

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
WIDEST = '888-888'
FILL = """(widest) => { for(const s of document.querySelectorAll('.sm-rec')) if(!s.textContent) s.textContent = widest; }"""
MEASURE = """(sel) => { const nav = [...document.querySelectorAll(sel)].find(n => getComputedStyle(n).display !== 'none');
  if(!nav) return null;
  const d = nav.querySelector('details.sm'), s = d && d.querySelector('summary'), list = d && d.querySelector('.sm-list');
  if(!d || !s || !list) return {menu: false};
  const b = s.getBoundingClientRect(), p = list.getBoundingClientRect();
  return {menu: true, open: d.open, vw: innerWidth, button: {left: b.left, right: b.right, scroll: s.scrollWidth,
          client: s.clientWidth}, panel: {left: p.left, right: p.right},
    rows: [...list.querySelectorAll('a')].map(a => {
      const r = a.getBoundingClientRect(), m = a.querySelector('.lgm');
      const img = m && [...m.querySelectorAll('img')].find(i => getComputedStyle(i).display !== 'none');
      const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return {name: a.textContent.trim(), left: r.left, right: r.right, scroll: a.scrollWidth, client: a.clientWidth,
              hit: !!(hit && a.contains(hit)), mark: img ? img.getBoundingClientRect().width : (m ? 0 : null)}; })}; }"""
VIEWS = [('.sidebar .sport-switch', 1080), ('.sidebar .sport-switch', 1280), ('.sidebar .sport-switch', 1440),
         ('.sport-strip', 375)]


async def check_pages(pages):
    report = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for path in pages:
            uri = Path(path).resolve().as_uri()
            for theme in ('dark', 'light'):
                for sel, width in VIEWS:
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
                    await page.evaluate(FILL, WIDEST)
                    button = page.locator(f'{sel} details.sm > summary')
                    if await button.count() != 1:
                        report.append(f'{where} no menu button in {sel}')
                        await ctx.close()
                        continue
                    await button.click()
                    await page.wait_for_timeout(150)
                    m = await page.evaluate(MEASURE, sel)
                    await ctx.close()
                    if m is None:
                        report.append(f'{where} no switcher is shown ({sel})')
                        continue
                    if not m['menu'] or not m['open']:
                        report.append(f'{where} the switcher is not a menu that opens')
                        continue
                    if m['button']['scroll'] > m['button']['client'] + 1 or m['button']['right'] > m['vw'] + 0.5:
                        report.append(f'{where} the menu button is cut')
                    if m['panel']['left'] < -0.5 or m['panel']['right'] > m['vw'] + 0.5:
                        report.append(f'{where} the menu runs outside the screen ({m["panel"]["right"]:.0f} > {m["vw"]})')
                    for row in m['rows']:
                        if row['left'] < m['panel']['left'] - 0.5 or row['right'] > m['panel']['right'] + 0.5:
                            report.append(f'{where} {row["name"]} lies outside the menu')
                        if row['scroll'] > row['client'] + 1:
                            report.append(f'{where} {row["name"]} is cut ({row["scroll"]} px in {row["client"]})')
                        if not row['hit']:
                            report.append(f'{where} {row["name"]} is covered')
                        if not row['name'].startswith('Home') and (row['mark'] is None or row['mark'] < 12):
                            report.append(f'{where} {row["name"]} has no mark drawn')
        await browser.close()
    return report


SIDEBAR = '.sidebar .sm-list{min-width:0;}'
NARROW = '.sidebar .sm-list{min-width:0; width:96px;}'
PHONE = '.sport-strip .sm-list, .home-switch .sm-list{position:absolute; top:100%; left:0;'
OFF = '.sport-strip .sm-list, .home-switch .sm-list{position:absolute; top:100%; left:240px;'


def self_test(tmp):
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    nhl = tmp / 'fit-nhl.html'
    subprocess.run([sys.executable, 'tests/browser/build_nhl.py', '--out', str(nhl)], cwd=ROOT, check=True,
                   capture_output=True)
    t = nhl.read_text(encoding='utf-8')
    problems = [f'self-test: {t.count(a)} copies of {a!r}, expected 1' for a in (SIDEBAR, PHONE) if t.count(a) != 1]
    if problems:
        return problems
    narrow, off = tmp / 'fit-nhl-narrow.html', tmp / 'fit-nhl-off.html'
    narrow.write_text(rehash(t.replace(SIDEBAR, NARROW)), encoding='utf-8')
    off.write_text(rehash(t.replace(PHONE, OFF)), encoding='utf-8')
    problems = [f'self-test: the real page should be clean: {r}' for r in asyncio.run(check_pages([nhl]))]
    if not any('is cut' in r or 'outside the menu' in r for r in asyncio.run(check_pages([narrow]))):
        problems.append('self-test: a sidebar menu too narrow for its rows was not reported')
    if not any('375]' in r and 'outside the screen' in r for r in asyncio.run(check_pages([off]))):
        problems.append('self-test: a phone menu off the screen was not reported')
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
