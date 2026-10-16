"""The "Next games" strip on every page and the best pick on each home card (Stage 80 item 52, the 2026-10-13 UI/UX audit's F1 and F2).

Measured 2026-10-14 on a site built from main, at 390 and 1440 px in both
themes: no page named another sport's games (0 cards for the next games on
the home, the NFL, the NHL and the NBA), and no home card named a pick (the
NHL's said "Picks this season" and "First puck drop" only). Mark chose the
small cards (option B) on 2026-10-14, on all four pages, with the NFL
preview's lean and, for a game whose pick is not saved yet, when it will be.

The build reads each sport's next games once (src/site/home.py slate()): a
saved pick's side and the chance its leading model gave it, the preview's
lean, or the run that will save the pick, by each sport's own lock rule
(read, not changed: lock_run is held to GameLock.decide below). The home's
cards name the strongest pick from it; the site build puts the strip and
the slate on every page that has the empty #site-strip, after all four are
built, so a sport's own build still reads only its own files.

Run with: pytest tests/test_tonight_strip.py -v
"""
import json
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from src.site import build, home
from src.sports.nba import lock as nba_lock
from src.sports.nhl import lock as nhl_lock

ROOT = Path(__file__).resolve().parents[1]
STRIP = (ROOT / 'src' / 'core' / 'strip.js').read_text(encoding='utf-8')
HOME_JS = (ROOT / 'src' / 'site' / 'home' / 'home.js').read_text(encoding='utf-8')
NODE = shutil.which('node')
NOW = datetime(2026, 10, 14, 22, 0, tzinfo=UTC)          # Wednesday 6 PM in New York


def write(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding='utf-8')


def node(code):
    if not NODE:
        pytest.skip('node not available')
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8',
                       env={**os.environ, 'TZ': 'America/New_York'})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


# ---------- the slate ----------

@pytest.mark.parametrize('lock', [nhl_lock, nba_lock], ids=['nhl', 'nba'])
def test_the_run_named_is_the_run_that_saves_the_game(lock):
    """Every start over a week, every half hour and a few odd minutes: the
    run lock_run names is the first at which GameLock.decide locks it."""
    rule = lock.GameLock()
    base = datetime(2026, 10, 19, tzinfo=UTC)
    for step in range(0, 7 * 48):
        start = base + timedelta(minutes=30 * step + (7 if step % 5 == 0 else 0))
        named = home.lock_run(start, lock.RUNS_UTC, lock.SLACK)
        slate = pd.DataFrame([{'game_id': 'g', 'status': 'scheduled', 'slate': start.date().isoformat(),
                               'start_utc': pd.Timestamp(start)}])
        # The daily run asks decide() at each run's own time; the first run
        # at which it locks the game is the run that saves it.
        t, first = lock.next_run(start - timedelta(days=3)).to_pydatetime(), None
        while t < start:
            if 'g' in rule.decide(slate, t).lock:
                first = t
                break
            t = lock.next_run(t).to_pydatetime()
        assert named == first, (start, named, first)


def test_the_run_named_matches_the_boards_for_tonight():
    start = datetime(2026, 10, 15, 23, 0, tzinfo=UTC)   # Thursday 7 PM in New York
    assert home.lock_run(start, nhl_lock.RUNS_UTC, nhl_lock.SLACK) == datetime(2026, 10, 15, 21, 0, tzinfo=UTC)
    assert home.lock_run(start, nba_lock.RUNS_UTC, nba_lock.SLACK) == datetime(2026, 10, 15, 21, 30, tzinfo=UTC)


