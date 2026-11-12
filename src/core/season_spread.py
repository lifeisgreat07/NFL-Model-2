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


def by_look(walk_forward: Callable[..., pd.Series], scores: Callable[[pd.Series, pd.DataFrame], dict[str, float]],
            table: pd.DataFrame, columns: Sequence[str], validation: Sequence[int], confirmation: Sequence[int],
            checkpoints: Sequence[int]) -> list[dict[str, Any]]:
    """Stage 95 item 31 (audit 7, M4): the drift baseline indexed by games into
    the season. For each registered checkpoint n, Model A's log loss over each
    backtest season's first n games, the same walk-forward the baseline comes
    from, with the confirmation seasons pooled (each holds n games, so the mean)
    and the spread over every season. A live look at n graded picks is a
    season's first n games, and a season's first games are scored on ratings
    that have seen fewer of its games, so the full season's log loss is the
    wrong yardstick for an early look. The history keeps each game's day but
    not its start time, so a season's games are ordered by day, then game id;
    the live check orders them by start time, which can differ within a day."""
    preds: dict[int, pd.Series] = {}
    for season in [*validation, *confirmation]:
        pred = walk_forward(table, columns, [season])
        order = table[table['game_id'].isin(pred.index)].sort_values(['day', 'game_id'], kind='stable')['game_id']
        preds[int(season)] = pred.reindex(order.to_numpy())
    out: list[dict[str, Any]] = []
    for n in checkpoints:
        seasons = {int(s): float(scores(p.iloc[:n], table)['log_loss']) for s, p in preds.items() if len(p) >= n}
        conf = [seasons[int(s)] for s in confirmation if int(s) in seasons]
        if not conf:
            raise ValueError(f'no confirmation season holds {n} games')
        values = list(seasons.values())
        out.append({'games': int(n), 'confirmation': sum(conf) / len(conf), 'low': min(values), 'high': max(values),
                    'seasons': {season_label(s): v for s, v in seasons.items()}})
    return out
