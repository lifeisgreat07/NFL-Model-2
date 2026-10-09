"""The NHL board says what happened and what is locked (Stage 63).

Mark, 2026-10-09: on the NHL board, every played game shows the pick, the
final score, the winner and whether each model was right; every upcoming
game with a locked pick shows it, marked locked; a game not yet locked says
when its pick will lock.

`src/sports/nhl/pages/nhl.js` does this with small functions: `lockRunFor`
(when the daily run will save a game), `lockNote`, `resultLine` and
`lockedTag`. They are executed here in node over each state rather than read.
`lockRunFor` restates the rule in `src/sports/nhl/lock.py`, so the two are
run side by side over three days of start times and must agree on every one:
a page that promised a lock time the run does not keep would be wrong in
the one place a reader checks it.

Run with: pytest tests/test_nhl_board_states.py -v
"""
import json
import re
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from src.sports.nhl import lock

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js'
NODE = shutil.which('node')


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
          + const_line(src, 'LOCK_RUN_HOURS_UTC') + const_line(src, 'LOCK_SLACK_MS') + const_line(src, 'FMT_WHEN')
          + ''.join(function_source(src, n) for n in
                    ('lockRunFor', 'whenEt', 'lockNote', 'modelSide', 'winnerOf', 'resultLine', 'lockedTag'))
          + body)
    r = subprocess.run([NODE, '-e', js], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


# ---------------------------------------------------------------- the lock time

STARTS = [datetime(2026, 10, 5, tzinfo=UTC) + timedelta(minutes=15 * i) for i in range(4 * 24 * 4)]


def python_lock_run(start):
    """The run at which lock.GameLock first puts the game in its lock list."""
    slate = pd.DataFrame([{'game_id': 'g', 'status': 'scheduled', 'start_utc': pd.Timestamp(start),
                           'slate': start.strftime('%Y-%m-%d')}])
    day = start.replace(hour=0, minute=0) - timedelta(days=3)
    runs = sorted(day + timedelta(days=d, hours=h) for d in range(5) for (_, h, _) in lock.RUNS_UTC[:2])
    for run in runs:
        if run >= start:
            break
        if 'g' in lock.GameLock().decide(slate, run).lock:
            return run
    return None


def test_the_page_uses_the_lock_rules_own_runs_and_slack():
    src = source()
    hours = json.loads(re.search(r'const LOCK_RUN_HOURS_UTC = (\[.*?\]);', src).group(1))
    assert sorted({h for _, h, _ in lock.RUNS_UTC}) == hours
    assert {m for _, _, m in lock.RUNS_UTC} == {0}
    assert {d for d, _, _ in lock.RUNS_UTC} == set(range(7)), 'the page assumes a run every day'
    slack = re.search(r'const LOCK_SLACK_MS = ([\d *]+);', src).group(1)
    product = 1
    for factor in slack.split('*'):
        product *= int(factor)
    assert product == lock.SLACK.total_seconds() * 1000


def test_the_page_and_the_lock_rule_agree_on_every_start():
    starts = [s.strftime('%Y-%m-%dT%H:%M:%SZ') for s in STARTS]
    got = run_node(f'const S={json.dumps(starts)};'
                   'process.stdout.write(JSON.stringify(S.map(s => { const r = lockRunFor(s); '
                   'return r ? r.toISOString().slice(0, 19) + "Z" : null; })));')
    for start, page in zip(STARTS, got):
        expect = python_lock_run(start)
        want = expect.strftime('%Y-%m-%dT%H:%M:%SZ') if expect else None
        assert page == want, f'a game starting {start:%a %H:%M} UTC: the page says {page}, the run locks at {want}'


# ---------------------------------------------------------------- what each card says

G = {'home': 'TBL', 'away': 'PHI', 'status': 'final', 'hs': 4, 'as': 1, 'start': '2026-10-05T23:00:00Z'}
CASES = {
    'home_win': (G, {'a': 0.58, 'b': 0.61, 'market': {'prob': 0.588}}),
    'away_win': (dict(G, hs=1, **{'as': 4}), {'a': 0.58, 'b': 0.61, 'market': {'prob': 0.588}}),
    'a_only': (G, {'a': 0.39, 'b': None}),
    'zero': (dict(G, hs=0, **{'as': 3}), {'a': 0.6, 'b': None}),
    'not_final': (dict(G, status='scheduled', hs=None, **{'as': None}), {'a': 0.6, 'b': 0.6}),
    'even_picks_home': (G, {'a': 0.5, 'b': None}),
}


@pytest.fixture(scope='module')
def results():
    return run_node(f'const C={json.dumps(CASES)};const o={{}};'
                    'for(const k in C) o[k]=resultLine(C[k][0], C[k][1]);process.stdout.write(JSON.stringify(o));')


def test_a_played_game_names_the_winner_and_each_model_right_or_wrong(results):
    line = results['home_win']
    assert 'Winner <b>TBL</b>' in line
    for part in ('Model B TBL, <b>right</b>', 'Model A TBL, <b>right</b>', 'Market TBL, <b>right</b>'):
        assert part in line, part


def test_a_model_on_the_losing_side_is_wrong(results):
    line = results['away_win']
    assert 'Winner <b>PHI</b>' in line and 'Model B TBL, <b>wrong</b>' in line and 'Model A TBL, <b>wrong</b>' in line


def test_a_model_with_no_chance_is_left_out_not_called_wrong(results):
    line = results['a_only']
    assert 'Model B' not in line and 'Market' not in line and 'Model A PHI, <b>wrong</b>' in line


def test_a_shutout_still_has_a_winner(results):
    """0 is falsy in JavaScript; a truthiness check would drop the line."""
    assert 'Winner <b>PHI</b>' in results['zero']


def test_a_game_not_final_has_no_result_line(results):
    assert results['not_final'] == ''


def test_exactly_even_is_the_home_side_as_the_saved_pick_is(results):
    assert 'Model A TBL, <b>right</b>' in results['even_picks_home']


@pytest.fixture(scope='module')
def notes():
    now = '2026-10-09T16:00:00Z'
    games = {
        'later_today': {'start': '2026-10-09T23:30:00Z', 'status': 'scheduled'},
        'early_sunday': {'start': '2026-10-11T17:00:00Z', 'status': 'scheduled'},
        'overdue': {'start': '2026-10-09T17:30:00Z', 'status': 'scheduled'},
        'no_start': {'start': None, 'status': 'scheduled'},
    }
    tags = {
        'locked': ({'status': 'scheduled'}, {'saved': '2026-10-09T21:00:30Z'}),
        'in_progress': ({'status': 'in_progress'}, {'saved': '2026-10-09T21:00:30Z'}),
        'final': ({'status': 'final'}, {'saved': '2026-10-09T21:00:30Z'}),
        'postponed': ({'status': 'postponed'}, {'saved': '2026-10-09T21:00:30Z'}),
    }
    return run_node(f'const N=Date.parse({json.dumps(now)});const G={json.dumps(games)};const T={json.dumps(tags)};'
                    'const o={};for(const k in G) o[k]=lockNote(G[k], N);'
                    'for(const k in T) o["tag_"+k]=lockedTag(T[k][0], T[k][1]);'
                    'process.stdout.write(JSON.stringify(o));')


def test_a_game_not_locked_says_when_it_locks_in_eastern_time(notes):
    assert notes['later_today'] == 'The pick locks Fri 5:00 PM ET, at the last run before puck drop.'
    assert notes['early_sunday'] == 'The pick locks Sun 10:00 AM ET, at the last run before puck drop.'


def test_a_lock_run_that_passed_without_a_pick_says_so(notes):
    assert notes['overdue'] == 'The pick was due to lock Fri 10:00 AM ET and has not been saved yet.'


def test_a_game_with_no_start_time_names_the_rule(notes):
    assert notes['no_start'] == 'The pick locks at the last run before puck drop (14:00 or 21:00 UTC).'


def test_a_saved_pick_on_a_game_not_final_is_marked_locked(notes):
    assert notes['tag_locked'] == '<span class="graded-tag nhl-locked">Locked Fri 5:00 PM ET</span>'
    assert notes['tag_in_progress'] == notes['tag_locked']
    assert notes['tag_final'] == '' and notes['tag_postponed'] == ''


def test_the_card_uses_these_functions():
    src = source()
    picked = function_source(src, 'pickedCard')
    assert '${resultLine(g, p)}' in picked
    assert "lockedTag(g, p)" in picked
    assert 'lockNote(g, Date.now())' in function_source(src, 'waitingCard')
