"""An opened card is on screen (Stage 75 item 3, from the 2026-10-13 UI/UX audit).

Tapping a row near the bottom of a phone opened its card below the fold and
never scrolled: on an 844 px phone the NHL card sat at 612 to 1052 px and the
NFL card at 704 to 1195 (measured 2026-10-13, last row centred first). Each
board now calls revealOpened(card), scrollIntoView({block:'nearest'}), and the
cards keep a scroll margin for the sticky top bar and the fixed bottom nav.

This opens the NFL page and the NHL's sample page at 390x844 and 1440x900,
dark and light, centres the last visible row, taps it, and fails unless the
opened card lies between the top bar's bottom and the bottom nav's top (the
window's bottom where there is no bottom nav). On the NFL phone it also fails
if the opened card repeats the row's "SEA at DEN" header.

`--self-test` deletes the scroll from a copy of each page and fails unless
the card is reported off screen.

Usage:
  python tests/browser/check_card_reveal.py <nfl page.html> <nhl page.html>
  python tests/browser/check_card_reveal.py --self-test --tmp <dir>
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
ROWS = '.nfl-row, .nhl-row, .nba-row'
CENTRE_LAST_JS = f"""() => {{
  const rows = [...document.querySelectorAll('{ROWS}')].filter(r => r.offsetParent);
  if (!rows.length) return -1;
  rows[rows.length - 1].scrollIntoView({{block: 'center'}});
  return rows.length - 1;
}}"""
WHERE_JS = """(id) => {
  const card = document.getElementById(id), r = card.getBoundingClientRect();
  const bar = document.querySelector('.topbar'), nav = document.querySelector('.bottom-nav');
  const top = bar && getComputedStyle(bar).position === 'sticky' ? bar.getBoundingClientRect().bottom : 0;
  // position:fixed elements have no offsetParent, so ask for display instead.
  const bottom = nav && getComputedStyle(nav).display !== 'none' ? nav.getBoundingClientRect().top : innerHeight;
  const header = card.querySelector(':scope > .matchup-header');
  return {top: r.top, bottom: r.bottom, height: r.height, room: [top, bottom],
          header: !!header && header.getBoundingClientRect().height > 0};
}"""


async def check_pages(paths):
    report = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for path in paths:
            for theme in THEMES:
                for w, h in SIZES:
                    where = f'[{Path(path).name} {theme} {w}]'
                    ctx = await browser.new_context(viewport={'width': w, 'height': h}, color_scheme=theme,
                                                    reduced_motion='reduce')
                    page = await ctx.new_page()
                    await page.route(lambda u: u.startswith(('http://', 'https://')), lambda r: r.abort())
                    await page.goto(Path(path).resolve().as_uri())
                    await page.wait_for_timeout(300)
                    n = await page.evaluate(CENTRE_LAST_JS)
                    if n < 0:
                        await ctx.close()
                        continue  # the NFL's desktop board has no rows: its cards are always open
                    row = page.locator(ROWS).filter(visible=True).nth(n)
                    await row.click()
                    await page.wait_for_timeout(150)
                    r = await page.evaluate(WHERE_JS, await row.get_attribute('aria-controls'))
                    top, bottom = r['room']
                    fits = r['height'] <= bottom - top
                    if fits and (r['top'] < top - 1 or r['bottom'] > bottom + 1):
                        report.append(f'{where} the opened card is at {r["top"]:.0f} to {r["bottom"]:.0f}, '
                                      f'outside the room between {top:.0f} and {bottom:.0f}')
                    if not fits and abs(r['top'] - top) > 1:
                        report.append(f'{where} a card taller than the room starts at {r["top"]:.0f}, not {top:.0f}')
                    if '.nfl-row' in await row.evaluate('e => "." + e.className') and r['header']:
                        report.append(f'{where} the opened phone card repeats the row\'s header')
                    print(f'{where} card at {r["top"]:.0f} to {r["bottom"]:.0f}, room {top:.0f} to {bottom:.0f}')
                    await ctx.close()
        await browser.close()
    return report


#: The scroll the item added, as it reads in each built page.
CALL = 'if(open) revealOpened(card);'


def self_test(tmp):
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, '-m', 'src.site.build', '--out', str(tmp / 'reveal-site')], cwd=ROOT,
                   check=True, capture_output=True)
    subprocess.run([sys.executable, 'tests/browser/build_nhl.py', '--out', str(tmp / 'reveal-nhl.html')],
                   cwd=ROOT, check=True, capture_output=True)
    pages = [tmp / 'reveal-site' / 'nfl' / 'index.html', tmp / 'reveal-nhl.html']
    problems = [f'self-test: the real page should be clean: {r}' for r in asyncio.run(check_pages(pages))]
    for page in pages:
        html = page.read_text(encoding='utf-8')
        if html.count(CALL) != 1:
            problems.append(f'self-test: {page.name} holds {html.count(CALL)} copies of the scroll, expected 1')
            continue
        bad = page.with_name(page.stem + '-noscroll.html')
        bad.write_text(html.replace(CALL, ''), encoding='utf-8')
        if not any('outside the room' in r for r in asyncio.run(check_pages([bad]))):
            problems.append(f'self-test: {page.name} without the scroll was not reported')
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
