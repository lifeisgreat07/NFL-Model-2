"""The home page's day card says how tonight is going (Stage 77 item 12, the 2026-10-13 UI/UX audit's copy fix 1).

It said "16 games tonight / First puck drop 6:00 PM" all evening, after the
first game had finished. It now says "16 games tonight · 11 final, 5 to
play" and, once the first game has started, "Next puck drop 11:00 PM".
dayStatus runs here under node with the clock and the time zone fixed.

Run with: pytest tests/test_home_tonight.py -v
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
NODE = shutil.which('node')


def day_status(games, now):
    """dayStatus(f, 'puck drop') for games of (start UTC, status), at `now` (UTC), in New York."""
    if not NODE:
        pytest.skip('node not available')
    helpers = ''.join(re.search(rf'^function {n}\(.*$', JS, re.M).group(0) + '\n' for n in ('dayKey', 'clock', 'weekday', 'when', 'record'))
    fn = re.search(r'^function dayStatus\(f, start\)\{.*?\n\}\n', JS, re.S | re.M)
    assert fn, 'dayStatus is not findable -- re-anchor this guard'
    # The puck drop is never a placeholder; only the NBA's tip-off is (Stage 77 item 33).
    # The best pick tonight reads the slate (Stage 80 item 52); none here.
    best = ("const HOME = {slate: []};\n" + re.search(r'^const START_SPORT = .*$', JS, re.M).group(0) + '\n' + re.search(r'^function slateOf\(.*$', JS, re.M).group(0) + '\n'
            + re.search(r'function bestPick\(.*?\n\}\n', JS, re.S).group(0))
    code = (f'const NOW = Date.parse({json.dumps(now)}); const HOUR = 3600 * 1000; const PLACEHOLDER_TIMES = {{}};\n' + helpers + best + fn.group(0)
            + 'console.log(JSON.stringify(dayStatus(%s, "puck drop")));' % json.dumps({'games': games, 'record': {'label': 'Picks'}}))
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8', env={**os.environ, 'TZ': 'America/New_York'})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


# Tuesday 2026-10-13: 7:00 PM, 7:30 PM and 10:00 PM Eastern.
TONIGHT = ['2026-10-13T23:00:00Z', '2026-10-13T23:30:00Z', '2026-10-14T02:00:00Z']


def test_before_the_first_game_it_names_the_first():
    out = day_status([[t, 'scheduled'] for t in TONIGHT], '2026-10-13T20:00:00Z')
    assert out['status']['text'] == '3 games tonight' and out['rows'][1] == ['First puck drop', '7:00 PM']


def test_once_games_finish_it_counts_them_and_names_the_next_start():
    games = [[TONIGHT[0], 'final'], [TONIGHT[1], 'in_progress'], [TONIGHT[2], 'scheduled']]
    out = day_status(games, '2026-10-14T01:30:00Z')
    assert out['status']['text'] == '3 games tonight · 1 final, 2 to play'
    assert out['rows'][1] == ['Next puck drop', '10:00 PM']


def test_when_every_game_is_over_it_says_so():
    out = day_status([[t, 'final'] for t in TONIGHT], '2026-10-14T03:30:00Z')   # 11:30 PM Eastern
    assert out['status']['text'] == '3 games tonight · all final' and out['rows'][1] == ['First puck drop', '7:00 PM']
