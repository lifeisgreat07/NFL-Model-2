"""Every board row says the pick that was saved (Stage 96 item 46; audit 7, T9).

The other browser checks measure how a page looks and moves. None of them
read what a row says against what was saved, so a page could show a pick
the repository does not hold, or the right teams with the wrong side, and
every check would stay green. This opens each sport's real board as a phone
sees it (390 px, the width that shows rows), reads every row's game, pick
and percentage, and compares them with predictions/:

- NHL and NBA: the row's game id (`aria-controls="<sport>-detail-<id>"`)
  names predictions/<sport>/<season>/<id>.json; the row must show that
  file's pick and the probability of it from the model the file says made
  it (`pick_model`), in whole percent. A row with no file must show no
  percentage.
- NFL: the row opens `card-<n>`, whose `data-game` is `<season>_week<w>-<away>-<home>`;
  the game is read from predictions/nfl/<season>_week<w>.json, or the
  preview of that week before it locks. Model B's home probability when it
  has one, else Model A's, as the board picks, rounded once to a whole
  percent (0.8047 shows 80%). Within CARD_EVEN_BAND points of 50 (read from
  app.js) the row says Toss-up.

A board with no saved pick on it (an NBA Monday morning) steps back a week
once, so the check always compares something.

`--self-test` copies predictions/ and swaps the side of one pick the board
shows, as a rewind to an older file would, and fails unless that row is
reported; the real files must come back clean.

Usage:
  python tests/browser/check_board_picks.py --nfl index.html --nhl nhl.html --nba nba.html [--pred predictions]
  python tests/browser/check_board_picks.py --self-test --nfl index.html --nhl nhl.html --nba nba.html --tmp <dir>
"""
import argparse
import asyncio
import json
import math
import re
import shutil
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
ROWS = """(sport) => [...document.querySelectorAll(`.${sport}-row`)].filter(r => r.offsetParent !== null).map(r => {
  const card = sport === 'nfl' ? document.getElementById(r.getAttribute('aria-controls')) : null;
  return {id: sport === 'nfl' ? (card && card.dataset.game) : (r.getAttribute('aria-controls') || '').replace(`${sport}-detail-`, ''),
          pick: r.querySelector(`.${sport}-row-pick`).textContent.trim()};
})"""
PICK = re.compile(r'^([A-Z]{2,4}) (\d+)%')
EVEN_BAND = float(re.search(r'const CARD_EVEN_BAND = ([\d.]+);',
                            (ROOT / 'src' / 'dashboard' / 'app.js').read_text(encoding='utf-8')).group(1))


def whole(p):
    """Percent as the pages round it (Math.round: halves up)."""
    return math.floor(p * 100 + 0.5)


def day_pick(pred, sport, gid):
    """(team, percent) a saved NHL or NBA pick should show, or None when none was saved."""
    files = list((pred / sport).glob(f'*/{gid}.json'))
    if not files:
        return None
    rec = json.loads(files[0].read_text(encoding='utf-8'))
    lead = rec[rec['pick_model']]
    return rec['pick'], whole(lead if rec['pick'] == rec['home'] else 1 - lead)


def nfl_pick(pred, game):
    """(team, percent) the NFL board should show for '<season>_week<w>-<away>-<home>', or None.
    The team is None inside the even band, where the row says Toss-up."""
    week, away, home = game.rsplit('-', 2)
    for path in (pred / 'nfl' / f'{week}.json', pred / 'nfl' / 'preview' / f'{week}.json'):
        if path.exists():
            for g in json.loads(path.read_text(encoding='utf-8')):
                if g['home'] == home and g['away'] == away:
                    b = g.get('model_b_home_win_prob')
                    h = b if b is not None else g['model_a_home_win_prob']
                    v = round(h * 100, 2)  # as generate_dashboard stores mktB_home / fbA_home
                    if abs(v - 50) < EVEN_BAND:
                        return None, math.floor(max(v, 100 - v) + 0.5)
                    return (home, math.floor(v + 0.5)) if v >= 50 else (away, math.floor(100 - v + 0.5))
    return None


