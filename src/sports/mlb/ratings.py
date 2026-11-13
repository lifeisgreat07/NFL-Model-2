"""MLB's Model A features, built walk-forward (Stage 99 item 1), as experiments/mlb/stage98/registry.json fixes them.

- **run_matchup**: before each game day, a weighted ridge regression of every earlier game's run margin (home minus
  away) on club indicators with a home term, `margin = edge x home + rating[home] - rating[away]`, where `home` is 1
  and 0 for a neutral-site game. A game played `d` days earlier weighs 0.5^(d / H); the ridge strength lambda falls
  on the club terms only. The feature is the home club's rating minus the away club's.
- **starter_matchup**: the away starter's rate minus the home starter's, so a higher value favours home. A pitcher's
  rate is his runs allowed per 27 outs over his earlier appearances (starts and relief), recency-weighted with the
  same H and shrunk toward the league by K outs: (weighted runs + K x the league's runs per out) / (weighted outs
  + K) x 27, the league's runs per out taken from every pitcher's appearances in the same earlier games. A pitcher
  with no earlier appearance gets the league rate. K is tuned with H and lambda (the amendment of 2026-11-12).

Every feature for a game day uses only games that ended before that day: the rows each day rates from are selected
by `day < today` and nothing else. The core's `ridge_ratings` has a home term on every game; MLB's registration
takes it off a neutral game, so the fit is here.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import pandas as pd

from src.core.day_ratings import weights as weights

#: Fewer earlier games than this and a day is not rated (the first days of the first training season).
MIN_TRAIN = 100
#: The shrinkage toward the league, in outs, when none is given (the grid's lowest, the value first registered).
SHRINK_OUTS = 150.0
OUTS_PER_GAME = 27.0
ET = 'America/New_York'


def prepare(games: pd.DataFrame) -> pd.DataFrame:
    """The history's games (`src/sports/mlb/history.py`) with dates parsed, the margin and the outcome added."""
    g = games.copy()
    for col in ('game_id', 'home', 'away', 'home_starter', 'away_starter'):
        g[col] = g[col].astype(str)
    # Audit 8 B1: a game is dated on the day it was completed. A suspended game keeps its official date (`slate`,
    # which the Retrosheet check matches on) but its result exists only from its resumption, the last listing's
    # start; dated on `slate` it fed every rating between the two days.
    g['day'] = pd.to_datetime(g['slate'])
    if 'start_utc' in g:
        start = pd.to_datetime(g['start_utc'], utc=True, errors='coerce').dt.tz_convert(ET)
        g['day'] = g['day'].where(start.isna() | (start.dt.tz_localize(None).dt.normalize() <= g['day']),
                                  start.dt.tz_localize(None).dt.normalize())
    g['run_margin'] = (g['home_score'] - g['away_score']).astype(float)
    # An official tie has no winner: it rates with a margin of 0 and is never a training or scored row.
    g['home_win'] = np.where(g['home_score'] == g['away_score'], np.nan,
                             (g['home_score'] > g['away_score']).astype(float))
    g['neutral_site'] = g['neutral_site'].astype(str).str.lower().isin(['true', '1'])
    return g.sort_values(['day', 'game_id'], kind='stable').reset_index(drop=True)


def run_ratings(train: pd.DataFrame, w: npt.NDArray[np.float64], alpha: float) -> tuple[float, dict[str, float]]:
    """(home edge, rating per club) from a weighted ridge fit of `run_margin = edge x home + r[home] - r[away]`, the
    home indicator 0 on a neutral-site game, penalising the club ratings only."""
    clubs = sorted(set(train['home']) | set(train['away']))
    idx = {c: i + 1 for i, c in enumerate(clubs)}
    n, k = len(train), len(clubs) + 1
    x = np.zeros((n, k))
    x[:, 0] = np.where(train['neutral_site'].to_numpy(bool), 0.0, 1.0)
    rows = np.arange(n)
    x[rows, train['home'].map(idx).to_numpy()] = 1.0
    x[rows, train['away'].map(idx).to_numpy()] = -1.0
    y = train['run_margin'].to_numpy(dtype=float)
    xtw = x.T * w
    penalty = np.full(k, alpha)
    penalty[0] = 0.0
    beta = np.linalg.solve(xtw @ x + np.diag(penalty), xtw @ y)
    return float(beta[0]), {c: float(beta[i]) for c, i in idx.items()}


