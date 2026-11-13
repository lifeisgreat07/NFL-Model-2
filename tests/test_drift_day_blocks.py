"""Stage 95 item 32 (audit 7, M4): the drift bootstrap resamples whole game days.

Run with: pytest tests/test_drift_day_blocks.py -v
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.core import day_drift
from src.sports.nba import daily as nba_daily
from src.sports.nba import drift as nba_drift
from src.sports.nhl import daily as nhl_daily
from src.sports.nhl import drift as nhl_drift

ROOT = Path(__file__).resolve().parents[1]
RULE = {'seed': 7, 'n_resamples': 4000, 'one_sided_level': 0.95}


def test_without_days_it_draws_single_games_as_before():
    losses = [0.5, 0.7, 0.6, 0.9] * 30
    arr = np.asarray(losses)
    idx = np.random.default_rng(7).integers(0, len(arr), size=(4000, len(arr)))
    want = float(np.percentile(arr[idx].mean(axis=1), 5))
    assert day_drift.lower_bound(losses, RULE) == want


def test_with_days_it_draws_whole_days_by_hand():
    losses = [0.2, 0.4, 0.9, 0.5, 0.7, 0.3]
    days = ['a', 'a', 'b', 'c', 'c', 'c']
    sums, counts = np.array([0.6, 0.9, 1.5]), np.array([2.0, 1.0, 3.0])
    idx = np.random.default_rng(7).integers(0, 3, size=(4000, 3))
    want = float(np.percentile(sums[idx].sum(axis=1) / counts[idx].sum(axis=1), 5))
    assert day_drift.lower_bound(losses, RULE, days=days) == want


def test_days_that_move_together_widen_the_interval():
    """Twenty days, each all good or all bad: drawn as single games the interval
    is far narrower than the days' own spread allows."""
    rng = np.random.default_rng(1)
    day_level = rng.choice([0.45, 0.85], size=20)
    losses = [float(x) for x in np.repeat(day_level, 6)]
    days = [f'd{i:02d}' for i in range(20) for _ in range(6)]
    mean = sum(losses) / len(losses)
    assert mean - day_drift.lower_bound(losses, RULE, days=days) > 1.5 * (mean - day_drift.lower_bound(losses, RULE))


def test_a_day_for_every_loss():
    with pytest.raises(ValueError, match='days for'):
        day_drift.lower_bound([0.5, 0.6], RULE, days=['a'])


def test_the_days_kept_are_the_rows_kept():
    rows = [(0.7, 1), (None, 1), (0.4, None), (0.6, 0, True)]
    assert day_drift.kept_days(rows, ['a', 'b', 'c', 'd']) == ['a', 'd']
    with pytest.raises(ValueError):
        day_drift.kept_days(rows, ['a'])


@pytest.mark.parametrize('daily', [nhl_daily, nba_daily], ids=['nhl', 'nba'])
def test_each_daily_reads_the_days_in_the_losses_order(daily, tmp_path):
    for gid, start, slate in (('1', '2026-10-12T23:00:00Z', '2026-10-12'), ('2', '2026-10-10T23:00:00Z', '2026-10-10'),
                              ('3', '2026-10-11T02:00:00Z', '2026-10-10')):
        (tmp_path / f'{gid}.json').write_text(json.dumps({'game_id': gid, 'pick': 'X', 'model_a': 0.6, 'slate': slate,
                                                          'start_utc': start}), encoding='utf-8')
    sched = pd.DataFrame([{'game_id': g, 'status': 'final', 'home_win': 1} for g in ('1', '2', '3')])
    assert daily.drift_days(tmp_path, sched) == ['2026-10-10', '2026-10-10', '2026-10-12']


@pytest.mark.parametrize('drift', [nhl_drift, nba_drift], ids=['nhl', 'nba'])
def test_each_look_resamples_its_own_picks_days(drift):
    spec = drift.baseline()
    losses = [0.55, 0.7, 0.62, 0.81, 0.6] * 40
    days = [f'd{i // 7:03d}' for i in range(200)]
    looks = drift.looks(losses, spec, days=days) if drift is nhl_drift else drift.looks(losses, spec, None, days)
    rule = spec['rule']
    for look in looks:
        n = look['games']
        assert look['lower_bound'] == day_drift.lower_bound(losses[:n], rule, rule['per_look_level'], days[:n])


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_each_daily_run_passes_the_days(sport):
    src = (ROOT / 'src' / 'sports' / sport / 'daily.py').read_text(encoding='utf-8').replace('\r\n', '\n')
    assert 'days = drift.kept_days(' in src and 'drift_days(folder, sched))' in src
    assert ('drift.flags(losses, spec, days)' in src) or ('drift.flags(losses, spec, bases, days)' in src)
