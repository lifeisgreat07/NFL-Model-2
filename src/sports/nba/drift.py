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

Amended 2026-11-04 (Stage 85 item 1, `drift.amended_2026_11_04` in the
registry): the rule above was tested at every daily run once 100 picks were
graded. It now looks only at the checkpoints in the baseline file's rule,
each at the per-look level that shares the 5% false-flag rate among them.
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


def lower_bound(losses: list[float], rule: dict[str, Any], level: float | None = None) -> float:
    """The one-sided lower bound of mean log loss at `level` (the rule's
    one_sided_level when not given), by the rule's seeded bootstrap."""
    arr = np.asarray(losses, dtype=float)
    rng = np.random.default_rng(rule['seed'])
    idx = rng.integers(0, len(arr), size=(rule['n_resamples'], len(arr)))
    lvl = rule['one_sided_level'] if level is None else level
    return float(np.percentile(arr[idx].mean(axis=1), (1 - lvl) * 100))


def looks(losses: list[float], spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Every registered look the graded picks have reached (Stage 85 item 1).

    The check looks only at the registered checkpoints, each on the first n
    graded picks in the order their games started, at the per-look level:
    the family's one-sided 95% shared over the looks (Bonferroni). A daily
    look at 95% has a 5% false-flag chance each day, and every extra look
    can only add to the season's."""
    rule = spec['rule']
    out = []
    for n in rule['checkpoints']:
        if len(losses) < n:
            break
        bound = lower_bound(losses[:n], rule, rule['per_look_level'])
        out.append({'games': n, 'lower_bound': bound, 'flagged': bool(bound > spec['baseline']['value'])})
    return out


def next_look(n_graded: int, spec: dict[str, Any]) -> int | None:
    """The checkpoint the check will look at next, or None after the last."""
    return next((n for n in spec['rule']['checkpoints'] if n > n_graded), None)


def flags(losses: list[float], spec: dict[str, Any]) -> bool:
    """True when any look so far has flagged: a flag stands for the season."""
    return any(look['flagged'] for look in looks(losses, spec))
