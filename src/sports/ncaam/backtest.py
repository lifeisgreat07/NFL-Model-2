"""The March Madness backtest (Stage 103 item 2), as `experiments/ncaam/stage103/registry.json` fixes it.

So far the tuning only: the registered grid is searched on the validation seasons, by Model A's log loss over
their games from 1 January on, walking forward a game day at a time. The confirmation on the 2021 to 2026
tournaments is not written yet and nothing here scores them.

Run by hand: python -m src.sports.ncaam.backtest            (tuning; writes results/tuning.json once)
"""
from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.day_backtest import log_losses
from src.core.sport import sport_paths
from src.sports.ncaam import ratings
from src.sports.ncaam.collector import HISTORY, CollectorError

PATHS = sport_paths('ncaam')
FOLDER = PATHS.experiments / 'stage103'
REGISTRY = FOLDER / 'registry.json'
RESULTS = FOLDER / 'results'


def registry() -> dict[str, Any]:
    reg: dict[str, Any] = json.loads(REGISTRY.read_text(encoding='utf-8'))
    return reg


def checked_seasons(folder: Path = HISTORY) -> set[int]:
    path = folder / 'checks.json'
    if not path.exists():
        return set()
    doc = json.loads(path.read_text(encoding='utf-8'))
    return {int(s) for s, c in doc.items() if c['checked']}


def load_history(first: int, last: int, folder: Path = HISTORY) -> pd.DataFrame:
    """Seasons `first` to `last`. Raises if any of them has not passed the fallback check."""
    unchecked = sorted(set(range(first, last + 1)) - checked_seasons(folder))
    if unchecked:
        raise CollectorError(f'seasons not checked against the fallback, so not used: {unchecked}')
    return ratings.load(first, last, folder)


def walk_forward(table: pd.DataFrame) -> pd.Series:
    """Model A's probability for every row of `table` (ratings.margins' output) that has an earlier row: before
    each game day the curve is refitted on every row strictly earlier. The first day has no earlier row and is
    not forecast."""
    preds: dict[str, float] = {}
    for day in sorted(table['day'].unique()):
        train = table[table['day'] < day]
        if train.empty:
            continue
        today = table[table['day'] == day]
        coef = ratings.slope(train['walk'].to_numpy(float), train['home_win'].to_numpy())
        preds.update(zip(today['game_id'], ratings.prob(coef, today['walk'].to_numpy(float))))
    return pd.Series(preds, name='p', dtype=float)


def scores(p: pd.Series, table: pd.DataFrame) -> dict[str, float]:
    y = table.set_index('game_id').loc[p.index, 'home_win'].to_numpy(float)
    q = p.to_numpy(float)
    return {'games': int(len(q)), 'log_loss': float(log_losses(q, y).mean()),
            'brier': float(((q - y) ** 2).mean()), 'accuracy': float(((q > 0.5) == (y == 1)).mean())}


def tune(games: pd.DataFrame, reg: dict[str, Any]) -> dict[str, Any]:
    """Every grid entry's scores on `games` (the validation seasons), and the entry with the lowest log loss,
    ties to the earlier entry."""
    grid = reg['models']['model_a']['grid']
    results = []
    for h in grid['H_days']:
        for lam in grid['lambda']:
            table = ratings.margins(games, h, lam)
            s = scores(walk_forward(table), table)
            results.append({'H_days': h, 'lambda': lam, **s})
            print(f'H={h} lambda={lam}: log loss {s["log_loss"]:.5f} over {s["games"]} games', flush=True)
    best = min(results, key=lambda r: r['log_loss'])  # min keeps the first of equals
    return {'seasons': sorted(int(s) for s in games['season'].unique()), 'grid': results,
            'chosen': {'H_days': best['H_days'], 'lambda': best['lambda']}}


def validation_seasons(reg: dict[str, Any]) -> list[int]:
    """A tournament is named by the year it is played; its season starts the year before."""
    return [t - 1 for t in reg['protocol']['validation_tournaments']]


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        raise SystemExit('usage: python -m src.sports.ncaam.backtest')
    if (RESULTS / 'tuning.json').exists():
        raise SystemExit('results/tuning.json exists: the tuning is run once and never rewritten')
    reg = registry()
    seasons = validation_seasons(reg)
    if min(seasons) != reg['protocol']['training_from_season']:
        raise SystemExit('the validation seasons no longer start where the history does')
    tuning = tune(load_history(min(seasons), max(seasons)), reg)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / 'tuning.json').write_text(json.dumps(tuning, indent=1) + '\n', encoding='utf-8')
    print(f"chosen: H {tuning['chosen']['H_days']}, lambda {tuning['chosen']['lambda']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
