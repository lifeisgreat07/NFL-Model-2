"""The NBA's drift check: is live Model A doing worse than its backtest said?

The NHL's rule (`src/sports/nhl/drift.py`, itself the NFL's Stage 33 R4),
registered for the NBA in `experiments/nba/stage65/registry.json`: once
`min_games` picks are graded, flag when the lower end of a one-sided 95%
bootstrap interval of mean per-game log loss is above the baseline in
`data/nba/drift_baseline.json`, Model A's log loss on Stage 61's
confirmation seasons. Each sport keeps its own copy, so neither reads the
other's files.

A flag is a reason to look, not proof that something broke: the backtest
knew who played, and a live pick knows only the injury report.
"""
from __future__ import annotations

import json
import math
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np

from src.core.sport import sport_paths

BASELINE = sport_paths('nba').data / 'drift_baseline.json'
EPS = 1e-15


def baseline(path: Path = BASELINE) -> dict[str, Any]:
    spec: dict[str, Any] = json.loads(path.read_text(encoding='utf-8'))
    for key in ('baseline', 'rule'):
        spec[key]  # a KeyError here is the "incomplete" case
    return spec


def per_game_log_loss(rows: Iterable[tuple[float | None, int | None]]) -> list[float]:
    """Per-game log loss from (Model A's home probability, home won) pairs;
    a game without both decides nothing."""
    out = []
    for p, y in rows:
        if p is None or y not in (0, 1):
            continue
        q = min(max(float(p), EPS), 1 - EPS)
        out.append(-math.log(q) if y == 1 else -math.log(1 - q))
    return out


def lower_bound(losses: list[float], rule: dict[str, Any]) -> float:
    arr = np.asarray(losses, dtype=float)
    rng = np.random.default_rng(rule['seed'])
    idx = rng.integers(0, len(arr), size=(rule['n_resamples'], len(arr)))
    return float(np.percentile(arr[idx].mean(axis=1), (1 - rule['one_sided_level']) * 100))


def flags(losses: list[float], spec: dict[str, Any]) -> bool:
    """True when the registered rule flags."""
    rule = spec['rule']
    if len(losses) < rule['min_games']:
        return False
    return bool(lower_bound(losses, rule) > spec['baseline']['value'])
