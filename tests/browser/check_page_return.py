"""Arriving on a page, and coming back to one (Stage 76 item 10, from the 2026-10-13 UI/UX audit's N12).

Measured 2026-10-14 on the built site: a link that opened the NHL's
Standings left focus on <body>, while a tap on the nav focused the page's
heading and drew a 2px ring round it; Back from the NFL's Methodology put
the Week Board at the top though it was left at 800 px, and the NHL's Back
and Forward both landed at 0.

This opens the NFL page and the NHL's sample page at 390x844 and 1440x900,
dark and light, and fails unless:
  - a page opened by its link (#method) has its heading focused, with no
    outline, in a fresh tab;
  - a tap on a nav button focuses the heading with no outline;
  - after scrolling the first page down, tapping to a second page,
    scrolling it, then Back and Forward, each page is where it was left.
The first page is the NFL's Week Board and the NHL's Standings (its board
is a day of games and may not scroll).

`--self-test` makes a copy of the NHL page that pushes its entry after the
page change and leaves the scroll to the browser, as before the item, and
fails unless it is reported.

Usage:
  python tests/browser/check_page_return.py <nfl page.html> <nhl page.html>
  python tests/browser/check_page_return.py --self-test --tmp <dir>
"""
import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
SIZES = ((390, 844), (1440, 900))
THEMES = ('dark', 'light')
FOCUS = """() => { const a = document.activeElement;
  return {tag: a.tagName, text: (a.textContent || '').trim().slice(0, 40), outline: getComputedStyle(a).outlineStyle}; }"""
TAP = """(page) => { const b = [...document.querySelectorAll(`[data-page="${page}"]`)].find(e => e.offsetParent)
  || document.querySelector(`[data-page="${page}"]`); b.click(); }"""
#: (sport, first page, its scroll, second page)
TRIPS = {'nfl': ('board', 800, 'method'), 'nhl': ('standings', 500, 'method')}


async def new_page(browser, theme, w, h):
    ctx = await browser.new_context(viewport={'width': w, 'height': h}, color_scheme=theme, reduced_motion='reduce')
    page = await ctx.new_page()
    await page.route(lambda u: u.startswith(('http://', 'https://')), lambda r: r.abort())
    return ctx, page


async def check_pages(nfl, nhl):
    report = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for theme in THEMES:
            for w, h in SIZES:
                for sport, path in (('nfl', nfl), ('nhl', nhl)):
                    where = f'[{sport} {theme} {w}]'
                    uri = Path(path).resolve().as_uri()
                    ctx, page = await new_page(browser, theme, w, h)
                    await page.goto(uri + '#method')
                    await page.wait_for_timeout(300)
                    f = await page.evaluate(FOCUS)
                    if f['tag'] != 'H2':
                        report.append(f'{where} arriving at #method left focus on {f["tag"]}')
                    elif f['outline'] != 'none':
                        report.append(f'{where} arriving at #method drew a {f["outline"]} outline round "{f["text"]}"')
                    await ctx.close()

                    first, y1, second = TRIPS[sport]
                    ctx, page = await new_page(browser, theme, w, h)
                    await page.goto(uri)
                    await page.wait_for_timeout(300)
                    if first != 'board':
                        await page.evaluate(TAP, first)
                        await page.wait_for_timeout(150)
                    await page.evaluate(f'window.scrollTo(0, {y1})')
                    await page.wait_for_timeout(300)
                    left = await page.evaluate('scrollY')
                    await page.evaluate(TAP, second)
                    await page.wait_for_timeout(200)
                    f = await page.evaluate(FOCUS)
                    if f['tag'] != 'H2' or f['outline'] != 'none':
                        report.append(f'{where} a tap to {second} focused {f["tag"]} with a {f["outline"]} outline')
                    await page.evaluate('window.scrollTo(0, 400)')
                    await page.wait_for_timeout(300)
                    left2 = await page.evaluate('scrollY')
                    await page.go_back()
                    await page.wait_for_timeout(400)
                    back = await page.evaluate('scrollY')
                    await page.go_forward()
                    await page.wait_for_timeout(400)
                    fwd = await page.evaluate('scrollY')
                    if left < 100:
                        report.append(f'{where} {first} did not scroll ({left}); nothing to come back to')
                    elif abs(back - left) > 2:
                        report.append(f'{where} Back to {first} put it at {back}, left at {left}')
                    if left2 > 100 and abs(fwd - left2) > 2:
                        report.append(f'{where} Forward to {second} put it at {fwd}, left at {left2}')
                    await ctx.close()
        await browser.close()
    return report


#: Item 10's capture-phase push and its scroll keeping, as they read in the
#: NHL's built page, and the bubbling push it replaced.
NEW = """    if(same(want)) return;
    saveScroll();
    history.pushState({y: 0}, '', want);
  }, true);"""
OLD = """    if(!same(want)) history.pushState(null, '', want);
  });"""
MANUAL = "  try{ if('scrollRestoration' in history) history.scrollRestoration = 'manual'; }catch(e){}\n"
RESTORE = "    if(y && window.scrollTo) window.scrollTo(0, y);\n"


def self_test(tmp):
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    nhl = tmp / 'return-nhl.html'
    subprocess.run([sys.executable, 'tests/browser/build_nhl.py', '--out', str(nhl)], cwd=ROOT, check=True, capture_output=True)
    subprocess.run([sys.executable, '-m', 'src.sports.nfl.generate_dashboard'], cwd=ROOT, check=True, capture_output=True)
    html = nhl.read_text(encoding='utf-8')
    if html.count(NEW) != 1 or html.count(MANUAL) != 1 or html.count(RESTORE) != 1:
        return [f'self-test: the NHL page holds {html.count(NEW)} capture pushes, {html.count(MANUAL)} manual '
                f'restorations and {html.count(RESTORE)} restores, expected 1 each']
    bad = tmp / 'return-nhl-old.html'
    bad.write_text(html.replace(NEW, OLD).replace(MANUAL, '').replace(RESTORE, ''), encoding='utf-8')
    nfl = ROOT / 'index.html'
    problems = [f'self-test: the real pages should be clean: {r}' for r in asyncio.run(check_pages(nfl, nhl))]
    if not any(r.startswith('[nhl') and 'Forward' in r for r in asyncio.run(check_pages(nfl, bad))):
        problems.append('self-test: the NHL page without the scroll keeping was not reported')
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
