"""Model A's three features for the NBA, built walk-forward (Stage 61, as registered).

`experiments/nba/stage61/registry.json` fixes what is computed here:

- **point_matchup**: before each game day, a weighted ridge regression of
  every earlier game's point margin (home minus away) on team indicators
  with a home term, `margin = home_edge + rating[home] - rating[away]`. The
  weight of a game played `d` days earlier is 0.5^(d / H); the ridge
  strength `lambda` falls on the team terms only. The feature is the home
  rating minus the away rating.
- **efficiency_matchup**: the same, on the margin per 100 possessions. A
  game's possessions are the mean of the two teams' FGA + 0.44 FTA - OREB
  + TOV (`src/sports/nba/history.py` writes them).
- **availability_matchup**: home availability minus away availability. A
  team's availability is the share of its expected minutes that play. A
  player's expected minutes are his recency-weighted minutes per team game
  over the team's earlier games, with the same weights; the share is the
  expected minutes of the players who play over the team's total. In the
  backtest the players who play are the box score's (minutes above zero).

ESPN's abbreviations are stable from 2015-16 on (the registration's team
identity), so no franchise map is needed.

Every feature for a game day uses only games that ended before that day:
the rows each day fits on are selected by `day < today` and nothing else.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import pandas as pd

#: Fewer earlier games than this and a day is not rated (the first days of
#: the first training season).
MIN_TRAIN = 100


def prepare(games: pd.DataFrame) -> pd.DataFrame:
    """The games with dates parsed and the two margins and the outcome added.
    Expects `src/sports/nba/history.py`'s game columns."""
    g = games.copy()
    g['game_id'] = g['game_id'].astype(str)
    g['day'] = pd.to_datetime(g['slate'])
    g['point_margin'] = (g['home_score'] - g['away_score']).astype(float)
    g['efficiency_margin'] = 100.0 * g['point_margin'] / g['possessions'].astype(float)
    g['home_win'] = (g['home_score'] > g['away_score']).astype(int)
    return g.sort_values(['day', 'game_id'], kind='stable').reset_index(drop=True)


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


def expected_minutes(minutes: pd.DataFrame, day_of: Mapping[str, pd.Timestamp], team: str,
                     day: pd.Timestamp, half_life: float) -> dict[str, float]:
    """Each player's recency-weighted minutes per `team` game, over the
    team's games before `day`. A player counts for the games he was listed
    in for that team; a game he was not listed in counts as 0 for him."""
    rows = minutes[minutes['team'] == team]
    rows = rows[rows['game_id'].map(day_of) < day]
    if rows.empty:
        return {}
    game_days = pd.Series({gid: day_of[gid] for gid in rows['game_id'].unique()})
    w = pd.Series(weights(game_days, day, half_life), index=game_days.index)
    total = float(w.sum())
    per_player = (rows['minutes'].to_numpy(float) * rows['game_id'].map(w).to_numpy(float))
    sums = pd.Series(per_player, index=rows['player_id'].to_numpy()).groupby(level=0).sum()
    return {str(p): float(v) / total for p, v in sums.items()}


def availability(expected: Mapping[str, float], playing: Iterable[str]) -> float:
    """The share of `expected` minutes that belongs to players in `playing`.
    A team with no earlier games has nothing missing: 1.0."""
    total = sum(expected.values())
    if total <= 0:
        return 1.0
    plays = {str(p) for p in playing}
    return sum(v for p, v in expected.items() if p in plays) / total


@dataclass(frozen=True)
class DayRatings:
    """Every team rating as it stood before one game day."""
    point: dict[str, float]
    efficiency: dict[str, float]

    def matchup(self, home: str, away: str) -> dict[str, float]:
        return {'point_matchup': self.point.get(home, 0.0) - self.point.get(away, 0.0),
                'efficiency_matchup': self.efficiency.get(home, 0.0) - self.efficiency.get(away, 0.0)}


