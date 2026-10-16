"""Live scores on the rows and cards (Stage 80 item 61, the 2026-10-13 UI/UX audit's F15).

Measured 2026-10-15 on the site built from main, at 390 and 1440 px in both
themes: a game under way showed no score anywhere. The NFL's row kept its
kickoff time and its card said "Kicked off · final score not in yet"; the
NHL's and NBA's rows said Live and their cards "In progress", with the
score only after the next daily run (the NHL's at 10 AM and 5 PM Eastern,
the NBA's at noon and 5:30 PM, so a game's score waited until the next
morning). The audit asked for the daily run to write the scores; no run is
on while games are, so Mark chose (2026-10-15) to have the open page ask
ESPN's public scoreboard instead, which allows a page to (its replies carry
Access-Control-Allow-Origin: *, checked that night for all three leagues).

src/core/scores.js does the asking and the filling; each sport page marks
a game not yet final (scoreMark) and leaves empty slots; the build puts the
script on the three sport pages (src/site/build.py add_scores); their
Content-Security-Policy reaches site.api.espn.com and nothing else
(tests/test_content_security_policy.py).

Run with: pytest tests/test_live_scores.py -v
"""
import inspect
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.site import build

ROOT = Path(__file__).resolve().parents[1]
SCORES = (ROOT / 'src' / 'core' / 'scores.js').read_text(encoding='utf-8')
APP = (ROOT / 'src' / 'dashboard' / 'app.js').read_text(encoding='utf-8')
NHL = (ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js').read_text(encoding='utf-8')
NBA = (ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js').read_text(encoding='utf-8')
CSS = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
NODE = shutil.which('node')


def node(code):
    if not NODE:
        pytest.skip('node not available')
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def pure():
    """scores.js's functions and constants, without the part that needs a page."""
    return SCORES[:SCORES.index('(function(){')]


def function_source(src, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def event(eid, away, home, as_, hs, state, name='STATUS_IN_PROGRESS', period=3, clock='4:12', short='4:12 - 3rd'):
    return {'id': eid, 'competitions': [{
        'status': {'period': period, 'displayClock': clock,
                   'type': {'name': name, 'state': state, 'shortDetail': short}},
        'competitors': [{'homeAway': 'home', 'score': str(hs), 'team': {'abbreviation': home}},
                        {'homeAway': 'away', 'score': str(as_), 'team': {'abbreviation': away}}]}]}


def read(sport, events, now=0):
    return node(pure() + f'console.log(JSON.stringify(scoresRead({json.dumps(sport)}, {json.dumps({"events": events})}, {now})));')


# ---------- reading ESPN's scoreboard ----------

def test_a_game_under_way_is_read_with_both_scores_and_its_clock():
    got = read('nfl', [event('401', 'WSH', 'KC', 17, 14, 'in')], now=5)
    assert got['WSH@KC'] == {'as': 17, 'hs': 14, 'state': 'in', 'clock': 'Q3 4:12', 'at': 5}
    assert got['#401'] == got['WSH@KC'], 'found by ESPN id too (the NBA page has it)'


def test_a_game_not_started_or_without_a_score_is_left_out():
    got = read('nba', [event('1', 'BOS', 'NY', 0, 0, 'pre', name='STATUS_SCHEDULED'),
                       {'id': '2', 'competitions': [{'status': {'type': {'state': 'in'}}, 'competitors': [
                           {'homeAway': 'home', 'score': '', 'team': {'abbreviation': 'GS'}},
                           {'homeAway': 'away', 'score': '3', 'team': {'abbreviation': 'LAL'}}]}]},
                       {'id': '3', 'competitions': []}])
    assert got == {}


def test_a_reply_that_is_not_a_scoreboard_reads_as_nothing():
    for bad in ('null', '{}', '{"events": "x"}', '{"events": [{"competitions": [{"competitors": [{"homeAway": "home"}]}]}]}'):
        assert node(pure() + f'console.log(JSON.stringify(scoresRead("nfl", {bad}, 0)));') == {}, bad


@pytest.mark.parametrize('sport,status,want', [
    ('nfl', {'period': 2, 'displayClock': '0:31', 'type': {'name': 'STATUS_IN_PROGRESS', 'state': 'in'}}, 'Q2 0:31'),
    ('nfl', {'period': 2, 'displayClock': '0:00', 'type': {'name': 'STATUS_HALFTIME', 'state': 'in'}}, 'Half'),
    ('nfl', {'period': 5, 'displayClock': '6:02', 'type': {'name': 'STATUS_IN_PROGRESS', 'state': 'in'}}, 'OT 6:02'),
    ('nba', {'period': 3, 'displayClock': '0:00', 'type': {'name': 'STATUS_END_PERIOD', 'state': 'in'}}, 'End Q3'),
    ('nba', {'period': 6, 'displayClock': '1:10', 'type': {'name': 'STATUS_IN_PROGRESS', 'state': 'in'}}, '2OT 1:10'),
    ('nhl', {'period': 2, 'displayClock': '10:03', 'type': {'name': 'STATUS_IN_PROGRESS', 'state': 'in'}}, 'P2 10:03'),
    ('nhl', {'period': 4, 'displayClock': '2:11', 'type': {'name': 'STATUS_IN_PROGRESS', 'state': 'in'}}, 'OT 2:11'),
    ('nhl', {'period': 5, 'displayClock': '0:00', 'type': {'name': 'STATUS_IN_PROGRESS', 'state': 'in', 'shortDetail': 'SO'}}, 'SO'),
    ('nhl', {'period': 4, 'type': {'name': 'STATUS_FINAL', 'state': 'post', 'shortDetail': 'Final/OT'}}, 'Final/OT'),
])
def test_the_clock_reads_as_a_fan_would_say_it(sport, status, want):
    got = node(pure() + f'console.log(JSON.stringify(scoresClock({json.dumps(sport)}, {json.dumps(status)})));')
    assert got == want


# ---------- matching a page's game ----------

@pytest.mark.parametrize('sport,page,espn', [
    ('nfl', 'LA@WAS', 'LAR@WSH'),
    ('nhl', 'TBL@LAK', 'TB@LA'),
    ('nhl', 'NJD@SJS', 'NJ@SJ'),
    ('nhl', 'UTA@BOS', 'UTAH@BOS'),
    ('nba', 'GS@NY', 'GS@NY'),
])
def test_a_pages_team_codes_find_espns(sport, page, espn):
    seen = {sport: {espn: {'as': 1, 'hs': 2}}}
    got = node(pure() + f'console.log(JSON.stringify(scoresFind({json.dumps(seen)}, {json.dumps(sport)}, {json.dumps(page)})));')
    assert got == {'as': 1, 'hs': 2}


def test_espns_id_wins_over_the_teams():
    seen = {'nba': {'#9': {'as': 5, 'hs': 6}, 'BOS@NY': {'as': 1, 'hs': 2}}}
    got = node(pure() + f'console.log(JSON.stringify([scoresFind({json.dumps(seen)}, "nba", "BOS@NY", "9"),'
                        f' scoresFind({json.dumps(seen)}, "nba", "BOS@NY", "8"), scoresFind({json.dumps(seen)}, "nba", "MIA@NY")]));')
    assert got == [{'as': 5, 'hs': 6}, {'as': 1, 'hs': 2}, None]


# ---------- when ESPN is asked ----------

HOUR = 3600 * 1000


def due(start, entry, now):
    return node(pure() + f'console.log(JSON.stringify(scoresDue({start}, {json.dumps(entry)}, {now})));')


def test_a_game_is_asked_about_from_ten_minutes_before_until_twelve_hours_after():
    s = 1_800_000_000_000
    assert due(s, None, s - 11 * 60 * 1000) is False
    assert due(s, None, s - 9 * 60 * 1000) is True
    assert due(s, None, s + 3 * HOUR) is True
    assert due(s, None, s + 12 * HOUR - 1) is True
    assert due(s, None, s + 12 * HOUR) is False


def test_a_game_espn_has_called_final_is_not_asked_about_again():
    s = 1_800_000_000_000
    assert due(s, {'state': 'in'}, s + HOUR) is True
    assert due(s, {'state': 'post'}, s + HOUR) is False


def test_one_scoreboard_per_sport_and_eastern_day():
    s = 1_792_000_000_000  # 2026-10-14 15:46 UTC
    games = [{'sport': 'nhl', 'start': s}, {'sport': 'nhl', 'start': s + HOUR},
             {'sport': 'nba', 'start': s + HOUR}, {'sport': 'nhl', 'start': s + 30 * HOUR}]
    got = node(pure() + f'console.log(JSON.stringify(scoresWant({json.dumps(games)}, {s + 2 * HOUR})));')
    assert got == [{'url': 'https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard?dates=20261014', 'sport': 'nhl'},
                   {'url': 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=20261014', 'sport': 'nba'}]


def test_a_late_game_is_on_its_eastern_day_not_utcs():
    # 10:30 PM Eastern on 2026-10-15 is 02:30 UTC on the 16th.
    assert node(pure() + 'console.log(JSON.stringify(scoresDay(Date.parse("2026-10-16T02:30:00Z"))));') == '20261015'


# ---------- what the slots say ----------

def view(key, entry, now):
    return node(pure() + f'console.log(JSON.stringify(scoresView({json.dumps(key)}, {json.dumps(entry)}, {now}, d => "8:41 PM")));')


def test_a_live_game_says_live_with_the_pages_own_codes():
    got = view('LA@WAS', {'as': 17, 'hs': 14, 'state': 'in', 'clock': 'Q3 4:12', 'at': 0}, 1000)
    assert got == {'clock': 'Q3 4:12', 'game': 'LA 17 @ WAS 14', 'line': 'Live: LA 17, WAS 14 · Q3 4:12'}


def test_an_old_reading_says_when_it_was_taken():
    got = view('BOS@NY', {'as': 80, 'hs': 77, 'state': 'in', 'clock': 'Q4 2:00', 'at': 0}, 3 * 60 * 1000 + 1)
    assert got['line'] == 'Live: BOS 80, NY 77 · Q4 2:00 · as of 8:41 PM'


def test_espns_final_says_the_picks_wait_for_the_next_update():
    got = view('TBL@LAK', {'as': 3, 'hs': 2, 'state': 'post', 'clock': 'Final/OT', 'at': 0}, 10 ** 9)
    assert got['line'] == 'Final: TBL 3, LAK 2 (OT) · picks are graded at the next update'
    assert got['clock'] == 'Final/OT'
    plain = view('BOS@NY', {'as': 99, 'hs': 101, 'state': 'post', 'clock': 'Final', 'at': 0}, 10)
    assert plain['line'] == 'Final: BOS 99, NY 101 · picks are graded at the next update'


# ---------- the page ----------

def test_the_slots_are_filled_with_text_never_html():
    assert 'slot.textContent = text' in SCORES
    assert 'innerHTML' not in SCORES


def test_nothing_is_asked_while_the_tab_is_hidden_and_a_failure_is_swallowed():
    tick = SCORES[SCORES.index('async function tick'):]
    assert 'if(busy || document.hidden) return;' in tick
    assert ".catch(() => {})" in tick, 'a refused request must not become a page error'
    assert "credentials: 'omit'" in tick
    assert "visibilitychange" in SCORES


def test_a_page_with_nothing_on_waits_for_the_next_start():
    tick = SCORES[SCORES.index('async function tick'):]
    assert 'if(!want.length){' in tick and 'later(next - now)' in tick
    assert 'later(SCORES_EVERY_MS)' in tick and 'SCORES_EVERY_MS = 60 * 1000' in SCORES


def test_until_espn_answers_the_row_and_card_read_as_before():
    rules = re.sub(r'\s+', '', CSS)
    assert '.score-on{display:none;}' in rules
    assert '[data-score-live].score-off{display:none;}' in rules
    assert '[data-score-live].score-on{display:inline;}' in rules


@pytest.mark.parametrize('name,src', [('nhl', NHL), ('nba', NBA)], ids=['nhl', 'nba'])
def test_a_day_board_marks_a_game_not_yet_final(name, src):
    mark = function_source(src, 'scoreMark')
    got = node(mark + 'console.log(JSON.stringify([' + ','.join(
        f'scoreMark({json.dumps(g)})' for g in (
            {'id': '7', 'away': 'BOS', 'home': 'NYR', 'start': '2026-10-15T23:00:00Z', 'status': 'in_progress'},
            {'id': '7', 'away': 'BOS', 'home': 'NYR', 'start': '2026-10-15T23:00:00Z', 'status': 'scheduled'},
            {'id': '7', 'away': 'BOS', 'home': 'NYR', 'start': '2026-10-15T23:00:00Z', 'status': 'final'},
            {'id': '7', 'away': 'BOS', 'home': 'NYR', 'start': '2026-10-15T23:00:00Z', 'status': 'postponed'},
            {'id': '7', 'away': 'BOS', 'home': 'NYR', 'start': None, 'status': 'scheduled'})) + ']));')
    live = f' data-score-sport="{name}" data-score-key="BOS@NYR" data-score-start="2026-10-15T23:00:00Z"'
    if name == 'nba':
        live += ' data-score-id="7"'
    assert got == [live, live, '', '', '']


@pytest.mark.parametrize('name,src', [('nhl', NHL), ('nba', NBA)], ids=['nhl', 'nba'])
def test_a_day_boards_row_and_cards_carry_the_mark_and_the_slots(name, src):
    row = function_source(src, 'rowHtml')
    assert 'aria-controls="${id}"${scoreMark(g)}>' in row
    assert f'<span class="{name}-row-time"><span class="score-off">${{rowTime(g, p)}}</span>${{scoreSlot(\'clock\')}}</span>' in row
    assert f'<span class="{name}-row-game"><span class="score-off">${{rowGame(g)}}</span>${{scoreSlot(\'game\')}}</span>' in row
    for card in (function_source(src, 'pickedCard'), function_source(src, 'waitingCard')):
        assert '${scoreMark(g)}>' in card
        assert f'<div class="{name}-card-status score-on" data-score-slot="line"></div>' in card
        assert f'<div class="{name}-card-status score-off">' in card


def test_the_nfl_board_marks_a_game_not_yet_final_or_graded():
    js = (function_source(APP, 'escapeHtml') + 'const ET_PARTS = ' + APP.split('const ET_PARTS = ', 1)[1].split(';\n', 1)[0] + ';\n'
          + function_source(APP, 'etInstant') + function_source(APP, 'scoreMark'))
    games = [{'away': 'LA', 'home': 'WAS', 'gameday': '2026-10-18', 'gametime_et': '13:00', 'status': 'started'},
             {'away': 'LA', 'home': 'WAS', 'gameday': '2026-10-18', 'gametime_et': '13:00', 'status': 'upcoming'},
             {'away': 'LA', 'home': 'WAS', 'gameday': '2026-10-18', 'gametime_et': '13:00', 'status': 'final'},
             {'away': 'LA', 'home': 'WAS', 'gameday': '2026-10-18', 'gametime_et': '13:00', 'status': 'started', 'graded': True},
             {'away': 'LA', 'home': 'WAS', 'gameday': '2026-10-18', 'gametime_et': '13:00', 'status': 'cancelled'}]
    got = node(js + 'console.log(JSON.stringify([' + ','.join(f'scoreMark({json.dumps(g)})' for g in games) + ']));')
    live = ' data-score-sport="nfl" data-score-key="LA@WAS" data-score-start="2026-10-18T17:00:00.000Z"'
    assert got == [live, live, '', '', '']


def test_the_nfl_row_and_card_carry_the_mark_and_the_slots():
    row = function_source(APP, 'phoneRowHtml')
    assert 'aria-controls="card-${n}"${scoreMark(g)}>' in row
    assert "<span class=\"score-off\">${time}</span>${scoreSlot('clock')}" in row
    assert "<span class=\"score-off\">${escapeHtml(g.away)} @ ${escapeHtml(g.home)}</span>${scoreSlot('game')}" in row
    assert "<div class=\"game-card ${g.flag?'has-flag':''}\"${scoreMark(g)}>" in APP
    assert '<div class="card-status score-on" data-score-slot="line"></div>' in APP
    assert '<div class="card-status score-off">${statusLine}</div>' in APP


# ---------- the build ----------

PAGE = '<html><body><script>const m = `data-score-key="${k}"`;</script></body></html>'


def test_the_build_puts_the_script_on_a_page_that_marks_games(tmp_path):
    page = tmp_path / 'p.html'
    page.write_text(PAGE, encoding='utf-8')
    block = build.scores_block()
    assert build.inject_scores(page, block)
    assert build.inject_scores(page, block), 'a second build replaces, not adds'
    html = page.read_text(encoding='utf-8')
    assert html.count('<script data-site-scores>') == 1
    assert html.index('data-site-scores') < html.index('</body>')
    assert 'function scoresRead' in html


def test_a_page_that_marks_nothing_gets_nothing(tmp_path):
    page = tmp_path / 'home.html'
    page.write_text('<html><body><p>home</p></body></html>', encoding='utf-8')
    assert not build.inject_scores(page, build.scores_block())
    assert 'data-site-scores' not in page.read_text(encoding='utf-8')
    assert not build.inject_scores(tmp_path / 'missing.html', build.scores_block())


def test_the_build_tries_the_three_sport_pages_only(tmp_path):
    for s in ('nfl', 'nhl', 'nba'):
        (tmp_path / s).mkdir()
        (tmp_path / s / 'index.html').write_text(PAGE, encoding='utf-8')
    (tmp_path / 'index.html').write_text(PAGE, encoding='utf-8')
    assert build.add_scores(tmp_path) == ['nfl/index.html', 'nhl/index.html', 'nba/index.html']
    assert 'data-site-scores' not in (tmp_path / 'index.html').read_text(encoding='utf-8')
    assert 'add_scores(out)' in inspect.getsource(build.build_site)
