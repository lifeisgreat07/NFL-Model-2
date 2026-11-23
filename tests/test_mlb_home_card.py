"""MLB's home card, dark until its page is published (Stage 100 item 4).

Mark (2026-11-23): build the card now, show it from Stage 101. Until the
site build lists 'mlb' among its SPORTS the home has no MLB card at all, not
a "not built" one, and a schedule file alone does not light it. Once lit,
before the first saved pick the card counts down to Opening Day by calendar
day on the visitor's clock, with the first pitch's time, or "time TBD" when
MLB has not set it (`start_time_tbd`); after that it is the NHL's and the
NBA's day card, with "first pitch" for the moment a game begins.

Run with: pytest tests/test_mlb_home_card.py -v
"""
import json
import os
import re
import subprocess
from datetime import UTC, datetime

import pytest

from src.site import build, home
from tests.optional import require_tool

HOME_JS = (home.TEMPLATE / 'home.js').read_text(encoding='utf-8')
NOW = datetime(2026, 3, 20, 16, 0, tzinfo=UTC)
OPENING = '2026-03-26T17:05:00Z'


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding='utf-8')


def season(tmp_path, tbd=False):
    games = [{'start_utc': '2026-03-27T23:10:00Z', 'status': 'scheduled', 'game_type': 'regular'},
             {'start_utc': OPENING, 'status': 'scheduled', 'game_type': 'regular', 'start_time_tbd': tbd},
             {'start_utc': '2026-03-01T18:05:00Z', 'status': 'final', 'game_type': 'spring'},
             {'start_utc': '2026-10-27T00:08:00Z', 'status': 'scheduled', 'game_type': 'world_series'}]
    write(tmp_path / 'results/mlb/schedule_2026.json', {'games': games})


# ---------- the facts ----------

def test_the_card_stays_dark_until_the_site_build_publishes_mlb(tmp_path):
    season(tmp_path)
    assert 'mlb' not in build.SPORTS, 'MLB is published: this test and the docstring move to Stage 101'
    assert home.mlb_facts(tmp_path, NOW) == {'built': False, 'dark': True}, 'a schedule file alone lit the card'
    assert home.facts(tmp_path, NOW)['mlb'] == {'built': False, 'dark': True}


def test_once_published_the_card_knows_opening_day_and_the_saved_picks(tmp_path):
    season(tmp_path)
    f = home.mlb_facts(tmp_path, NOW, published=True)
    assert f['built'] is True and f['first_game'] == OPENING and f['picks'] == 0
    assert f['unset'] == [], 'a set start was listed as unset'
    assert all(g[0] != '2026-03-01T18:05:00Z' for g in f['games']), 'spring training counted as a game'
    write(tmp_path / 'results/mlb/graded_2026.json', [{'result': 'correct'}, {'result': 'wrong'}])
    f = home.mlb_facts(tmp_path, NOW, published=True)
    assert f['picks'] == 2 and f['record']['won'] == 1 and f['record']['lost'] == 1


def test_a_start_mlb_has_not_set_is_listed_as_unset(tmp_path):
    season(tmp_path, tbd=True)
    assert home.mlb_facts(tmp_path, NOW, published=True)['unset'] == [OPENING]


def test_published_with_no_schedule_says_not_built_not_dark(tmp_path):
    assert home.mlb_facts(tmp_path, NOW, published=True) == {'built': False}


# ---------- the card, under node ----------

def card(facts, now='2026-03-20T16:00:00Z', tz='America/New_York'):
    """mlbCard(HOME.mlb) as the page runs it, at `now` on a visitor's clock in `tz`."""
    node = require_tool('node')
    head = HOME_JS[:HOME_JS.index("document.getElementById('home-cards').innerHTML")]
    assert head.count('const NOW = Date.now();') == 1
    head = head.replace('const NOW = Date.now();', f"const NOW = Date.parse('{now}');")
    data = json.dumps({'mlb': facts})
    src = ("const document = {getElementById: () => ({textContent: " + json.dumps(data) + "}), "
           "addEventListener(){}};\n" + head + "\nconsole.log(mlbCard(HOME.mlb));")
    env = {**os.environ, 'TZ': tz}
    return subprocess.run([node, '-e', src], capture_output=True, text=True, encoding='utf-8',
                          env=env, check=True).stdout.strip()


