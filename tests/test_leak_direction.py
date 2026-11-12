"""Stage 95 item 33 (audit 7, M4): the leak-direction line. The drift check looks
only for live Model A worse than its backtest; better than it by more than its
seasons differ is said in the run log, the drift file and on the page, beside
the count of saved picks whose own records show a leak.

Run with: pytest tests/test_leak_direction.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.core import day_drift
from src.sports.nba import drift as nba_drift
from src.sports.nhl import drift as nhl_drift
from tests.optional import in_ci
from tests.page_script import day_script

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')


def test_better_by_more_than_the_spread_is_said_from_the_first_look_on():
    say = day_drift.leak_direction(0.60, 100, 0.65, 0.03, 100, 0)
    assert say == {'better_than_spread': True, 'margin': 0.05, 'spread_range': 0.03, 'leaked_picks': 0}
    assert day_drift.leak_direction(0.63, 100, 0.65, 0.03, 100, 0)['better_than_spread'] is False, 'within the spread'
    assert day_drift.leak_direction(0.60, 99, 0.65, 0.03, 100, 0)['better_than_spread'] is False, 'before a look'
    assert day_drift.leak_direction(0.70, 100, 0.65, 0.03, 100, 0)['better_than_spread'] is False, 'worse is drift'
    assert day_drift.leak_direction(None, 0, 0.65, 0.03, 100, 0)['margin'] is None


def test_the_run_log_says_each_direction_once_and_nothing_otherwise():
    assert day_drift.leak_lines(day_drift.leak_direction(0.63, 150, 0.65, 0.03, 100, 0)) == []
    lines = day_drift.leak_lines(day_drift.leak_direction(0.60, 150, 0.65, 0.03, 100, 3))
    assert len(lines) == 2 and lines[0].startswith('LEAK CHECK: live log loss is 0.0500 better')
    assert '3 saved pick(s) could have seen their result' in lines[1]


def test_saved_picks_are_counted_by_their_own_records(tmp_path):
    picks = [{'game_id': '1', 'slate': '2026-11-01', 'training_through': '2026-10-31'},
             {'game_id': '2', 'slate': '2026-11-01', 'training_through': '2026-11-01'},
             {'game_id': '3', 'start_utc': '2026-11-01T23:00:00Z', 'saved_utc': '2026-11-01T23:05:00Z'}]
    for p in picks:
        (tmp_path / f"{p['game_id']}.json").write_text(json.dumps(p), encoding='utf-8')
    assert day_drift.leaked_picks(tmp_path) == 2
    assert day_drift.leaked_picks(tmp_path / 'none') == 0


@pytest.mark.parametrize('drift, stage', [(nhl_drift, 'stage56'), (nba_drift, 'stage61')])
def test_each_sport_reads_its_own_backtest_spread(drift, stage):
    sport = drift.__name__.split('.')[-2]
    spread = json.loads((ROOT / f'experiments/{sport}/{stage}/results/model_a_by_season.json').read_text(encoding='utf-8'))
    assert drift.spread_range() == spread['spread']['range'] > 0


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_each_daily_run_writes_and_prints_it(sport):
    src = (ROOT / 'src' / 'sports' / sport / 'daily.py').read_text(encoding='utf-8')
    assert "'leak': leak" in src
    assert 'for line in drift.leak_lines(leak):\n            print(line)' in src.replace('\r\n', '\n')
    assert 'drift.leaked_picks(folder)' in src


def run(sport, call):
    js = day_script(sport)
    fn = ''.join(re.search(rf'function {n}\(.*?\n\}}\n', js, re.S).group(0) for n in ('leakNote', 'driftStatus'))
    return subprocess.run([NODE, '-e', fn + f'process.stdout.write({call});'], capture_output=True, text=True,
                          encoding='utf-8', check=True).stdout


@pytest.mark.skipif(NODE is None and not in_ci(), reason='node not installed')
@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_the_page_says_it_beside_the_drift_check(sport):
    rule = json.loads((ROOT / 'data' / sport / 'drift_baseline.json').read_text(encoding='utf-8'))
    d = {'games': 240, 'mean_log_loss': 0.6477, 'baseline': 0.6753, 'flagged': False, 'next_look': 400,
         'looks': [{'games': 200, 'lower_bound': 0.62, 'flagged': False}],
         'leak': {'better_than_spread': True, 'margin': 0.0276, 'spread_range': 0.0257, 'leaked_picks': 29}}
    out = run(sport, f'driftStatus({json.dumps(d)}, {json.dumps(rule)})')
    assert out.startswith('Not flagged.')
    assert 'Live log loss is 0.0276 below it, against a spread of 0.0257 between its seasons.' in out
    assert '29 saved picks could have seen their result' in out
    quiet = dict(d, leak={'better_than_spread': False, 'margin': 0.01, 'spread_range': 0.0257, 'leaked_picks': 0})
    assert 'leak' not in run(sport, f'driftStatus({json.dumps(quiet)}, {json.dumps(rule)})')
