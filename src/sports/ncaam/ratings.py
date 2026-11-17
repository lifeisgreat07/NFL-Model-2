"""Model A's ratings and curve for the March Madness bracket (Stage 103 item 2).

`experiments/ncaam/stage103/registry.json` fixes them: each club's rating and the home edge come from a
recency-weighted ridge regression of the point margin of the same season's games strictly before the day being
forecast; a game's expected margin is home rating minus away rating, plus the home edge when the game is not
neutral; a logistic curve with no intercept turns it into a probability, so a forecast is one minus itself when
the two clubs are swapped.

Two expected margins are kept for a game:

- `walk`, from the games strictly before its own day. The curve's rows and the tuning use it.
- `lock`, for an NCAA tournament game only: from the games strictly before the tournament's first game, the same
  for every round. The confirmation and the live bracket use it; a later round never reads an earlier round.

The ridge is solved from sums that grow a day at a time, not from a fresh table every day: a game's weight on day
D is 0.5^((D - its day) / H) = 0.5^((D - first day) / H) x 2^((its day - first day) / H), and the first factor is
common to every game, so each game is added once with the second.
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd
from sklearn.linear_model import LogisticRegression

from src.sports.ncaam.collector import HISTORY

NCAA = '22'
Array = npt.NDArray[np.float64]


def load(first: int, last: int, folder: Path = HISTORY) -> pd.DataFrame:
    """Seasons `first` to `last` as one table in day order: ids, day, clubs, margin, neutral, tournament, home_win.
    An NCAA tournament game is neutral whatever ESPN's flag says."""
    g = pd.concat([pd.read_csv(folder / f'games_{s}.csv', dtype=str, keep_default_na=False)
                   for s in range(first, last + 1)], ignore_index=True)
    margin = g['home_score'].astype(int) - g['away_score'].astype(int)
    tournament = g['tournament_id'] == NCAA
    out = pd.DataFrame({'game_id': g['game_id'], 'season': g['season'].astype(int), 'day': pd.to_datetime(g['day']),
                        'home': g['home_id'], 'away': g['away_id'], 'margin': margin.astype(float),
                        'neutral': (g['neutral_site'] == 'True') | tournament, 'tournament': tournament,
                        'home_win': (margin > 0).astype(int)})
    return out.sort_values(['day', 'game_id'], kind='stable').reset_index(drop=True)


def curve_start(season: int) -> pd.Timestamp:
    """The first day whose games are curve rows: 1 January of the season's second year."""
    return pd.Timestamp(year=season + 1, month=1, day=1)


def solve(a: Array, b: Array, scale: float, lam: float) -> Array:
    """The ridge's coefficients (home edge first, then one per club) from the weighted sums `a` and `b`, each
    game's weight multiplied by `scale`. The edge is not penalised; with no home game yet it is 0."""
    m = scale * a
    m[np.diag_indices_from(m)] += lam
    m[0, 0] -= lam
    if a[0, 0] == 0:
        m[0, 0] = 1.0
    out: Array = np.linalg.solve(m, scale * b)
    return out


def season_margins(games: pd.DataFrame, h_days: float | None, lam: float) -> pd.DataFrame:
    """`walk` and `lock` (see the module's docstring) for one season's games, by game_id. `walk` is filled from
    the season's `curve_start` on and for every tournament game; `lock` for tournament games only."""
    [season] = games['season'].unique()
    clubs = sorted(set(games['home']) | set(games['away']))
    idx = {c: i + 1 for i, c in enumerate(clubs)}
    k = len(clubs) + 1
    a, b = np.zeros((k, k)), np.zeros(k)
    first = games['day'].min()
    t_first = games.loc[games['tournament'], 'day'].min()
    wanted_from = curve_start(int(season))
    frozen: Array | None = None
    rows: list[dict[str, Any]] = []
    for day, block in games.groupby('day', sort=True):
        h = block['home'].map(idx).to_numpy()
        w = block['away'].map(idx).to_numpy()
        site = (~block['neutral']).to_numpy(float)
        age = float((day - first).days)
        if day >= wanted_from or block['tournament'].any():
            beta = solve(a, b, 1.0 if h_days is None else 0.5 ** (age / h_days), lam)
            if frozen is None and pd.notna(t_first) and day >= t_first:
                frozen = beta
            walk = beta[h] - beta[w] + beta[0] * site
            lock = frozen[h] - frozen[w] if frozen is not None else np.full(len(block), np.nan)
            for gid, t, x, z in zip(block['game_id'], block['tournament'], walk, lock):
                rows.append({'game_id': gid, 'walk': float(x), 'lock': float(z) if t else np.nan})
        u = 1.0 if h_days is None else 2.0 ** (age / h_days)
        add_day(a, b, h, w, site, block['margin'].to_numpy(float), u)
    return pd.DataFrame(rows, columns=['game_id', 'walk', 'lock'])


def add_day(a: Array, b: Array, h: npt.NDArray[Any], w: npt.NDArray[Any], site: Array, margin: Array,
            u: float) -> None:
    """Add one day's games to the sums, each with weight `u`: a game's row is the home term (`site`), +1 for the
    home club and -1 for the away club."""
    cols, vals = (np.zeros(len(h), dtype=int), h, w), (site, np.ones(len(h)), -np.ones(len(h)))
    for p in range(3):
        np.add.at(b, cols[p], u * vals[p] * margin)
        for q in range(3):
            np.add.at(a, (cols[p], cols[q]), u * vals[p] * vals[q])


def margins(games: pd.DataFrame, h_days: float | None, lam: float) -> pd.DataFrame:
    """`games` from the first curve day of each season on, with `walk` and `lock` added, in day order."""
    parts = [season_margins(g, h_days, lam) for _, g in games.groupby('season', sort=True)]
    out = games.merge(pd.concat(parts, ignore_index=True), on='game_id', how='inner')
    return out.sort_values(['day', 'game_id'], kind='stable').reset_index(drop=True)


def slope(x: Array, y: Sequence[int] | npt.NDArray[Any]) -> float:
    """The registered curve: logistic regression, L2, C=1.0, no intercept and no scaling, on one column."""
    model = LogisticRegression(C=1.0, l1_ratio=0.0, fit_intercept=False, max_iter=1000)
    model.fit(np.asarray(x, dtype=float).reshape(-1, 1), np.asarray(y))
    return float(model.coef_[0, 0])


def prob(coef: float, x: Array) -> Array:
    """The home club's win probability for expected margins `x`."""
    out: Array = 1.0 / (1.0 + np.exp(-coef * np.asarray(x, dtype=float)))
    return out