def day_ratings(train: pd.DataFrame, day: pd.Timestamp, half_life: float, alpha: float) -> DayRatings:
    w = weights(train['day'], day, half_life)
    _, point = ridge_ratings(train, 'point_margin', w, alpha)
    _, eff = ridge_ratings(train, 'efficiency_margin', w, alpha)
    return DayRatings(point, eff)


def availability_table(games: pd.DataFrame, minutes: pd.DataFrame, half_life: float) -> pd.Series:
    """availability_matchup for every game, indexed by game_id.

    It walks each team's games in date order, carrying each player's
    weighted minutes and the weighted game count forward and decaying both
    by 0.5^(days / H) between games: the same numbers `expected_minutes`
    computes from scratch, in one pass. A team's games before its first
    have nothing to weigh, so its first game's availability is 1.0."""
    m = minutes.copy()
    m['game_id'] = m['game_id'].astype(str)
    m['player_id'] = m['player_id'].astype(str)
    day_of = dict(zip(games['game_id'], games['day']))
    m = m[m['game_id'].isin(day_of)]
    by_game_team = {key: frame for key, frame in m.groupby(['game_id', 'team'])}
    avail: dict[tuple[str, str], float] = {}
    for team in sorted(set(games['home']) | set(games['away'])):
        own = games[(games['home'] == team) | (games['away'] == team)].sort_values(['day', 'game_id'], kind='stable')
        carried: dict[str, float] = {}
        weight_sum = 0.0
        last: pd.Timestamp | None = None
        for gid, day in zip(own['game_id'], own['day']):
            if last is not None and day > last:
                decay = 0.5 ** ((day - last).days / half_life)
                carried = {p: v * decay for p, v in carried.items()}
                weight_sum *= decay
                last = day
            elif last is None:
                last = day
            rows = by_game_team.get((gid, team))
            playing = set() if rows is None else set(rows.loc[rows['minutes'] > 0, 'player_id'])
            expected = {p: v / weight_sum for p, v in carried.items()} if weight_sum else {}
            avail[(gid, team)] = availability(expected, playing)
            if rows is not None:
                for p, mins in zip(rows['player_id'], rows['minutes'].astype(float)):
                    carried[p] = carried.get(p, 0.0) + mins
            weight_sum += 1.0
    return pd.Series({gid: avail[(gid, h)] - avail[(gid, a)]
                      for gid, h, a in zip(games['game_id'], games['home'], games['away'])},
                     name='availability_matchup')


def features(games: pd.DataFrame, minutes: pd.DataFrame, half_life: float, alpha: float,
             first_day: str | None = None, avail: pd.Series | None = None) -> pd.DataFrame:
    """One row per game from `first_day` on with point_matchup,
    efficiency_matchup and availability_matchup, each built only from games
    on earlier days. `games` is `prepare`d; `minutes` is the history's
    minutes table (game_id, team, player_id, minutes). `avail`, when given,
    is `availability_table(games, minutes, half_life)` computed once for
    every lambda that shares H."""
    if avail is None:
        avail = availability_table(games, minutes, half_life)
    days = sorted(games['day'].unique())
    if first_day is not None:
        days = [d for d in days if d >= pd.Timestamp(first_day)]
    out = []
    for day in days:
        day = pd.Timestamp(day)
        train = games[games['day'] < day]
        if len(train) < MIN_TRAIN:
            continue
        rated = day_ratings(train, day, half_life, alpha)
        for g in games[games['day'] == day].itertuples():
            row: dict[str, object] = {'game_id': g.game_id, 'day': day, 'season': g.season,
                                      'game_type': g.game_type, 'home': g.home, 'away': g.away,
                                      'home_win': g.home_win}
            row.update(rated.matchup(g.home, g.away))
            row['availability_matchup'] = float(avail[g.game_id])
            out.append(row)
    return pd.DataFrame(out)
