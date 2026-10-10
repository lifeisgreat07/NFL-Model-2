"""The NHL board a day at a time (Stage 64).

Mark chose it from the rendered "NHL Day Board Options" (2026-10-09):
option A's strip of the week's seven days, opening on today, with option B's
compact rows (time, game, pick, result) that open on a tap to the full card
(both models, the market, the lock time and the goalies). The NFL keeps its
week view: it plays by the week.

The row and summary functions in `src/sports/nhl/pages/nhl.js` are executed
here in node over each state. `tests/browser/check_nhl_day.py` drives the
built sample page in Chromium at phone and desktop widths in both themes
(`.github/workflows/browser-checks.yml`).

Run with: pytest tests/test_nhl_day_board.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.core.template_parts import JOINED_TEMPLATE

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / 'src' / 'sports' / 'nhl' / 'pages'
JS = PAGES / 'nhl.js'
NODE = shutil.which('node')

FUNCTIONS = ('dayDate', 'dayIso', 'weekDays', 'defaultDay', 'lockRunFor', 'winnerOf', 'rowResult', 'rowPick',
             'rowTime', 'rowGame', 'daySummary')


def source():
    return JS.read_text(encoding='utf-8')


def function_source(src, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def const_line(src, name):
    m = re.search(r'^const ' + name + r' = .*$', src, re.M)
    assert m, f'const {name} is not findable'
    return m.group(0) + '\n'


def run_node(body):
    if not NODE:
        pytest.skip('node not available')
    src = source()
    js = ("const ET = 'America/New_York';\n"
          + ''.join(const_line(src, c) for c in ('LOCK_RUN_HOURS_UTC', 'LOCK_SLACK_MS', 'FMT_HOUR'))
          + ''.join(function_source(src, n) for n in FUNCTIONS) + body)
    r = subprocess.run([NODE, '-e', js], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


GAME = {'id': '1', 'day': '2026-10-09', 'home': 'DAL', 'away': 'COL', 'status': 'final', 'hs': 2, 'as': 3, 'lp': 'REG',
        'start': '2026-10-09T23:30:00Z'}
UPCOMING = dict(GAME, status='scheduled', hs=None, **{'as': None})
NOW = '2026-10-09T16:00:00Z'


@pytest.fixture(scope='module')
def rows():
    cases = {
        'right': (GAME, {'a': 0.4, 'b': 0.42, 'pick': 'COL', 'result': 'correct'}),
        'wrong': (GAME, {'a': 0.6, 'b': 0.58, 'pick': 'DAL', 'result': 'wrong'}),
        'final_ungraded': (GAME, {'a': 0.6, 'b': None, 'pick': 'DAL', 'result': 'pending'}),
        'locked': (UPCOMING, {'a': 0.6, 'b': 0.55, 'pick': 'DAL', 'result': 'pending'}),
        'open': (UPCOMING, None),
        'late': (dict(UPCOMING, start='2026-10-09T17:30:00Z'), None),
        'no_pick_final': (GAME, None),
        'postponed': (dict(UPCOMING, status='postponed'), None),
        'ot': (dict(GAME, lp='OT'), None),
        'shutout': (dict(GAME, hs=0, **{'as': 1}), None),
    }
    return run_node(f'const N=Date.parse({json.dumps(NOW)});const C={json.dumps(cases)};const o={{}};'
                    'for(const k in C){const [g,p]=C[k];'
                    'o[k]={r:rowResult(g,p,N),pick:rowPick(g,p),time:rowTime(g),game:rowGame(g)};}'
                    'process.stdout.write(JSON.stringify(o));')


def test_a_graded_pick_says_correct_or_missed(rows):
    """The words the cards and the Accuracy table use (Stage 68 item 18b)."""
    assert rows['right']['r'] == {'text': 'Correct', 'cls': 'right'}
    assert rows['wrong']['r'] == {'text': 'Missed', 'cls': 'wrong'}


def test_a_saved_pick_not_yet_graded_says_locked_or_grading(rows):
    assert rows['locked']['r'] == {'text': 'Locked', 'cls': 'locked'}
    assert rows['final_ungraded']['r'] == {'text': 'Grading', 'cls': 'locked'}


def test_an_unsaved_game_says_when_it_locks_or_that_it_is_late(rows):
    assert rows['open']['r'] == {'text': 'Locks 5 PM', 'cls': 'open'}
    assert rows['late']['r'] == {'text': 'Late', 'cls': 'open'}


def test_a_game_without_a_pick_says_so(rows):
    assert rows['no_pick_final']['r']['text'] == 'No pick'
    assert rows['postponed']['r']['text'] == 'Postponed'


def test_the_pick_column_is_the_saved_side_with_its_chance(rows):
    assert rows['right']['pick'] == 'COL 58%', 'Model B leads, and COL is the away side: 1 - 0.42'
    assert rows['final_ungraded']['pick'] == 'DAL 60%', 'no Model B: Model A leads'
    assert rows['open']['pick'] == '—'


def test_the_time_column_says_final_and_how_it_ended(rows):
    assert rows['right']['time'] == 'Final' and rows['ot']['time'] == 'Final/OT'
    assert rows['open']['time'] == '7:30 PM'


def test_the_game_column_bolds_the_winner_with_the_score(rows):
    assert rows['right']['game'] == '<b>COL 3</b> <span class="at-symbol">@</span> DAL 2'
    assert rows['shutout']['game'] == '<b>COL 1</b> <span class="at-symbol">@</span> DAL 0'
    assert rows['open']['game'] == 'COL <span class="at-symbol">@</span> DAL'


@pytest.fixture(scope='module')
def days():
    games = [dict(GAME, id='a', day='2026-10-06'), dict(GAME, id='b', day='2026-10-08')]
    picks = {'a': {'result': 'correct'}, 'b': {'result': 'wrong'}, 'c': {'result': 'pending'}}
    return run_node(
        f'const G={json.dumps(games)};const P={json.dumps(picks)};'
        'process.stdout.write(JSON.stringify({'
        'week: weekDays("2026-10-05"),'
        'today: defaultDay("2026-10-05", G, "2026-10-09"),'
        'other: defaultDay("2026-10-05", G, "2026-10-20"),'
        's3: daySummary([{id:"a"},{id:"b"},{id:"x"}], P),'
        's_locked: daySummary([{id:"c"},{id:"x"}], P),'
        's_none: daySummary([{id:"x"}], P),'
        's_empty: daySummary([], P)}));')


def test_the_strip_is_the_weeks_seven_days(days):
    assert days['week'] == ['2026-10-05', '2026-10-06', '2026-10-07', '2026-10-08', '2026-10-09', '2026-10-10',
                            '2026-10-11']


def test_the_board_opens_on_today_and_otherwise_on_the_first_day_with_games(days):
    assert days['today'] == '2026-10-09'
    assert days['other'] == '2026-10-06'


def test_the_summary_counts_the_days_right_picks_as_mark_wrote_it(days):
    assert days['s3'] == '3 games, 1 of 2 right so far'
    assert days['s_locked'] == '2 games, 1 locked'
    assert days['s_none'] == '1 game'
    assert days['s_empty'] == 'No games this day.'


def test_a_row_opens_its_card_and_says_so():
    src = source()
    row = function_source(src, 'rowHtml')
    assert 'aria-expanded="false" aria-controls="${id}"' in row
    assert '<div class="nhl-row-detail" id="${id}" hidden>${p ? pickedCard(g, p) : waitingCard(g)}</div>' in row
    board = function_source(src, 'renderBoard')
    assert "btn.setAttribute('aria-expanded', String(open));" in board
    assert ".hidden = !open;" in board


def test_the_day_strip_marks_the_chosen_day_and_today():
    board = function_source(source(), 'renderBoard')
    assert 'aria-pressed="${d === currentDay}"' in board
    assert 'aria-current="date"' in board


def test_the_nfl_keeps_its_week_view():
    nfl = JOINED_TEMPLATE.read_text(encoding='utf-8')
    assert 'nhl-row' not in nfl and 'nhl-day-strip' not in nfl
    assert 'id="week-step-label"' in nfl


def test_the_board_is_named_for_what_it_shows():
    body = (PAGES / 'body.html').read_text(encoding='utf-8')
    assert '<h2>Day Board</h2>' in body and 'Week Board' not in body
