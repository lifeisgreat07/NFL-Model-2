"""A day-board row and its card say the same pick (Stage 75 item 2, from the 2026-10-13 UI/UX audit).

Inside EVEN_BAND the card said "Too close to call · saved pick TOR" while
its row said "TOR 51%" (NSH at TOR and MIN at BUF on the NHL's sample
week, measured 2026-10-13). Both now print "TOR 51% · even" from one
function, pickText. This opens the NHL's sample page at 390 and 1440 px,
dark and light, presses every day, and for every row with a pick checks
that its card's pick phrase (the headline's bold text, and "· even" when
the line after it says so) is exactly the row's pick text. A page with no
close game, or no pick at all, is a failure: the check would prove nothing.

`--self-test` writes the old row code back into a copy of the page and
fails unless the disagreement is reported.

Usage:
  python tests/browser/check_row_card.py <nhl page.html>
  python tests/browser/check_row_card.py --self-test --tmp <dir>
"""
import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
WIDTHS = (390, 1440)
THEMES = ('dark', 'light')
PAIRS_JS = """() => [...document.querySelectorAll('.nhl-row, .nba-row')].map(row => {
  const pick = row.querySelector('.nhl-row-pick, .nba-row-pick');
  const card = document.getElementById(row.getAttribute('aria-controls'));
  const hl = card && card.querySelector('.card-hl');
  const text = pick ? [...pick.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim() : '';
  // The card's pick phrase: its bold text, and "· even" when the line after it says so.
  const b = hl && hl.querySelector('b'), to = hl && hl.querySelector('.card-hl-to');
  const even = to && to.textContent.trim() === '· even' ? ' · even' : '';
  return {row: row.innerText.replace(/\\n/g, ' | '), pick: text.replace(/\\s+/g, ' '),
          card: b ? (b.textContent.trim() + even).replace(/\\s+/g, ' ') : null};
}).filter(x => x.pick && x.pick !== '—')"""


async def check_page(path):
    report = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for theme in THEMES:
            for width in WIDTHS:
                where = f'[{theme} {width}]'
                ctx = await browser.new_context(viewport={'width': width, 'height': 900}, color_scheme=theme,
                                                reduced_motion='reduce')
                page = await ctx.new_page()
                await page.route(lambda u: u.startswith(('http://', 'https://')), lambda r: r.abort())
                await page.goto(Path(path).resolve().as_uri())
                await page.wait_for_timeout(200)
                pairs, even = 0, 0
                chips = page.locator('.nhl-day-chip, .nba-day-chip')
                for i in range(await chips.count()):
                    await chips.nth(i).click()
                    await page.wait_for_timeout(50)
                    for x in await page.evaluate(PAIRS_JS):
                        pairs += 1
                        even += 'even' in x['pick']
                        if x['card'] != x['pick']:
                            report.append(f'{where} {x["row"]}: the row says "{x["pick"]}", '
                                          f'the card says "{x["card"]}"')
                print(f'{where} {pairs} rows with a pick, {even} of them even')
                if not pairs:
                    report.append(f'{where} no row with a pick to compare')
                elif not even:
                    report.append(f'{where} no close game on the page, so the case this guards is not shown')
                await ctx.close()
        await browser.close()
    return report


#: The NHL's row before Stage 75 item 2, and now.
OLD = """  const lead = p.b !== null && p.b !== undefined ? p.b : p.a;
  const pct = p.pick === g.home ? lead : 1 - lead;
  return `${p.pick} ${Math.round(pct * 100)}%`;
}"""
NEW = """  return pickText(g, p);
}"""


def self_test(tmp):
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    page = tmp / 'row-card-nhl.html'
    subprocess.run([sys.executable, 'tests/browser/build_nhl.py', '--out', str(page)], cwd=ROOT, check=True,
                   capture_output=True)
    html = page.read_text(encoding='utf-8')
    if html.count(NEW) != 1:
        return [f'self-test: the page holds {html.count(NEW)} copies of the row code, expected 1']
    bad = tmp / 'row-card-nhl-old.html'
    bad.write_text(html.replace(NEW, OLD), encoding='utf-8')
    problems = [f'self-test: the real page should be clean: {r}' for r in asyncio.run(check_page(page))]
    if not any('the row says' in r for r in asyncio.run(check_page(bad))):
        problems.append('self-test: the old row was not reported')
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
