"""Model A's three features, built walk-forward (Stage 56, as registered).

`experiments/nhl/stage56/registry.json` fixes what is computed here:

- **goal_matchup** and **shot_matchup**: before each game day, a weighted
  ridge regression of every earlier game's margin on team indicators with a
  home term, `margin = home_edge + rating[home] - rating[away]`. The weight
  of a game played `d` days earlier is 0.5^(d / H). The ridge strength is 1.0
  on the team terms only. The goal margin leaves out a shootout's deciding
  goal, so a shootout game's margin is 0; the shot margin is shots on goal.
- **goalie_matchup**: each goalie's recency-weighted goals saved above the
  league's rate on the shots he faced, divided by (his weighted shots + K).
  The league rate comes from the same weighted earlier games. A goalie with
  no earlier shots has a rating of 0. `goalie_terms` keeps the numerator and
  the weighted shots apart, so each K in the grid costs nothing extra.

Ratings follow the franchise's roster (`FRANCHISE`): Atlanta's games count
as Winnipeg's, Phoenix's and Arizona's as Utah's.

Every feature for a game day uses only games that ended before that day,
which `features` checks rather than trusts: the rows it fits on are
selected by `game_date < day` and nothing else.
"""
from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import numpy.typing as npt
import pandas as pd

#: Older club -> the current club whose history it is (the registration's
#: team identity). Vegas and Seattle need no entry: they start with none.
FRANCHISE = {'ATL': 'WPG', 'PHX': 'UTA', 'ARI': 'UTA'}

RIDGE = 1.0


def franchise(abbr: str) -> str:
    return FRANCHISE.get(abbr, abbr)


def prepare(games: pd.DataFrame) -> pd.DataFrame:
    """The box-score history with franchises mapped, dates parsed and the
    two margins added. Expects `src/sports/nhl/history.py`'s columns."""
    g = games.copy()
    g['home'] = g['home'].map(franchise)
    g['away'] = g['away'].map(franchise)
    g['day'] = pd.to_datetime(g['game_date'])
    margin = g['home_score'] - g['away_score']
    g['goal_margin'] = np.where(g['last_period'] == 'SO', 0, margin)
    g['shot_margin'] = g['home_sog'] - g['away_sog']
    g['home_win'] = (g['home_score'] > g['away_score']).astype(int)
    return g.sort_values(['day', 'game_id'], kind='stable').reset_index(drop=True)


def weights(days: pd.Series, day: pd.Timestamp, half_life: float) -> npt.NDArray[np.float64]:
    age = (day - days).dt.days.to_numpy(dtype=float)
    out: npt.NDArray[np.float64] = np.power(0.5, age / half_life)
    return out


def ridge_ratings(train: pd.DataFrame, value: str, w: npt.NDArray[np.float64],
                  alpha: float = RIDGE) -> tuple[float, dict[str, float]]:
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


def goalie_terms(train: pd.DataFrame, w: npt.NDArray[np.float64]) -> pd.DataFrame:
    """Per goalie: weighted goals saved above the league rate (`saved`) and
    weighted shots faced (`shots`). rating = saved / (shots + K)."""
    sa = np.concatenate([train['home_goalie_sa'].to_numpy(float), train['away_goalie_sa'].to_numpy(float)])
    ga = np.concatenate([train['home_goalie_ga'].to_numpy(float), train['away_goalie_ga'].to_numpy(float)])
    ww = np.concatenate([w, w])
    ids = np.concatenate([train['home_goalie_id'].to_numpy(), train['away_goalie_id'].to_numpy()])
    shots_w = (ww * sa).sum()
    league = (ww * ga).sum() / shots_w if shots_w else 0.0
    frame = pd.DataFrame({'goalie': ids, 'saved': ww * (league * sa - ga), 'shots': ww * sa})
    return frame.groupby('goalie')[['saved', 'shots']].sum()


def goalie_rating(terms: pd.DataFrame, goalie: object, k: float) -> float:
    if goalie not in terms.index:
        return 0.0
    row = terms.loc[goalie]
    return float(row['saved'] / (row['shots'] + k))


def features(games: pd.DataFrame, half_life: float, ks: Iterable[float],
             first_day: str | None = None) -> pd.DataFrame:
    """One row per game from `first_day` on: goal_matchup, shot_matchup and
    goalie_matchup_<K> for each K, each built only from games on earlier
    days. `games` is `prepare`d."""
    ks = list(ks)
    days = sorted(games['day'].unique())
    if first_day is not None:
        days = [d for d in days if d >= pd.Timestamp(first_day)]
    out = []
    for day in days:
        day = pd.Timestamp(day)
        train = games[games['day'] < day]
        today = games[games['day'] == day]
        if len(train) < 100:
            continue
        w = weights(train['day'], day, half_life)
        _, goal = ridge_ratings(train, 'goal_margin', w)
        _, shot = ridge_ratings(train, 'shot_margin', w)
        terms = goalie_terms(train, w)
        for g in today.itertuples():
            row = {'game_id': g.game_id, 'day': day, 'season': g.season, 'game_type': g.game_type,
                   'home': g.home, 'away': g.away, 'home_win': g.home_win,
                   'goal_matchup': goal.get(g.home, 0.0) - goal.get(g.away, 0.0),
                   'shot_matchup': shot.get(g.home, 0.0) - shot.get(g.away, 0.0)}
            for k in ks:
                row[f'goalie_matchup_{k:g}'] = (goalie_rating(terms, g.home_goalie_id, k)
                                                - goalie_rating(terms, g.away_goalie_id, k))
            out.append(row)
    return pd.DataFrame(out)
