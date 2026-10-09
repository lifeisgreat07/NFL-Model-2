"""The NHL's day board, driven in Chromium (Stage 64 item 4).

`tests/browser/check_page.py` checks what a page shows when it opens. The
NHL board now shows one day and keeps each game's card folded under its row,
so most of it is reached only by clicking. This script clicks: at a phone
width (390) and a desktop width (1280), in the dark theme and the light, it
presses each of the week's seven day buttons and opens every row, and
reports:

- a day button that does not become the pressed one, or a list whose rows
  are not that day's games (counted from the page's own data);
- a summary line that is missing or does not count the day's games;
- a row that does not open its card, or does not say it is open
  (`aria-expanded`), or whose card stays visible once closed;
- a row or day button under 44px tall (a phone tap target);
- the page wider than the window, with a row open;
- a page error.

`--self-test` first builds the sample page, then three broken copies of it,
each with one defect written in, and fails unless every one is reported:
rows that do not open, a day strip that does not move, a row that never
says it is open. The real page must come back clean.

Usage:
  python tests/browser/check_nhl_day.py <nhl page.html>
  python tests/browser/check_nhl_day.py --self-test --tmp <dir>
"""
import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
WIDTHS = (390, 1280)
THEMES = ('dark', 'light')
TARGET_MIN = 44

DAY_JS = """() => {
  const data = JSON.parse(document.getElementById('nhl-data').textContent);
  const chips = [...document.querySelectorAll('.nhl-day-chip')];
  return {chips: chips.map(c => c.dataset.day), games: data.games.map(g => g.day)};
}"""
STATE_JS = """(day) => {
  const chip = document.querySelector(`.nhl-day-chip[data-day="${day}"]`);
  const rows = [...document.querySelectorAll('.nhl-row')];
  const summary = document.querySelector('.nhl-day-summary');
  return {
    pressed: chip ? chip.getAttribute('aria-pressed') : null,
    chipH: chip ? chip.getBoundingClientRect().height : 0,
    rows: rows.length,
    rowH: rows.map(r => r.getBoundingClientRect().height),
    summary: summary ? summary.textContent : null,
  };
}"""
OPEN_JS = """(i) => {
  const row = document.querySelectorAll('.nhl-row')[i];
  const panel = document.getElementById(row.getAttribute('aria-controls'));
  const box = panel ? panel.getBoundingClientRect() : {height: 0};
  return {expanded: row.getAttribute('aria-expanded'), visible: !!panel && !panel.hidden && box.height > 0,
          wide: document.documentElement.scrollWidth > window.innerWidth + 1};
}"""


async def check_page(path):
    report = []
    url = Path(path).resolve().as_uri()
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for theme in THEMES:
            for width in WIDTHS:
                where = f'[{theme} {width}]'
                ctx = await browser.new_context(viewport={'width': width, 'height': 900}, color_scheme=theme,
                                                reduced_motion='reduce')
                page = await ctx.new_page()
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)))
                await page.route(lambda u: u.startswith(('http://', 'https://')), lambda r: r.abort())
                await page.goto(url)
                await page.wait_for_timeout(200)
                info = await page.evaluate(DAY_JS)
                if len(info['chips']) != 7:
                    report.append(f'{where} the strip has {len(info["chips"])} days, not 7')
                for day in info['chips']:
                    await page.click(f'.nhl-day-chip[data-day="{day}"]')
                    await page.wait_for_timeout(50)
                    s = await page.evaluate(STATE_JS, day)
                    want = info['games'].count(day)
                    if s['pressed'] != 'true':
                        report.append(f'{where} {day}: its button is not the pressed one after a click')
                    if s['rows'] != want:
                        report.append(f'{where} {day}: {s["rows"]} rows for {want} games')
                    if s['summary'] is None or (want and not s['summary'].startswith(f'{want} game')):
                        report.append(f'{where} {day}: the summary says {s["summary"]!r}')
                    if s['chipH'] < TARGET_MIN:
                        report.append(f'{where} {day}: the day button is {s["chipH"]:.0f}px tall')
                    for i, h in enumerate(s['rowH']):
                        if h < TARGET_MIN:
                            report.append(f'{where} {day} row {i}: {h:.0f}px tall')
                    for i in range(s['rows']):
                        await page.locator('.nhl-row').nth(i).click()
                        o = await page.evaluate(OPEN_JS, i)
                        if o['expanded'] != 'true':
                            report.append(f'{where} {day} row {i}: does not say it is open')
                        if not o['visible']:
                            report.append(f'{where} {day} row {i}: its card does not open')
                        if o['wide']:
                            report.append(f'{where} {day} row {i}: the page is wider than the window')
                        await page.locator('.nhl-row').nth(i).click()
                        c = await page.evaluate(OPEN_JS, i)
                        if c['expanded'] != 'false' or c['visible']:
                            report.append(f'{where} {day} row {i}: does not close')
                report += [f'{where} page error: {e}' for e in errors]
                await ctx.close()
        await browser.close()
    return report


# ---------------------------------------------------------------- self-test
#: Each defect: (name, the text to find in the built page, what replaces it, the finding expected).
DEFECTS = (
    ('rows-do-not-open', ".hidden = !open;", ".hidden = true;", 'its card does not open'),
    ('strip-does-not-move', "currentDay = btn.dataset.day;", "", 'rows for'),
    ('never-says-open', "btn.setAttribute('aria-expanded', String(open));", "", 'does not say it is open'),
)


def build_sample(out):
    r = subprocess.run([sys.executable, str(ROOT / 'tests' / 'browser' / 'build_nhl.py'), '--out', str(out)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f'could not build the sample page: {r.stderr[-800:]}')
    return out


async def self_test(tmp):
    failed = []
    real = build_sample(Path(tmp) / 'nhl_day_real.html')
    html = real.read_text(encoding='utf-8')
    for name, find, replace, expect in DEFECTS:
        if html.count(find) != 1:
            print(f'self-test {name}: ANCHOR ({html.count(find)} matches)')
            failed.append(name)
            continue
        broken = Path(tmp) / f'nhl_day_{name}.html'
        broken.write_text(html.replace(find, replace), encoding='utf-8')
        report = await check_page(broken)
        hit = [r for r in report if expect in r]
        print(f"self-test {name}: {'caught' if hit else 'MISSED'} ({len(report)} finding(s))")
        if not hit:
            failed.append(name)
    report = await check_page(real)
    print(f"self-test real page: {'FALSE ALARM' if report else 'clean'} ({len(report)} finding(s))")
    for line in report[:10]:
        print('  ' + line)
    if report:
        failed.append('real')
    return failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('page', nargs='?')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--tmp', default='.')
    a = ap.parse_args()
    if a.self_test:
        failed = asyncio.run(self_test(a.tmp))
        if failed:
            print(f'SELF-TEST FAILED: {failed}')
            sys.exit(1)
        print('self-test: every defect caught, the real page clean')
        return
    if not a.page:
        ap.error('give the NHL page, or --self-test')
    report = asyncio.run(check_page(a.page))
    for line in report:
        print(line)
    if report:
        print(f'{len(report)} finding(s)')
        sys.exit(1)
    print(f'{a.page}: every day and every row works at {", ".join(map(str, WIDTHS))}px in both themes')


if __name__ == '__main__':
    main()

