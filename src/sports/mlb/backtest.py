"""MLB's Stage 98 backtest, as registered (experiments/mlb/stage98/registry.json). Stage 99 item 3, first part.

**Tuning** (`results/tuning.json`): for each (H, lambda) in the registered grid, Model A walk-forward over the
validation seasons 2023 and 2024, scored by log loss over all their games pooled. The lowest wins; ties go to the
earlier grid entry. No game after the last validation season is read.

The confirmation seasons (2025 and 2026), Model B and the market wait: 2026's Retrosheet log is not posted, so 2026
is not yet checked and so not yet used (the registration's fallback_check), and the market history is read in its
own step.

Walk-forward: before each game day, refit on every game strictly earlier (from 2010), then predict that day. On a
neutral-site game the fitted intercept, the home edge, is not added to the forecast; its row still enters the fit.
Only seasons `data/mlb/history/checks.json` marks checked are read.

Run by hand: python -m src.sports.mlb.backtest
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.core.day_backtest import estimator, scores
from src.core.sport import sport_paths
from src.sports.mlb import history, ratings

PATHS = sport_paths('mlb')
FOLDER = PATHS.experiments / 'stage98'
REGISTRY = FOLDER / 'registry.json'
RESULTS = FOLDER / 'results'


def registry() -> dict[str, Any]:
    reg: dict[str, Any] = json.loads(REGISTRY.read_text(encoding='utf-8'))
    return reg


def checked_seasons(folder: Path = history.HISTORY) -> set[int]:
    doc = json.loads((folder / 'checks.json').read_text(encoding='utf-8'))
    return {int(s) for s, c in doc.items() if c['checked']}


def load_history(first: int, last: int, folder: Path = history.HISTORY) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(games, pitcher lines) for seasons `first` to `last`. Raises if any of them is not checked against
    Retrosheet."""
    seasons = range(first, last + 1)
    unchecked = sorted(set(seasons) - checked_seasons(folder))
    if unchecked:
        raise history.HistoryError(f'seasons not checked against Retrosheet, so not used: {unchecked}')
    games = pd.concat([pd.read_csv(folder / f'games_{s}.csv', dtype={'game_id': str, 'home': str, 'away': str})
                       for s in seasons], ignore_index=True)
    lines = pd.concat([pd.read_csv(folder / f'pitchers_{s}.csv', dtype={'game_id': str, 'pitcher_id': str})
                       for s in seasons], ignore_index=True)
    return games, lines


def walk_forward(table: pd.DataFrame, columns: Sequence[str], seasons: Sequence[int]) -> pd.Series:
    """Out-of-sample home-win probabilities for every game of `seasons`, refitting before each game day on every
    earlier row; a neutral-site game's forecast loses the fitted intercept."""
    table = table.dropna(subset=['home_win'])  # an official tie is neither trained on nor scored
    preds: dict[str, float] = {}
    for day in sorted(table.loc[table['season'].isin(seasons), 'day'].unique()):
        train = table[table['day'] < day]
        today = table[table['day'] == day]
        model = estimator().fit(train[list(columns)], train['home_win'])
        z = model.decision_function(today[list(columns)])
        neutral = today['neutral_site'].astype(bool).to_numpy()
        z = np.where(neutral, z - float(model[-1].intercept_[0]), z)
        preds.update(zip(today['game_id'], 1.0 / (1.0 + np.exp(-z))))
    return pd.Series(preds, name='p')


def tune(games: pd.DataFrame, lines: pd.DataFrame, reg: dict[str, Any]) -> dict[str, Any]:
    grid = reg['models']['model_a']['grid']
    seasons = reg['protocol']['validation_seasons']
    games = games[games['season'] <= max(seasons)]
    results = []
    for h in grid['H_days']:
        table = ratings.features(games, lines, h, grid['lambda'])
        for lam in grid['lambda']:
            cols = [f'run_matchup_{lam:g}', 'starter_matchup']
            s = scores(walk_forward(table, cols, seasons), table)
            results.append({'H_days': h, 'lambda': lam, **s})
            print(f'H={h} lambda={lam}: log loss {s["log_loss"]:.5f} over {s["games"]} games', flush=True)
    best = min(results, key=lambda r: r['log_loss'])  # min keeps the first of equals
    return {'seasons': seasons, 'grid': results, 'chosen': {'H_days': best['H_days'], 'lambda': best['lambda']}}


def main() -> int:
    reg = registry()
    p = reg['protocol']
    games, lines = load_history(p['training_from_season'], max(p['validation_seasons']))
    tuning = tune(ratings.prepare(games), lines, reg)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / 'tuning.json').write_text(json.dumps(tuning, indent=1) + '\n', encoding='utf-8')
    print(f"chosen: H {tuning['chosen']['H_days']}, lambda {tuning['chosen']['lambda']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
