"""The home says what was graded since this browser's last visit (Stage 80 item 54, the 2026-10-13 UI/UX audit's F8).

Before, a returning visitor saw the season's records and nothing about what
had changed since they last looked. Each visit now leaves each sport's
record in this browser (localStorage, nothing leaves it), and the next says
what was graded in between: "Since Sunday: NFL 10 of 14 right, NHL 5 of 7
right." A sport with nothing new, or a record that went down (a new season),
is not named; a first visit shows nothing. The session keeps the sentence,
so a reload does not take it away.

Run with: pytest tests/test_home_since.py -v
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'src' / 'site' / 'home' / 'home.js').read_text(encoding='utf-8')
PAGE = (ROOT / 'src' / 'site' / 'home' / 'page.html').read_text(encoding='utf-8')
NODE = shutil.which('node')


def fn(name):
    m = re.search(r'function %s\(.*?\n\}\n' % name, JS, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def run(expr):
    if not NODE:
        pytest.skip('node not available')
    head = ("const HOUR = 3600 * 1000;\nconst SPORT_NAME = {nfl:'NFL', nhl:'NHL', nba:'NBA'};\n"
            + re.search(r'^function dayKey\(.*$', JS, re.M).group(0) + '\n')
    code = head + fn('sinceLabel') + fn('sinceText') + fn('sinceSnapshot') + f'console.log(JSON.stringify({expr}));'
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8',
                       env={**os.environ, 'TZ': 'America/New_York'})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def sports(nfl, nhl, nba=(0, 0)):
    return json.dumps({s: {'built': True, 'record': {'won': w, 'lost': l}}
                       for s, (w, l) in (('nfl', nfl), ('nhl', nhl), ('nba', nba))})


SUN = "Date.parse('2026-10-12T00:00:00Z')"   # Sunday 8 PM in New York
WED = "Date.parse('2026-10-15T00:00:00Z')"   # Wednesday 8 PM


def test_it_says_what_was_graded_since_the_last_visit():
    prev = f"{{at: {SUN}, rec: {{nfl: [39, 25], nhl: [30, 16], nba: [0, 0]}}}}"
    got = run(f"sinceText({prev}, {sports((49, 29), (35, 18))}, {WED})")
    assert got == 'Since Sunday: NFL 10 of 14 right, NHL 5 of 7 right.'


def test_nothing_new_a_new_season_and_a_first_visit_say_nothing():
    same = f"{{at: {SUN}, rec: {{nfl: [49, 29], nhl: [35, 18], nba: [0, 0]}}}}"
    reset = f"{{at: {SUN}, rec: {{nfl: [60, 40], nhl: [30, 16]}}}}"
    got = run(f"[sinceText({same}, {sports((49, 29), (35, 18))}, {WED}), sinceText({reset}, {sports((2, 1), (35, 18))}, {WED}), sinceText(null, {sports((49, 29), (35, 18))}, {WED})]")
    assert got == ['', 'Since Sunday: NHL 5 of 7 right.', '']


def test_the_day_is_named_as_a_person_would():
    got = run("[sinceLabel(Date.parse('2026-10-14T13:00:00Z'), Date.parse('2026-10-15T00:00:00Z')),"
              " sinceLabel(Date.parse('2026-10-14T01:00:00Z'), Date.parse('2026-10-15T00:00:00Z')),"
              " sinceLabel(Date.parse('2026-10-03T16:00:00Z'), Date.parse('2026-10-15T00:00:00Z'))]")
    assert got == ['earlier today', 'yesterday', 'Oct 3']


def visits():
    """The page's own start-up block, run three times against one browser's
    storage: a first visit, a return after Sunday's games were graded, and a
    reload of that return in the same session."""
    if not NODE:
        pytest.skip('node not available')
    block = JS[JS.index("(function(){\n  const el = document.getElementById('home-since');"):]
    block = block[:block.index('})();') + len('})();')]
    head = ("const HOUR = 3600 * 1000;\nconst SPORT_NAME = {nfl:'NFL', nhl:'NHL', nba:'NBA'};\n"
            "const SINCE_KEY = 'site:lastVisit', SINCE_SHOWN = 'site:sinceShown';\n"
            + fn('sinceLabel') + fn('sinceText') + fn('sinceSnapshot'))
    code = (head + "function store(){ const m = {}; return {getItem: k => k in m ? m[k] : null, setItem: (k, v) => { m[k] = String(v); }}; }\n"
            "const localStorage = store(); let sessionStorage = store();\n"
            "const el = {textContent: 'unset'}; const document = {getElementById: () => el};\n"
            "const rec = (a, b) => ({built: true, record: {won: a[0], lost: a[1]}});\n"
            "function load(HOME, NOW){\n" + block + "\nreturn el.textContent; }\n"
            "const out = [load({nfl: rec([39, 25]), nhl: rec([30, 16]), nba: rec([0, 0])}, Date.parse('2026-10-12T00:00:00Z'))];\n"
            "sessionStorage = store();\n"
            "out.push(load({nfl: rec([49, 29]), nhl: rec([35, 18]), nba: rec([0, 0])}, Date.parse('2026-10-15T00:00:00Z')));\n"
            "out.push(load({nfl: rec([49, 29]), nhl: rec([35, 18]), nba: rec([0, 0])}, Date.parse('2026-10-15T00:05:00Z')));\n"
            "console.log(JSON.stringify(out));")
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8', env={**os.environ, 'TZ': 'America/New_York'})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_the_page_shows_it_and_keeps_it_for_the_session():
    assert '<p class="home-since" id="home-since" role="status"></p>' in PAGE
    assert PAGE.index('id="home-since"') < PAGE.index('id="home-score"')
    first, back, reload = visits()
    assert first == '', 'a first visit says nothing'
    assert back == 'Since Sunday: NFL 10 of 14 right, NHL 5 of 7 right.'
    assert reload == back, 'a reload in the same session keeps the line'
