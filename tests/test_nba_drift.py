"""The NBA's drift check: the registered rule, and a baseline that is the
backtest's own figure.

Run with: pytest tests/test_nba_drift.py -v
"""
import json
import math
from pathlib import Path

import pytest

from src.sports.nba import drift

ROOT = Path(__file__).resolve().parents[1]
SPEC = drift.baseline()


def test_the_baseline_is_model_as_confirmation_log_loss():
    doc = json.loads((ROOT / 'experiments/nba/stage61/results/confirmation.json').read_text(encoding='utf-8'))
    assert SPEC['baseline']['value'] == doc['scores']['model_a']['log_loss']
    assert SPEC['rule']['min_games'] == 100 and SPEC['rule']['one_sided_level'] == 0.95


def test_per_game_log_loss_skips_games_without_a_result():
    losses = drift.per_game_log_loss([(0.8, 1), (0.8, 0), (None, 1), (0.6, None)])
    assert losses == pytest.approx([-math.log(0.8), -math.log(0.2)])


def test_too_few_games_never_flags():
    assert drift.flags([5.0] * 99, SPEC) is False


def test_a_clearly_worse_season_flags_and_a_matching_one_does_not():
    assert drift.flags([0.70] * 150, SPEC) is True
    v = SPEC['baseline']['value']
    # A season that averages the baseline, with spread. (A constant column of
    # exactly the baseline can sit one float ulp above it after averaging.)
    assert drift.flags([v - 0.2, v + 0.2] * 75, SPEC) is False


def test_the_bound_is_one_sided_and_seeded():
    losses = [0.5, 0.6, 0.7] * 50
    a, b = drift.lower_bound(losses, SPEC['rule']), drift.lower_bound(losses, SPEC['rule'])
    assert a == b and a < sum(losses) / len(losses)