def test_a_day_sports_games_carry_the_saved_pick_or_when_it_is_saved(tmp_path):
    games = [{'game_id': '1', 'slate': '2026-10-14', 'start_utc': '2026-10-14T23:30:00Z', 'home': 'WSH', 'away': 'MTL',
              'status': 'scheduled', 'game_type': 'regular'},
             {'game_id': '2', 'slate': '2026-10-14', 'start_utc': '2026-10-15T00:30:00Z', 'home': 'COL', 'away': 'DAL',
              'status': 'scheduled', 'game_type': 'regular'},
             {'game_id': '3', 'slate': '2026-10-15', 'start_utc': '2026-10-15T23:00:00Z', 'home': 'TOR', 'away': 'BUF',
              'status': 'scheduled', 'game_type': 'regular'},
             {'game_id': '4', 'slate': '2026-10-15', 'start_utc': '2026-10-15T23:00:00Z', 'home': 'OTT', 'away': 'NYI',
              'status': 'postponed', 'game_type': 'regular'},
             {'game_id': '5', 'slate': '2026-10-13', 'start_utc': '2026-10-13T23:00:00Z', 'home': 'BOS', 'away': 'NYR',
              'status': 'final', 'game_type': 'regular'},
             {'game_id': '6', 'slate': '2026-10-14', 'start_utc': '2026-10-14T23:00:00Z', 'home': 'PIT', 'away': 'CBJ',
              'status': 'scheduled', 'game_type': 'preseason'}]
    write(tmp_path / 'results/nhl/schedule_2026.json', {'games': games})
    write(tmp_path / 'predictions/nhl/2026/1.json', {'model_a': 0.62, 'model_b': 0.511, 'pick': 'WSH'})
    write(tmp_path / 'predictions/nhl/2026/2.json', {'model_a': 0.57, 'model_b': None, 'pick': 'COL'})
    rows = home.day_slate('nhl', ('regular', 'playoff'), nhl_lock.RUNS_UTC, nhl_lock.SLACK, tmp_path, NOW)
    assert rows == [
        {'s': 'nhl', 't': '2026-10-14T23:30:00Z', 'a': 'MTL', 'h': 'WSH', 'k': 'pick', 'p': 'WSH', 'c': 51, 'e': True},
        {'s': 'nhl', 't': '2026-10-15T00:30:00Z', 'a': 'DAL', 'h': 'COL', 'k': 'pick', 'p': 'COL', 'c': 57, 'e': False},
        {'s': 'nhl', 't': '2026-10-15T23:00:00Z', 'a': 'BUF', 'h': 'TOR', 'k': 'wait', 'l': '2026-10-15T21:00:00Z'},
    ], 'Model B leads, else Model A; a game played, postponed or out of season is not named'


def test_an_away_pick_carries_the_away_sides_chance(tmp_path):
    write(tmp_path / 'results/nba/schedule_2026.json', {'games': [
        {'game_id': '9', 'slate': '2026-10-20', 'start_utc': '2026-10-20T23:30:00Z', 'home': 'NYK', 'away': 'BOS',
         'status': 'scheduled', 'game_type': 'regular'}]})
    write(tmp_path / 'predictions/nba/2026/9.json', {'model_a': 0.4, 'model_b': 0.36, 'pick': 'BOS'})
    rows = home.day_slate('nba', ('regular',), nba_lock.RUNS_UTC, nba_lock.SLACK, tmp_path, NOW)
    assert rows[0]['p'] == 'BOS' and rows[0]['c'] == 64 and rows[0]['e'] is False


def test_the_nfl_names_model_bs_side_for_its_locked_week_and_leans_for_the_preview(tmp_path):
    def g(home_, away, day, clock, b):
        return {'home': home_, 'away': away, 'gameday': day, 'gametime_et': clock, 'model_b_home_win_prob': b}
    write(tmp_path / 'predictions/nfl/2026_week5.json', [g('DAL', 'TB', '2026-10-08', '20:15', 0.8),
                                                          g('GB', 'CHI', '2026-10-18', '13:00', 0.43)])
    write(tmp_path / 'predictions/nfl/preview/2026_week6.json', [g('DEN', 'SEA', '2026-10-15', '20:15', 0.443)])
    write(tmp_path / 'predictions/nfl/preview/2026_week5.json', [g('X', 'Y', '2026-10-18', '13:00', 0.9)])
    rows = home.nfl_slate(tmp_path, NOW)
    assert rows == [
        {'s': 'nfl', 't': '2026-10-18T17:00:00Z', 'a': 'CHI', 'h': 'GB', 'k': 'pick', 'p': 'CHI', 'c': 57, 'e': False},
        {'s': 'nfl', 't': '2026-10-16T00:15:00Z', 'a': 'SEA', 'h': 'DEN', 'k': 'lean', 'p': 'SEA', 'c': 56, 'e': False},
    ], 'a game already played is left out, and so is a preview of the locked week'


def test_the_home_carries_the_slate_in_start_order(tmp_path):
    write(tmp_path / 'predictions/nfl/preview/2026_week6.json', [])
    f = home.facts(tmp_path, NOW)
    assert f['slate'] == []
    rows = home.slate(ROOT, NOW)
    assert rows == sorted(rows, key=lambda r: r['t']) and {r['s'] for r in rows} <= {'nfl', 'nhl', 'nba'}


# ---------- the strip ----------

