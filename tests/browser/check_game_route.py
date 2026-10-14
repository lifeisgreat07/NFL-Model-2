"""A game's address opens it (Stage 76 item 9, from the 2026-10-13 UI/UX audit's F4).

No route named a game: #game/<id> opened the board on its default week or
day (measured 2026-10-14). It now opens the game's week or day with its card
open and on screen, and the address keeps the link.

This opens the NFL page at #game/<the first game of its earliest week> and
the NHL's sample page at #game/<its first game>, at 390x844 and 1440x900,
dark and light, and fails unless the board shows that week or day, the
game's card is open, its top is on screen below the top bar, and the
address still names the game.

`--self-test` deletes the route's call to open the game from a copy of each
page and fails unless both are reported.

Usage:
  python tests/browser/check_game_route.py <nfl page.html> <nhl page.html>
  python tests/browser/check_game_route.py --self-test --tmp <dir>
"""
import argparse
import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
SIZES = ((390, 844), (1440, 900))
THEMES = ('dark', 'light')
TOP_BAR = "() => { const b = document.querySelector('.topbar'); return b && getComputedStyle(b).display !== 'none' ? b.getBoundingClientRect().bottom : 0; }"
NFL_CARD = """(key) => { const c = [...document.querySelectorAll('#game-grid > .game-card')].find(c => c.dataset.game === key);
  if(!c) return null;
  const row = document.querySelector(`.nfl-row[aria-controls="${c.id}"]`);
  const phone = row && row.offsetParent;
  const open = !phone || row.getAttribute('aria-expanded') === 'true';
  // On a phone the row names the game, so it is the row that must be on screen, its card below it.
  const top = phone ? row.getBoundingClientRect().top : c.getBoundingClientRect().top;
  return {top, open, week: document.getElementById('week-select').value}; }"""
NHL_CARD = """(id) => { const d = document.getElementById('nhl-detail-' + id);
  if(!d) return null;
  const chip = document.querySelector('.nhl-day-chip[aria-pressed=true]');
  return {top: d.getBoundingClientRect().top, bottom: d.getBoundingClientRect().bottom, open: !d.hidden,
          day: chip ? chip.dataset.day : null}; }"""


async def open_at(browser, uri, theme, w, h, hash_=''):
    ctx = await browser.new_context(viewport={'width': w, 'height': h}, color_scheme=theme, reduced_motion='reduce')
    page = await ctx.new_page()
    await page.route(lambda u: u.startswith(('http://', 'https://')), lambda r: r.abort())
    await page.goto(uri + hash_)
    await page.wait_for_timeout(300)
    return ctx, page


async def check_pages(nfl, nhl):
    report = []
    nfl_uri, nhl_uri = Path(nfl).resolve().as_uri(), Path(nhl).resolve().as_uri()
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx, page = await open_at(browser, nfl_uri, 'dark', 1440, 900)
        # From the page's own data, so a page without the route is measured too.
        key = await page.evaluate("() => { const k = weekKeysSorted[0], g = weeks[k].games[0]; return `${k}-${g.away}-${g.home}`; }")
        await ctx.close()
        ctx, page = await open_at(browser, nhl_uri, 'dark', 1440, 900)
        gid = await page.evaluate('() => DATA.games.slice().sort((a, b) => a.day.localeCompare(b.day))[0]')
        await ctx.close()
        for theme in THEMES:
            for w, h in SIZES:
                where = f'[{theme} {w}]'
                ctx, page = await open_at(browser, nfl_uri, theme, w, h, f'#game/{key}')
                card, bar, hash_ = await page.evaluate(NFL_CARD, key), await page.evaluate(TOP_BAR), await page.evaluate('location.hash')
                if not card:
                    report.append(f'{where} NFL #game/{key}: no card for it (week {await page.evaluate("document.getElementById(\'week-select\').value")})')
                elif not card['open'] or card['top'] < bar - 1 or card['top'] > h / 2:
                    report.append(f'{where} NFL #game/{key}: card open {card["open"]}, top {card["top"]:.0f} (top bar {bar:.0f})')
                if hash_ != f'#game/{key}':
                    report.append(f'{where} NFL #game/{key}: the address became {hash_!r}')
                await ctx.close()
                ctx, page = await open_at(browser, nhl_uri, theme, w, h, f'#game/{gid["id"]}')
                card, bar = await page.evaluate(NHL_CARD, gid['id']), await page.evaluate(TOP_BAR)
                if not card:
                    day = await page.evaluate("() => (document.querySelector('.nhl-day-chip[aria-pressed=true]') || {dataset: {}}).dataset.day")
                    report.append(f'{where} NHL #game/{gid["id"]}: no row for it on {day}, not {gid["day"]}')
                elif not card['open'] or card['top'] < bar - 1 or card['bottom'] > h:
                    report.append(f'{where} NHL #game/{gid["id"]}: card open {card["open"]}, at {card["top"]:.0f} to {card["bottom"]:.0f} (top bar {bar:.0f})')
                await ctx.close()
        await browser.close()
    return report


#: The route's call to open the game, as it reads in each built page.
NFL_OPEN = '  if(r.game) openGame(r.game);\n'
NHL_OPEN = '    if(first.game && route.open) route.open(first.game);\n'


def self_test(tmp):
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    nhl = tmp / 'game-nhl.html'
    subprocess.run([sys.executable, 'tests/browser/build_nhl.py', '--out', str(nhl)], cwd=ROOT, check=True, capture_output=True)
    subprocess.run([sys.executable, '-m', 'src.sports.nfl.generate_dashboard'], cwd=ROOT, check=True, capture_output=True)
    nfl = tmp / 'game-nfl.html'
    shutil.copyfile(ROOT / 'index.html', nfl)
    nfl_html, nhl_html = nfl.read_text(encoding='utf-8'), nhl.read_text(encoding='utf-8')
    if nfl_html.count(NFL_OPEN) != 1 or nhl_html.count(NHL_OPEN) != 1:
        return [f'self-test: the pages hold {nfl_html.count(NFL_OPEN)} and {nhl_html.count(NHL_OPEN)} calls, expected 1 each']
    nfl_bad, nhl_bad = tmp / 'game-nfl-old.html', tmp / 'game-nhl-old.html'
    nfl_bad.write_text(nfl_html.replace(NFL_OPEN, ''), encoding='utf-8')
    nhl_bad.write_text(nhl_html.replace(NHL_OPEN, ''), encoding='utf-8')
    problems = [f'self-test: the real pages should be clean: {r}' for r in asyncio.run(check_pages(nfl, nhl))]
    bad = asyncio.run(check_pages(nfl_bad, nhl_bad))
    if not any('NFL #game/' in r for r in bad):
        problems.append('self-test: the NFL page that does not open the game was not reported')
    if not any('NHL #game/' in r for r in bad):
        problems.append('self-test: the NHL page that does not open the game was not reported')
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
