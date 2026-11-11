"""The day sports' drift check (Stage 87 item 2): the per-game loss, the registered
looks' lower bound and the next look.

One copy for both day sports; src/sports/nhl/drift.py and src/sports/nba/drift.py re-export
these names, and tests/test_core_python.py fails if a copy comes back."""
from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

import numpy as np

EPS = 1e-15


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



def look_value(spec: dict[str, Any], key: str, n: int) -> float:
    """Stage 95 item 31 (audit 7, M4): the baseline `key` for a look at n graded
    picks: the backtest's figure over a season's first n games when the spec
    indexes it by look (`<key>_by_look`), else its one figure for whole seasons."""
    table = spec.get(f'{key}_by_look') or {}
    return float(table[str(n)]) if str(n) in table else float(spec[key]['value'])


def next_look(n_graded: int, spec: dict[str, Any]) -> int | None:
    """The checkpoint the check will look at next, or None after the last."""
    return next((n for n in spec['rule']['checkpoints'] if n > n_graded), None)
