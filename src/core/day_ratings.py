"""The day sports' rating fit (Stage 87 item 2).

One copy for both day sports; src/sports/nhl/ratings.py and src/sports/nba/ratings.py re-export
these names, and tests/test_core_python.py fails if a copy comes back."""
from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pandas as pd


def weights(days: pd.Series, day: pd.Timestamp, half_life: float) -> npt.NDArray[np.float64]:
    age = (day - days).dt.days.to_numpy(dtype=float)
    out: npt.NDArray[np.float64] = np.power(0.5, age / half_life)
    return out


def ridge_ratings(train: pd.DataFrame, value: str, w: npt.NDArray[np.float64],
                  alpha: float) -> tuple[float, dict[str, float]]:
    """(home edge, rating per team) from a weighted ridge fit of
    `value = edge + r[home] - r[away]`, penalising the ratings only."""
    teams = sorted(set(train['home']) | set(train['away']))
    idx = {t: i + 1 for i, t in enumerate(teams)}
    n, k = len(train), len(teams) + 1
    x = np.zeros((n, k))
    x[:, 0] = 1.0
    rows = np.arange(n)
    x[rows, train['home'].map(idx).to_numpy()] = 1.0
    x[rows, train['away'].map(idx).to_numpy()] = -1.0
    y = train[value].to_numpy(dtype=float)
    xtw = x.T * w
    penalty = np.full(k, alpha)
    penalty[0] = 0.0
    beta = np.linalg.solve(xtw @ x + np.diag(penalty), xtw @ y)
    return float(beta[0]), {t: float(beta[i]) for t, i in idx.items()}
