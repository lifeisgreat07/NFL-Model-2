"""The NBA's day board (Stage 65) says what happened, what is locked, where
each price came from, and who was out.

The board's functions in `src/sports/nba/pages/nba.js` are executed here in
node over each state rather than read. `lockRunFor` restates the rule in
`src/sports/nba/lock.py`, with its 21:30 run, so the two are run side by
side over four days of start times and must agree on every one. The market
line is checked for each source the registration names: ESPN, Kalshi as
the fallback, and none, which must say "no price".

Run with: pytest tests/test_nba_board.py -v
"""
import json
import re
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from src.sports.nba import lock

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js'
# escapeHtml is shared with the NHL and included ahead of nba.js (Stage 68 item 24).
ESCAPE_JS = ROOT / 'src' / 'core' / 'escape.js'
NODE = shutil.which('node')


def source():
    return ESCAPE_JS.read_text(encoding='utf-8') + JS.read_text(encoding='utf-8')


def function_source(src, name):
    m = re.search(r'^function ' + name + r'\(.*?\n\}\n', src, re.S | re.M)
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
          + ''.join(const_line(src, n) for n in ('LOCK_RUNS_UTC', 'LOCK_SLACK_MS', 'FMT_WHEN', 'FMT_HOUR'))
          + 'const EVEN_BAND = 2;\n'
          + ''.join(function_source(src, n) for n in
                    ('escapeHtml', 'pct', 'lockRunFor', 'whenEt', 'lockNote', 'modelSide', 'winnerOf', 'resultLine',
                     'lockedTag', 'side', 'sideText', 'american', 'marketText', 'availText', 'rowPick', 'rowResult'))
          + body)
    r = subprocess.run([NODE, '-e', js], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


# ---------------------------------------------------------------- the lock time

STARTS = [datetime(2026, 10, 20, tzinfo=UTC) + timedelta(minutes=15 * i) for i in range(4 * 24 * 4)]


def python_lock_run(start):
    """The run at which lock.GameLock first puts the game in its lock list."""
    slate = pd.DataFrame([{'game_id': 'g', 'status': 'scheduled', 'start_utc': pd.Timestamp(start),
                           'slate': start.strftime('%Y-%m-%d')}])
    day = start.replace(hour=0, minute=0) - timedelta(days=3)
    runs = sorted(day + timedelta(days=d, hours=h, minutes=m) for d in range(5) for (_, h, m) in lock.RUNS_UTC[:2])
    for run in runs:
        if run >= start:
            break
        if 'g' in lock.GameLock().decide(slate, run).lock:
            return run
    return None


def test_the_page_uses_the_lock_rules_own_runs_and_slack():
    src = source()
    runs = json.loads(re.search(r'const LOCK_RUNS_UTC = (\[.*?\]\]);', src).group(1))
    assert sorted({(h, m) for _, h, m in lock.RUNS_UTC}) == [tuple(r) for r in runs]
    assert {d for d, _, _ in lock.RUNS_UTC} == set(range(7)), 'the page assumes a run every day'
    product = 1
    for factor in re.search(r'const LOCK_SLACK_MS = ([\d *]+);', src).group(1).split('*'):
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


# ---------------------------------------------------------------- the market line, by source

G = {'home': 'ORL', 'away': 'ATL', 'status': 'scheduled', 'hs': None, 'as': None, 'start': '2026-10-21T23:00:00Z'}
PICKS = {
    'espn': {'a': 0.55, 'b': 0.53, 'pick': 'ORL', 'source': 'espn',
             'market': {'book': 'DraftKings', 'hp': -130, 'ap': 110, 'prob': 0.5427}},
    'kalshi': {'a': 0.55, 'b': 0.53, 'pick': 'ORL', 'source': 'kalshi',
               'market': {'book': 'Kalshi', 'hp': 0.57, 'ap': 0.43, 'prob': 0.57}},
    'none': {'a': 0.44, 'b': None, 'pick': 'ATL', 'source': None,
             'why': 'ESPN has no pre-game price; Kalshi spread 0.64 is wider than 0.05'},
}


@pytest.fixture(scope='module')
def lines():
    return run_node(f'const G={json.dumps(G)};const P={json.dumps(PICKS)};const o={{}};'
                    'for(const k in P){ o[k]=marketText(G, P[k]); o["row_"+k]=rowPick(G, P[k]); }'
                    'process.stdout.write(JSON.stringify(o));')


def test_an_espn_price_names_the_book_and_espn(lines):
    assert lines['espn'].startswith('Market (DraftKings via ESPN): ATL <b>+110</b> · ORL <b>−130</b>')
    assert 'ORL 54%' in lines['espn']


def test_a_kalshi_price_says_it_is_the_fallback(lines):
    assert lines['kalshi'].startswith('Market (Kalshi, the fallback: ESPN had no price)')
    assert 'ORL 57%' in lines['kalshi']


def test_no_price_is_said_with_its_reason_and_model_a_makes_the_pick(lines):
    assert lines['none'] == ('Market: <b>no price</b> (ESPN has no pre-game price; Kalshi spread 0.64 is wider '
                             'than 0.05), so Model A made the pick')
    assert lines['row_none'] == 'ATL 56% <span class="nba-no-price">no price</span>'
    assert lines['row_espn'] == 'ORL 53%'


# ---------------------------------------------------------------- availability

def test_availability_names_who_is_out_and_says_when_the_report_was_not_read():
    got = run_node(
        f'const G={json.dumps(G)};'
        'const read={avail:{read:true, home:0.97, away:0.8835}, out:{home:[], away:["Trae Young", "<i>x</i>"]}};'
        'const unread={avail:{read:false}, out:{home:[], away:[]}};'
        'process.stdout.write(JSON.stringify([availText(G, read), availText(G, unread)]));')
    assert got[0] == ('Expected minutes available: ATL <b>88%</b> (out: Trae Young, &lt;i&gt;x&lt;/i&gt;) · '
                      'ORL <b>97%</b>')
    assert got[1].startswith('Injury report: <b>not read</b>') and 'without availability' in got[1]


# ---------------------------------------------------------------- results and lock notes

def test_a_played_game_names_the_winner_and_each_model():
    g = dict(G, status='final', hs=0, **{'as': 101})
    got = run_node(f'process.stdout.write(JSON.stringify(resultLine({json.dumps(g)}, {json.dumps(PICKS["espn"])})));')
    assert 'Winner <b>ATL</b>' in got and 'Model B ORL, <b>wrong</b>' in got and 'Market ORL, <b>wrong</b>' in got


def test_a_game_not_locked_says_when_it_locks():
    now = '2026-10-21T16:30:00Z'
    games = {'tonight': {'start': '2026-10-21T23:00:00Z', 'status': 'scheduled'},
             'sunday_noon': {'start': '2026-10-25T16:00:00Z', 'status': 'scheduled'},
             'no_start': {'start': None, 'status': 'scheduled'}}
    got = run_node(f'const N=Date.parse({json.dumps(now)});const G={json.dumps(games)};const o={{}};'
                   'for(const k in G) o[k]=lockNote(G[k], N);process.stdout.write(JSON.stringify(o));')
    assert got['tonight'] == 'The pick locks Wed 5:30 PM ET, at the last run before tip-off.'
    assert got['sunday_noon'] == 'The pick locks Sat 5:30 PM ET, at the last run before tip-off.'
    assert got['no_start'] == 'The pick locks at the last run before tip-off (16:00 or 21:30 UTC).'


def test_the_card_uses_these_functions():
    src = source()
    picked = function_source(src, 'pickedCard')
    for call in ('${resultLine(g, p)}', 'lockedTag(g, p)', 'marketText(g, p)', 'availText(g, p)'):
        assert call in picked, call
    assert 'lockNote(g, Date.now())' in function_source(src, 'waitingCard')


def test_an_empty_season_says_the_board_fills_from_the_first_run():
    assert 'The board fills from the first daily run' in function_source(source(), 'renderBoard')