def pitcher_totals(lines: pd.DataFrame, day_of: pd.Series, day: pd.Timestamp,
                   half_life: float) -> tuple[float, pd.DataFrame]:
    """(the league's runs per out, each pitcher's weighted runs `r` and outs `o`) from every appearance before
    `day`, starts and relief alike."""
    earlier = lines[lines['game_id'].map(day_of) < day]
    if earlier.empty:
        return 0.0, pd.DataFrame(columns=['r', 'o'])
    w = weights(earlier['game_id'].map(day_of), day, half_life)
    runs = earlier['runs'].to_numpy(float) * w
    outs = earlier['outs'].to_numpy(float) * w
    total_outs = float(outs.sum())
    league = float(runs.sum()) / total_outs if total_outs else 0.0
    per = pd.DataFrame({'p': earlier['pitcher_id'].to_numpy(), 'r': runs, 'o': outs}).groupby('p')[['r', 'o']].sum()
    return league, per


def shrunk(league: float, per: pd.DataFrame, k: float) -> dict[str, float]:
    """Each pitcher's rate per 27 outs, shrunk toward the league by `k` outs."""
    rate = (per['r'] + k * league) / (per['o'] + k) * OUTS_PER_GAME
    return {str(p): float(v) for p, v in rate.items()}


def pitcher_rates(lines: pd.DataFrame, day_of: pd.Series, day: pd.Timestamp, half_life: float,
                  k: float = SHRINK_OUTS) -> tuple[float, dict[str, float]]:
    """(the league's rate, each pitcher's rate shrunk by `k` outs) per 27 outs, from every appearance before
    `day`."""
    league, per = pitcher_totals(lines, day_of, day, half_life)
    if per.empty:
        return 0.0, {}
    return league * OUTS_PER_GAME, shrunk(league, per, k)


@dataclass(frozen=True)
class DayRatings:
    """Every club and pitcher rating as it stood before one game day."""
    runs: dict[str, float]
    league_rate: float
    pitchers: dict[str, float]

    def starter(self, pitcher: str | None) -> float:
        return self.pitchers.get(str(pitcher), self.league_rate) if pitcher else self.league_rate

    def matchup(self, home: str, away: str, home_starter: str | None, away_starter: str | None) -> dict[str, float]:
        return {'run_matchup': self.runs.get(home, 0.0) - self.runs.get(away, 0.0),
                'starter_matchup': self.starter(away_starter) - self.starter(home_starter)}


def day_ratings(train: pd.DataFrame, lines: pd.DataFrame, day_of: pd.Series, day: pd.Timestamp, half_life: float,
                alpha: float, k: float = SHRINK_OUTS) -> DayRatings:
    _, runs = run_ratings(train, weights(train['day'], day, half_life), alpha)
    league, pitchers = pitcher_rates(lines, day_of, day, half_life, k)
    return DayRatings(runs, league, pitchers)


def features(games: pd.DataFrame, lines: pd.DataFrame, half_life: float, alphas: list[float],
             shrinks: list[float] | None = None, last_day: str | None = None) -> pd.DataFrame:
    """One row per game with run_matchup_<lambda> for each lambda and starter_matchup_<K> for each K in `shrinks`
    (SHRINK_OUTS alone when None), each built only from games on earlier days. `games` is `prepare`d; `lines` is the
    history's pitchers table. Days after `last_day` are not rated."""
    shrinks = [SHRINK_OUTS] if shrinks is None else shrinks
    day_of = pd.Series(games['day'].to_numpy(), index=games['game_id'])
    lines = lines.assign(game_id=lines['game_id'].astype(str), pitcher_id=lines['pitcher_id'].astype(str))
    lines = lines[lines['game_id'].isin(day_of.index)]
    days = sorted(games['day'].unique())
    if last_day is not None:
        days = [d for d in days if d <= pd.Timestamp(last_day)]
    out = []
    for day in days:
        day = pd.Timestamp(day)
        train = games[games['day'] < day]
        if len(train) < MIN_TRAIN:
            continue
        w = weights(train['day'], day, half_life)
        runs = {a: run_ratings(train, w, a)[1] for a in alphas}
        league, per = pitcher_totals(lines, day_of, day, half_life)
        rated = {k: DayRatings({}, league * OUTS_PER_GAME, shrunk(league, per, k) if not per.empty else {})
                 for k in shrinks}
        for g in games[games['day'] == day].itertuples():
            row: dict[str, object] = {'game_id': g.game_id, 'day': day, 'season': g.season, 'game_type': g.game_type,
                                      'home': g.home, 'away': g.away, 'home_win': g.home_win,
                                      'neutral_site': g.neutral_site}
            for k in shrinks:
                row[f'starter_matchup_{k:g}'] = rated[k].starter(g.away_starter) - rated[k].starter(g.home_starter)
            for a in alphas:
                row[f'run_matchup_{a:g}'] = runs[a].get(g.home, 0.0) - runs[a].get(g.away, 0.0)
            out.append(row)
    return pd.DataFrame(out)