def compare(sport, rows, pred):
    report, compared = [], []
    for r in rows:
        want = nfl_pick(pred, r['id']) if sport == 'nfl' else day_pick(pred, sport, r['id'])
        got = PICK.match(r['pick'])
        if want is None:
            if got:
                report.append(f'{sport} {r["id"]}: the row shows "{r["pick"]}" and no pick was saved')
            continue
        compared.append(r['id'])
        if want[0] is None:
            if not r['pick'].startswith('Toss-up'):
                report.append(f'{sport} {r["id"]}: the row shows "{r["pick"]}", the saved pick is within '
                              f'{EVEN_BAND:g} points of even (Toss-up)')
            continue
        if not got or (got.group(1), int(got.group(2))) != want:
            report.append(f'{sport} {r["id"]}: the row shows "{r["pick"]}", the saved pick is {want[0]} {want[1]}%')
    return report, compared


async def check(pages, pred, seen=None):
    """Problems found; `seen`, when given, collects each sport's compared row ids."""
    report = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for sport, path in pages.items():
            ctx = await browser.new_context(viewport={'width': 390, 'height': 900})
            page = await ctx.new_page()
            await page.route(lambda u: u.startswith(('http://', 'https://')), lambda r: r.abort())
            await page.goto(Path(path).resolve().as_uri())
            await page.wait_for_timeout(300)
            found, compared = compare(sport, await page.evaluate(ROWS, sport), pred)
            if not compared and await page.locator('#week-prev').count():
                await page.locator('#week-prev').click()
                await page.wait_for_timeout(100)
                found, compared = compare(sport, await page.evaluate(ROWS, sport), pred)
            report += found
            if seen is not None:
                seen[sport] = compared
            if not compared:
                report.append(f'{sport}: no row on the board has a saved pick to compare')
            else:
                print(f'{sport}: {len(compared)} row(s) compared with predictions/')
            await ctx.close()
        await browser.close()
    return report


async def self_test(pages, tmp):
    tmp = Path(tmp)
    copy = tmp / 'predictions'
    shutil.rmtree(copy, ignore_errors=True)
    shutil.copytree(ROOT / 'predictions', copy)
    seen: dict = {}
    problems = [f'self-test: the real files should be clean: {r}'
                for r in await check(pages, ROOT / 'predictions', seen)]
    for sport, path in pages.items():
        if not seen.get(sport):
            problems.append(f'self-test: {sport} has no compared row to swap')
            continue
        target = seen[sport][0]
        swap(copy, sport, target)
        hit = [r for r in await check({sport: path}, copy) if target in r]
        print(f"self-test {sport} swapped {target}: {'caught' if hit else 'MISSED'}")
        if not hit:
            problems.append(f'self-test: {sport} {target} with its pick swapped was not reported')
    return problems


def swap(pred, sport, gid):
    """The other side of one saved pick, as an older file would have it."""
    if sport != 'nfl':
        (path,) = (pred / sport).glob(f'*/{gid}.json')
        rec = json.loads(path.read_text(encoding='utf-8'))
        rec['pick'] = rec['away'] if rec['pick'] == rec['home'] else rec['home']
        for key in ('model_a', 'model_b'):
            if rec.get(key) is not None:
                rec[key] = round(1 - rec[key], 4)
        path.write_text(json.dumps(rec), encoding='utf-8')
        return
    week, away, home = gid.rsplit('-', 2)
    for path in (pred / 'nfl' / f'{week}.json', pred / 'nfl' / 'preview' / f'{week}.json'):
        if path.exists():
            games = json.loads(path.read_text(encoding='utf-8'))
            for g in games:
                if g['home'] == home and g['away'] == away:
                    for key in ('model_a_home_win_prob', 'model_b_home_win_prob'):
                        if g.get(key) is not None:
                            g[key] = round(1 - g[key], 4)
            path.write_text(json.dumps(games), encoding='utf-8')
            return


def main():
    ap = argparse.ArgumentParser()
    for sport in ('nfl', 'nhl', 'nba'):
        ap.add_argument(f'--{sport}')
    ap.add_argument('--pred', default=str(ROOT / 'predictions'))
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--tmp', default='.')
    a = ap.parse_args()
    pages = {s: getattr(a, s) for s in ('nfl', 'nhl', 'nba') if getattr(a, s)}
    if not pages:
        ap.error('give at least one of --nfl, --nhl, --nba')
    report = asyncio.run(self_test(pages, a.tmp) if a.self_test else check(pages, Path(a.pred)))
    for line in report:
        print(line)
    print('OK' if not report else f'{len(report)} problem(s)')
    return 1 if report else 0


if __name__ == '__main__':
    sys.exit(main())