ROWS = [
    {'s': 'nhl', 't': '2026-10-14T21:30:00Z', 'a': 'OLD', 'h': 'GAM', 'k': 'pick', 'p': 'GAM', 'c': 60, 'e': False},
    {'s': 'nhl', 't': '2026-10-14T23:30:00Z', 'a': 'MTL', 'h': 'WSH', 'k': 'pick', 'p': 'WSH', 'c': 51, 'e': True},
    {'s': 'nhl', 't': '2026-10-15T00:30:00Z', 'a': 'DAL', 'h': 'COL', 'k': 'pick', 'p': 'COL', 'c': 57, 'e': False},
    {'s': 'nhl', 't': '2026-10-15T23:00:00Z', 'a': 'BUF', 'h': 'TOR', 'k': 'wait', 'l': '2026-10-15T21:00:00Z'},
    {'s': 'nfl', 't': '2026-10-16T00:15:00Z', 'a': 'SEA', 'h': 'DEN', 'k': 'lean', 'p': 'SEA', 'c': 56, 'e': False},
    {'s': 'nba', 't': '2026-10-20T19:00:00Z', 'a': 'BOS', 'h': 'NYK', 'k': 'wait', 'l': '2026-10-14T21:30:00Z'},
    {'s': 'nba', 't': '2026-10-21T23:30:00Z', 'a': 'LAL', 'h': 'GSW', 'k': 'wait', 'l': None},
    {'s': 'nba', 't': '2026-10-22T23:30:00Z', 'a': 'SEVENTH', 'h': 'X', 'k': 'wait', 'l': None},
]


def strip(rows=ROWS, home_page=True, now='2026-10-14T22:00:00Z'):
    dom = ("const box = {hidden: true, innerHTML: ''};\n"
           f"const data = {{textContent: {json.dumps(json.dumps(rows))}}};\n"
           f"const document = {{documentElement: {{hasAttribute: a => a === 'data-site-home' && {str(home_page).lower()}}},\n"
           "  getElementById: id => id === 'site-strip' ? box : id === 'site-strip-data' ? data : null};\n"
           f"Date.now = () => Date.parse('{now}');\n")
    return node(dom + STRIP + "\nconsole.log(JSON.stringify(box));")


def cards(html):
    return re.findall(r'<a class="ts-item" href="([^"]*)" aria-label="([^"]*)">(.*?)</a>', html)


def test_the_strip_shows_the_next_six_games_still_to_start():
    box = strip()
    assert box['hidden'] is False
    got = cards(box['innerHTML'])
    assert len(got) == 6, 'the next six'
    assert 'OLD' not in box['innerHTML'] and 'SEVENTH' not in box['innerHTML']
    assert [h for h, _, _ in got] == ['nhl/', 'nhl/', 'nhl/', 'nfl/', 'nba/', 'nba/']


def test_each_card_says_the_pick_the_lean_or_when_the_pick_is_saved():
    got = cards(strip()['innerHTML'])
    lines = [re.search(r'<span class="ts-pick[^"]*">([^<]*)</span>', c).group(1) for _, _, c in got]
    assert lines == ['WSH 51% · even', 'COL 57%', 'Pick at 5 PM', 'Leans SEA 56%', 'Pick before the start', 'Pick before the start']
    assert '<span class="ts-bar" aria-hidden="true"><i style="width:57%"></i></span>' in got[1][2], 'a saved pick draws its chance'
    assert 'ts-bar' not in got[2][2] and 'ts-bar' not in got[3][2], 'a lean or a waiting game draws none'
    assert '<span class="ts-pick is-pick">COL 57%</span>' in got[1][2]


def test_each_card_says_when_in_the_visitors_time_zone_and_reads_as_one_sentence():
    got = cards(strip()['innerHTML'])
    assert got[0][1] == 'NHL: MTL at WSH, 7:30 PM. WSH 51% · even.'
    assert got[2][1] == 'NHL: BUF at TOR, Thu 7:00 PM. Pick at 5 PM.'
    assert got[4][1] == 'NBA: BOS at NYK, Tue time TBD. Pick before the start.', 'a weekday NBA tip before 5 PM is not a time'


def test_on_a_sports_page_the_cards_lead_up_a_level_and_the_heading_is_a_step_down():
    box = strip(home_page=False)
    assert [h for h, _, _ in cards(box['innerHTML'])][:1] == ['../nhl/']
    assert '<h3 id="ts-title">Next games</h3>' in box['innerHTML']
    assert '<h2 id="ts-title">Next games</h2>' in strip()['innerHTML']


def test_with_nothing_ahead_the_strip_stays_hidden():
    assert strip(now='2026-11-30T00:00:00Z') == {'hidden': True, 'innerHTML': ''}
    assert strip(rows=[]) == {'hidden': True, 'innerHTML': ''}


def test_the_strip_draws_the_homes_marks():
    parts = re.search(r'const ICON_PARTS = \{.*?\n\s*\};', STRIP, re.S).group(0)
    home_parts = re.search(r'const ICON_PARTS = \{.*?\n\};', HOME_JS, re.S).group(0)

    def squash(s):
        return re.sub(r"\s+", " ", s)
    assert squash(parts) == squash(home_parts), "strip.js and home.js draw the sports' marks apart"


