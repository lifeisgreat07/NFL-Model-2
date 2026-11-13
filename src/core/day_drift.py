"""The day sports' drift check (Stage 87 item 2): the per-game loss, the registered
looks' lower bound and the next look.

One copy for both day sports; src/sports/nhl/drift.py and src/sports/nba/drift.py re-export
these names, and tests/test_core_python.py fails if a copy comes back."""
from __future__ import annotations

import json
import math
from collections.abc import Iterable, Sequence
from pathlib import Path
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


def lower_bound(losses: list[float], rule: dict[str, Any], level: float | None = None,
                days: Sequence[str] | None = None) -> float:
    """The one-sided lower bound of mean log loss at `level` (the rule's
    one_sided_level when not given), by the rule's seeded bootstrap.

    Stage 95 item 32 (audit 7, M4): given each loss's game day, the bootstrap
    resamples whole days, each resample the pooled mean of the days drawn.
    Games on one day share conditions, so drawing single games treats them as
    independent, which they need not be; drawing days does not, whichever way
    that moves the bound (when a day's games move together it widens the
    interval). Without days it draws single games, as before."""
    arr = np.asarray(losses, dtype=float)
    rng = np.random.default_rng(rule['seed'])
    lvl = rule['one_sided_level'] if level is None else level
    if days is None:
        idx = rng.integers(0, len(arr), size=(rule['n_resamples'], len(arr)))
        return float(np.percentile(arr[idx].mean(axis=1), (1 - lvl) * 100))
    if len(days) != len(arr):
        raise ValueError(f'{len(days)} days for {len(arr)} losses')
    labels = sorted(set(days))
    pos = {d: i for i, d in enumerate(labels)}
    which = np.array([pos[d] for d in days])
    sums = np.bincount(which, weights=arr, minlength=len(labels))
    counts = np.bincount(which, minlength=len(labels)).astype(float)
    idx = rng.integers(0, len(labels), size=(rule['n_resamples'], len(labels)))
    means = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)
    return float(np.percentile(means, (1 - lvl) * 100))


def kept_days(rows: Iterable[tuple[Any, ...]], days: Sequence[str]) -> list[str]:
    """Stage 95 item 32: the days of the rows a per-game log loss keeps (a game
    without both a probability and a result decides nothing, `per_game_log_loss`),
    so each loss has its own day."""
    rows = list(rows)
    if len(rows) != len(days):
        raise ValueError(f'{len(days)} days for {len(rows)} rows')
    return [d for r, d in zip(rows, days, strict=True) if r[0] is not None and r[1] in (0, 1)]



def look_value(spec: dict[str, Any], key: str, n: int) -> float:
    """Stage 95 item 31 (audit 7, M4): the baseline `key` for a look at n graded
    picks: the backtest's figure over a season's first n games when the spec
    indexes it by look (`<key>_by_look`), else its one figure for whole seasons."""
    table = spec.get(f'{key}_by_look') or {}
    return float(table[str(n)]) if str(n) in table else float(spec[key]['value'])



def leaked_picks(folder: Path) -> int:
    """Stage 95 item 33: how many saved picks' own records show they could have
    seen their result (src/core/pick_guard.py: fitted through their slate day,
    saved or priced at or after the start)."""
    from src.core import pick_guard
    paths = sorted(folder.glob('*.json')) if folder.exists() else []
    return sum(1 for p in paths if pick_guard.problems(json.loads(p.read_text(encoding='utf-8'))))


def leak_direction(mean: float | None, games: int, baseline: float, spread_range: float | None,
                   first_look: int, leaked: int) -> dict[str, Any]:
    """Stage 95 item 33 (audit 7, M4): the drift check only looks for live
    Model A doing worse than its backtest. Doing better by more than the
    backtest's seasons differ from each other is the other direction a leak
    shows in. Said, not flagged: from the first registered look on, with the
    margin and the spread; and the count of saved picks whose own records show
    a leak. A report for a reader, not a rule that decides anything."""
    better = (mean is not None and spread_range is not None and games >= first_look
              and baseline - mean > spread_range)
    return {'better_than_spread': bool(better),
            'margin': None if mean is None else round(baseline - mean, 6),
            'spread_range': spread_range, 'leaked_picks': int(leaked)}


def leak_lines(leak: dict[str, Any]) -> list[str]:
    """The run log's lines for `leak_direction`'s result; none when there is nothing to say."""
    out = []
    if leak['better_than_spread']:
        out.append(f"LEAK CHECK: live log loss is {leak['margin']:.4f} better than the backtest, more than the "
                   f"{leak['spread_range']:.4f} its seasons differ by; worth checking no pick saw its result")
    if leak['leaked_picks']:
        out.append(f"LEAK CHECK: {leak['leaked_picks']} saved pick(s) could have seen their result by their own "
                   'records (src/core/pick_guard.py)')
    return out


def next_look(n_graded: int, spec: dict[str, Any]) -> int | None:
    """The checkpoint the check will look at next, or None after the last."""
    return next((n for n in spec['rule']['checkpoints'] if n > n_graded), None)