def lit(**over):
    f = {'built': True, 'games': [[OPENING, 'scheduled']], 'first_game': OPENING, 'picks': 0, 'unset': [],
         'record': {'label': 'Picks this season', 'won': 0, 'lost': 0}}
    return {**f, **over}


def status(html):
    return re.search(r'<span class="home-status[^"]*">(.*?)</span>', html).group(1)


def test_no_card_at_all_while_dark_and_not_built_once_published():
    assert card({'built': False, 'dark': True}) == ''
    assert card(None) == ''
    html = card({'built': False})
    assert 'is-unbuilt' in html and 'Not built yet' in html


@pytest.mark.parametrize('now, expected', [
    ('2026-03-20T16:00:00Z', 'Opening Day in 6 days'),
    # 11:30 PM on the 24th in New York: two calendar days, not one and a half.
    ('2026-03-25T03:30:00Z', 'Opening Day in 2 days'),
    ('2026-03-25T16:00:00Z', 'Opening Day tomorrow'),
    ('2026-03-26T13:00:00Z', 'Opening Day today'),
])
def test_the_countdown_is_by_calendar_day_on_the_visitors_clock(now, expected):
    assert status(card(lit(), now)) == expected


def test_the_countdown_card_shows_the_first_pitch_and_links_to_the_board():
    html = card(lit())
    assert 'href="mlb/"' in html and 'data-sport="mlb"' in html and 'Open the MLB board' in html
    assert '<dt>First pitch</dt><dd>Thu 1:05 PM</dd>' in html
    assert '<dt>First pitch</dt><dd>Thu · time TBD</dd>' in card(lit(unset=[OPENING]))


def test_after_the_first_pick_it_is_the_day_card():
    html = card(lit(picks=3, record={'label': 'Picks this season', 'won': 2, 'lost': 1}), '2026-03-26T13:00:00Z')
    assert status(html) == '1 game today' and 'Opening Day' not in html
    assert '<dt>Picks this season</dt><dd>2–1</dd>' in html and '<dt>First first pitch</dt>' not in html
    assert '<dt>First pitch</dt><dd>1:05 PM</dd>' in html
    # A doubleheader once the first game is under way: the next one, as "Next game".
    two = lit(picks=1, games=[[OPENING, 'in_progress'], ['2026-03-26T21:10:00Z', 'scheduled']])
    assert '<dt>Next game</dt><dd>5:10 PM</dd>' in card(two, '2026-03-26T18:00:00Z')
    # The next day with games, before today's: "First pitch" with its weekday.
    assert '<dt>First pitch</dt><dd>Thu 1:05 PM</dd>' in card(lit(picks=1), '2026-03-25T16:00:00Z')


def test_the_other_sports_keep_their_labels():
    assert "MOMENT_LABELS[start] || [`First ${start}`, `Next ${start}`]" in HOME_JS
    assert "const MOMENT_LABELS = {'first pitch': ['First pitch', 'Next game']};" in HOME_JS


def test_the_card_sits_after_the_nba_and_draws_the_pages_ball():
    assert 'nbaCard(HOME.nba)\n  + mlbCard(HOME.mlb) + marchCard(HOME.march);' in HOME_JS
    assert "START_SPORT = {'puck drop': 'nhl', 'tip-off': 'nba', 'first pitch': 'mlb'};" in HOME_JS
    body = (home.ROOT / 'src' / 'sports' / 'mlb' / 'pages' / 'body.html').read_text(encoding='utf-8')
    assert 'M5.2 3.6c2.4 2.2 2.4 10.6 0 12.8M14.8 3.6c-2.4 2.2-2.4 10.6 0 12.8' in body
    assert "mlb: '<g><circle cx=\"10\" cy=\"10\" r=\"8.4\"/>'" in HOME_JS
    assert 'M5.2 3.6c2.4 2.2 2.4 10.6 0 12.8M14.8 3.6c-2.4 2.2-2.4 10.6 0 12.8' in HOME_JS
