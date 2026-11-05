"""The drift baseline's season-to-season spread (Stage 85 item 3, the 2026-11-02
review).

Each day sport's drift check compares live Model A against one number: Model
A's log loss pooled over the backtest's two confirmation seasons. A reader of
"flagged" or "not flagged" cannot tell from that number how far a single
season moves on its own. This scores the same Model A, at the settings the
validation chose, season by season over the validation and confirmation
seasons, with the backtest's own walk-forward, and checks that the
confirmation seasons pooled give back the registered baseline.

Sport-agnostic: the sport passes its walk_forward and scores functions
(src/core does not import a sport).
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import pandas as pd


def season_label(season: int) -> str:
    return f'{season}-{(season + 1) % 100:02d}'


def spread(walk_forward: Callable[..., pd.Series], scores: Callable[[pd.Series, pd.DataFrame], dict[str, float]],
           table: pd.DataFrame, columns: Sequence[str], validation: Sequence[int], confirmation: Sequence[int],
           baseline: float) -> dict[str, Any]:
    """Model A's scores for each season, and the pooled confirmation check."""
    rows: list[dict[str, Any]] = []
    for season in [*validation, *confirmation]:
        s = scores(walk_forward(table, columns, [season]), table)
        rows.append({'season': int(season), 'label': season_label(int(season)),
                     'role': 'validation' if season in validation else 'confirmation', **s})
    conf = [r for r in rows if r['role'] == 'confirmation']
    games = int(sum(r['games'] for r in conf))
    pooled = float(sum(r['log_loss'] * r['games'] for r in conf)) / games
    values = [float(r['log_loss']) for r in rows]
    return {
        'seasons': rows,
        'baseline': {'value': baseline, 'pooled_confirmation': pooled, 'games': games,
                     'agrees': abs(pooled - baseline) < 1e-9},
        'spread': {'low': min(values), 'high': max(values), 'range': max(values) - min(values)},
    }
