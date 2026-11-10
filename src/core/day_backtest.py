"""The day sports' walk-forward backtest and its scoring (Stage 87 item 2).

One copy for both day sports; src/sports/nhl/backtest.py and src/sports/nba/backtest.py re-export
these names, and tests/test_core_python.py fails if a copy comes back."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

EPS = 1e-15


def estimator() -> Any:
    """The registered estimator: L2 logistic regression, C=1.0, after a
    StandardScaler fitted on each refit's own rows."""
    return make_pipeline(StandardScaler(), LogisticRegression(C=1.0, l1_ratio=0.0, max_iter=1000))


def walk_forward(table: pd.DataFrame, columns: Sequence[str], seasons: Sequence[int],
                 needs_market: bool = False) -> pd.Series:
    """Out-of-sample probabilities for every game of `seasons`, refitting
    before each game day on every earlier row. With `needs_market`, rows
    without a market price are neither trained on nor predicted."""
    rows = table.dropna(subset=['home_prob']) if needs_market else table
    preds: dict[str, float] = {}
    for day in sorted(rows.loc[rows['season'].isin(seasons), 'day'].unique()):
        train = rows[rows['day'] < day]
        today = rows[rows['day'] == day]
        model = estimator().fit(train[list(columns)], train['home_win'])
        p = model.predict_proba(today[list(columns)])[:, 1]
        preds.update(zip(today['game_id'], p))
    return pd.Series(preds, name='p')


def base_rate(table: pd.DataFrame, seasons: Sequence[int]) -> pd.Series:
    """The home-win share of every earlier game, per game day."""
    preds: dict[str, float] = {}
    for day in sorted(table.loc[table['season'].isin(seasons), 'day'].unique()):
        rate = table.loc[table['day'] < day, 'home_win'].mean()
        for gid in table.loc[table['day'] == day, 'game_id']:
            preds[gid] = rate
    return pd.Series(preds, name='p')


def log_losses(p: npt.NDArray[np.float64], y: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    p = np.clip(p, EPS, 1 - EPS)
    out: npt.NDArray[np.float64] = -(y * np.log(p) + (1 - y) * np.log(1 - p))
    return out


def scores(p: pd.Series, table: pd.DataFrame) -> dict[str, float]:
    t = table.set_index('game_id').loc[p.index]
    y, q = t['home_win'].to_numpy(float), p.to_numpy(float)
    return {'games': int(len(q)), 'log_loss': float(log_losses(q, y).mean()),
            'brier': float(((q - y) ** 2).mean()), 'accuracy': float(((q > 0.5) == (y == 1)).mean())}


def label(interval: dict[str, float]) -> str:
    """The registered rule: ACCEPT if the interval lies below 0, REJECT if
    above, otherwise INCONCLUSIVE."""
    if interval['high'] < 0:
        return 'ACCEPT'
    if interval['low'] > 0:
        return 'REJECT'
    return 'INCONCLUSIVE'
