"""Stage 95 item 37 (audit 7, M12): under 20 game days, the forward test's
intervals carry the interval that resamples single games beside the one that
resamples whole days, and the pages print it with a note.

A day-block bootstrap over a dozen days has a dozen blocks to draw from: its
interval is rough, and on its own a reader cannot tell. The day-block interval
stays the registered one; the game-level one is printed under it, narrower
because it ignores how one day's games move together, until 20 days are in.

Run with: pytest tests/test_forward_few_days.py -v
"""
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from src.core import forward_test as ft
from tests.js_source import function_source

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')


def series(days, per_day=6, seed=1):
    rng = np.random.default_rng(seed)
    diff = rng.normal(-0.01, 0.2, days * per_day)
    return diff, np.repeat(np.arange(days), per_day)


def test_under_twenty_days_the_game_level_interval_is_reported_beside_it():
    diff, days = series(12)
    got = ft.interval(diff, days, seed=7)
    few = got['few_days']
    assert few['min_days'] == ft.MIN_DAY_BLOCKS == 20
    rng = np.random.default_rng(7)
    rng.integers(0, 12, size=(ft.N_RESAMPLES, 12))  # the day blocks, drawn first
    boot = diff[rng.integers(0, len(diff), size=(ft.N_RESAMPLES, len(diff)))].mean(axis=1)
    tail = (1 - ft.LEVEL) / 2
    assert (few['game_low'], few['game_high']) == tuple(float(q) for q in np.quantile(boot, [tail, 1 - tail]))
    assert few['game_low'] < got['diff'] < few['game_high']


def test_the_day_block_interval_is_unchanged_by_it():
    """The game draws come after the day blocks', so the registered interval
    is the same as before this was added."""
    diff, days = series(12)
    got = ft.interval(diff, days, seed=7)
    frame_sums = np.array([diff[days == d].sum() for d in range(12)])
    counts = np.full(12, 6.0)
    draws = np.random.default_rng(7).integers(0, 12, size=(ft.N_RESAMPLES, 12))
    boot = frame_sums[draws].sum(axis=1) / counts[draws].sum(axis=1)
    tail = (1 - ft.LEVEL) / 2
    assert (got['low'], got['high']) == tuple(float(q) for q in np.quantile(boot, [tail, 1 - tail]))


def test_from_twenty_days_there_is_none():
    diff, days = series(20)
    assert 'few_days' not in ft.interval(diff, days, seed=7)


@pytest.mark.skipif(NODE is None, reason='node not installed')
@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_the_page_prints_it_and_says_why_only_while_it_applies(sport):
    src = (ROOT / 'src' / 'sports' / sport / 'pages' / f'{sport}.js').read_text(encoding='utf-8')
    js = function_source(src, 'forwardHtml') + "function calibrationTable(){ return ''; }\n"

    def render(days):
        diff, d = series(days)
        c = ft.interval(diff, d, seed=7)
        f = {'graded_picks': len(diff), 'through': '2026-11-02', 'registered': 'r.json',
             'scores': {}, 'comparisons': {'model_a_minus_base_rate': c},
             'interval_rule': {'level': ft.LEVEL, 'resamples': ft.N_RESAMPLES}}
        code = js + f'process.stdout.write(forwardHtml({json.dumps(f)}, {json.dumps(sport)}));'
        return subprocess.run([NODE, '-e', code], capture_output=True, text=True, check=True).stdout

    few = render(12)
    assert '<span class="forward-games">games [' in few
    assert 'Only 12 game days are in so far, under the 20' in few
    assert 'The day-block interval is the one the registration uses.' in few
    many = render(25)
    assert 'forward-games' not in many and 'game days are in so far' not in many