# ---------- the best pick on each home card ----------

def best(rows, now='2026-10-14T22:00:00Z'):
    fn = re.search(r'function bestPick\(.*?\n\}\n', HOME_JS, re.S).group(0)
    return node(f"const NOW = Date.parse('{now}');\n" + fn
                + f"console.log(JSON.stringify(bestPick({json.dumps(rows)}, t => 'T' + new Date(t).getUTCHours())));")


def test_a_card_names_its_strongest_pick_still_to_play():
    assert best(ROWS[:3]) == 'COL 57% over DAL · T0', 'the strongest not started; a game under way is not named'
    away = [{'s': 'nba', 't': '2026-10-20T23:30:00Z', 'a': 'BOS', 'h': 'NYK', 'k': 'pick', 'p': 'BOS', 'c': 64, 'e': False}]
    assert best(away) == 'BOS 64% over NYK · T23'
    assert best(ROWS[3:4]) is None, 'a game with no pick yet names nothing'


def test_each_card_asks_for_its_own_best_pick():
    assert "if(best) rows.push([`Strongest ${kind}, Week ${wk}`, best]);" in HOME_JS
    assert "const best = bestPick(slateOf(START_SPORT[start]).filter(r => r.k === 'pick' && dayKey(Date.parse(r.t)) === dayKey(NOW)), atClock);" in HOME_JS
    assert "if(best) rows.push([`Best pick ${evening ? 'tonight' : 'today'}`, best]);" in HOME_JS
    assert "const START_SPORT = {'puck drop': 'nhl', 'tip-off': 'nba'};" in HOME_JS


# ---------- the build puts it on every page ----------

TEMPLATES = ['src/site/home/page.html', 'src/dashboard/body.html', 'src/sports/nhl/pages/body.html',
             'src/sports/nba/pages/body.html']


@pytest.mark.parametrize('rel', TEMPLATES)
def test_every_page_has_a_place_for_it(rel):
    assert (ROOT / rel).read_text(encoding='utf-8').count(
        '<div class="ts" id="site-strip" role="region" aria-labelledby="ts-title" hidden></div>') == 1


def test_the_build_puts_the_slate_and_the_script_on_a_page_once(tmp_path):
    page = tmp_path / 'index.html'
    page.write_text('<html><body><div class="ts" id="site-strip" hidden></div></body></html>', encoding='utf-8')
    block = build.strip_block([{'s': 'nhl', 't': '</script>'}])
    assert build.inject_strip(page, block) and build.inject_strip(page, block)
    html = page.read_text(encoding='utf-8')
    assert html.count('id="site-strip-data"') == 1 and html.count('<script data-site-strip>') == 1, 'a kept page is not given two'
    assert html.index('<script data-site-strip>') < html.index('</body>')
    assert '</script>"' not in html, 'the slate cannot close its script'
    assert '/*' not in html.split('<script data-site-strip>')[1], 'its comments are taken out, as every page has its own'
    other = tmp_path / 'other.html'
    other.write_text('<html><body>no strip here</body></html>', encoding='utf-8')
    assert not build.inject_strip(other, block) and 'site-strip' not in other.read_text(encoding='utf-8')


def test_a_sport_that_was_not_published_has_no_cards(tmp_path):
    rows = [{'s': s, 't': '2026-10-15T00:00:00Z'} for s in ('nfl', 'nhl', 'nba')]
    for rel in ('index.html', 'nfl/index.html', 'nhl/index.html'):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text('<body><div id="site-strip"></div></body>', encoding='utf-8')
    results = [build.SportResult('nfl', built=True), build.SportResult('nhl', built=True), build.SportResult('nba')]
    assert build.add_strip(tmp_path, results, lambda: rows) == ['index.html', 'nfl/index.html', 'nhl/index.html']
    data = re.search(r'id="site-strip-data" data-site-strip>(.*?)</script>', (tmp_path / 'index.html').read_text(encoding='utf-8')).group(1)
    assert [r['s'] for r in json.loads(data)] == ['nfl', 'nhl']


def test_a_slate_that_fails_publishes_the_pages_without_it(tmp_path):
    def boom():
        raise ValueError('no schedule')
    (tmp_path / 'index.html').write_text('<body><div id="site-strip"></div></body>', encoding='utf-8')
    assert build.add_strip(tmp_path, [build.SportResult('nfl', built=True)], boom) == []
    assert 'site-strip-data' not in (tmp_path / 'index.html').read_text(encoding='utf-8')
    assert 'add_strip(out, results)' in Path(build.__file__).read_text(encoding='utf-8')
