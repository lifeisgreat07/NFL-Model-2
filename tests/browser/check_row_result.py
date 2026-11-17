"""A watched row's last word follows ESPN's scoreboard, not the last build (audit 9, finding D2).

The NHL's and NBA's Day Board rows ended with the word the build saw ("Locked", "Live") while
src/core/scores.js rewrote their clock and score from ESPN, so a finished game read "Final ... Live" and one under
way "Q4 7:01 ... Locked". This opens the NHL's sample page with the scores script on it, the clock frozen at
2026-10-09 02:30 UTC (MIN at BUF started 23:00, VGK at SEA 02:00, both saved as Locked), and ESPN's scoreboard
answered by hand: MIN at BUF final, VGK at SEA in the second period. It fails unless MIN at BUF's row ends
"Grading" and VGK at SEA's ends "Live", and neither shows the build's word.

`--self-test` takes the result slot out of a copy of the page and fails unless the stale words are reported.

Usage:
  python tests/browser/check_row_result.py <nhl-page.html>
  python tests/browser/check_row_result.py --self-test --tmp <dir>
"""
import argparse
import asyncio
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 9, 2, 30, tzinfo=UTC)
WANT = {'MIN@BUF': 'Grading', 'VGK@SEA': 'Live'}


def team(abbr, score, side):
    return {'homeAway': side, 'score': str(score), 'team': {'abbreviation': abbr}}


def event(eid, away, home, as_, hs, state, period, clock, short):
    name = 'STATUS_FINAL' if state == 'post' else 'STATUS_IN_PROGRESS'
    st = {'period': period, 'displayClock': clock, 'type': {'state': state, 'name': name, 'shortDetail': short}}
    return {'id': eid, 'competitions': [{'competitors': [team(away, as_, 'away'), team(home, hs, 'home')],
                                         'status': st}]}


BOARD = {'events': [event('1', 'MIN', 'BUF', 2, 4, 'post', 3, '0:00', 'Final'),
                    event('2', 'VGK', 'SEA', 1, 0, 'in', 2, '10:03', '10:03 - 2nd')]}
ROWS = """() => [...document.querySelectorAll('.nhl-row[data-score-key]')].map(r => ({
  key: r.dataset.scoreKey, live: r.getAttribute('data-score-live'),
  last: r.querySelector('.nhl-row-result').innerText.trim()}))"""


async def check_page(path):
    scores = (ROOT / 'src' / 'core' / 'scores.js').read_text(encoding='utf-8')
    asked = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 1440, 'height': 900}, bypass_csp=True)
        page = await ctx.new_page()
        await page.clock.install(time=NOW)

        async def answer(route):
            asked.append(route.request.url)
            if 'site.api.espn.com' in route.request.url and 'dates=20261008' in route.request.url:
                await route.fulfill(body=json.dumps(BOARD), content_type='application/json')
            else:
                await route.abort()
        await page.route(lambda u: u.startswith(('http://', 'https://')), answer)
        await page.goto(Path(path).resolve().as_uri())
        await page.wait_for_timeout(300)
        await page.add_script_tag(content=scores)
        await page.clock.run_for(2000)
        await page.wait_for_timeout(500)
        rows = await page.evaluate(ROWS)
        await browser.close()
    report = []
    if not any('scoreboard' in u for u in asked):
        report.append('the scores script never asked ESPN for the scoreboard')
    seen = {r['key']: r for r in rows}
    for key, word in WANT.items():
        r = seen.get(key)
        if r is None:
            report.append(f'{key}: no watched row on the page')
        elif r['last'] != word:
            report.append(f'{key}: the row ends "{r["last"]}" with ESPN saying {r["live"]}, not "{word}"')
    return report


SLOT = 'data-score-slot="${p ? \'result\' : \'unpicked\'}"'


def self_test(tmp):
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    nhl = tmp / 'result-nhl.html'
    subprocess.run([sys.executable, 'tests/browser/build_nhl.py', '--out', str(nhl)], cwd=ROOT, check=True,
                   capture_output=True)
    t = nhl.read_text(encoding='utf-8')
    if t.count(SLOT) != 1:
        return [f'self-test: {t.count(SLOT)} copies of the result slot, expected 1']
    stale = tmp / 'result-nhl-stale.html'
    stale.write_text(t.replace(SLOT, 'data-score-slot="none"'), encoding='utf-8')
    problems = [f'self-test: the real page should be clean: {r}' for r in asyncio.run(check_page(nhl))]
    if not any('not "Grading"' in r for r in asyncio.run(check_page(stale))):
        problems.append('self-test: a row without the result slot was not reported')
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
