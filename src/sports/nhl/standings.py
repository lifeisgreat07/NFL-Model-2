"""The NHL's standings odds: the rest of the regular season simulated from
each game's home-win probability (Stage 57 item 3).

The NHL's rules, as the simulation applies them:

- a win is two points; a loss in overtime or a shootout is one; a loss in
  regulation is none;
- each conference sends eight teams: the top three of each of its two
  divisions, then the two best of the rest (the wild cards);
- ties in points are broken by regulation wins, then by regulation and
  overtime wins (not shootout), then by drawing lots. The league's further
  steps (points in head-to-head games, goal differential and on) are left
  out: a tie that survives the first two is rare, and the draw is said
  aloud rather than hidden.

Design choices, stated rather than buried, as the NFL's simulation states
its own (`src/sports/nfl/simulate_season.py`):

- A finished game keeps its real result, overtime and shootout included.
- An unplayed game is decided by its home-win probability, then goes to
  overtime with the share of recent games that did (`overtime_share`), and
  if it does, a shootout with the share of overtime games that did. Who
  wins does not depend on whether it went past regulation: the model gives
  one probability for the game.
- Probabilities are held fixed for the rest of the season: real teams
  change, and a projection far ahead is less sure than the numbers show.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd

#: The 2026-27 divisions and conferences.
DIVISIONS: Mapping[str, tuple[str, ...]] = {
    'Atlantic': ('BOS', 'BUF', 'DET', 'FLA', 'MTL', 'OTT', 'TBL', 'TOR'),
    'Metropolitan': ('CAR', 'CBJ', 'NJD', 'NYI', 'NYR', 'PHI', 'PIT', 'WSH'),
    'Central': ('CHI', 'COL', 'DAL', 'MIN', 'NSH', 'STL', 'UTA', 'WPG'),
    'Pacific': ('ANA', 'CGY', 'EDM', 'LAK', 'SEA', 'SJS', 'VAN', 'VGK'),
}
CONFERENCES: Mapping[str, tuple[str, ...]] = {
    'Eastern': ('Atlantic', 'Metropolitan'),
    'Western': ('Central', 'Pacific'),
}
TEAM_DIVISION = {t: d for d, teams in DIVISIONS.items() for t in teams}
TEAM_CONFERENCE = {t: c for c, divs in CONFERENCES.items() for d in divs for t in DIVISIONS[d]}

DIVISION_SPOTS = 3
WILD_CARDS = 2


def overtime_share(games: pd.DataFrame) -> tuple[float, float]:
    """(share of final games that went past regulation, share of those that
    went to a shootout), from games with `last_period` 'REG', 'OT' or 'SO'."""
    done = games[games['last_period'].isin(['REG', 'OT', 'SO'])]
    if done.empty:
        raise ValueError('no finished games to measure overtime from')
    past = done['last_period'] != 'REG'
    shootout = (done.loc[past, 'last_period'] == 'SO').mean() if past.any() else 0.0
    return float(past.mean()), float(shootout)


def _points(home_win: npt.NDArray[np.bool_], period: npt.NDArray[np.int_]
            ) -> tuple[npt.NDArray[np.int_], npt.NDArray[np.int_]]:
    """Home and away points for each game: 2 to the winner, 1 to a loser
    past regulation."""
    beyond = period != 0
    home = np.where(home_win, 2, np.where(beyond, 1, 0))
    away = np.where(~home_win, 2, np.where(beyond, 1, 0))
    return home, away


def playoff_teams(points: Mapping[str, float], rw: Mapping[str, float], row: Mapping[str, float],
                  rng: np.random.Generator) -> tuple[set[str], set[str]]:
    """(the 16 playoff teams, the 4 division winners) for one finished season,
    by the rules in the module's docstring."""
    lots = {t: rng.random() for t in points}

    def order(teams: list[str]) -> list[str]:
        return sorted(teams, key=lambda t: (points[t], rw[t], row[t], lots[t]), reverse=True)

    playoff: set[str] = set()
    winners: set[str] = set()
    for divs in CONFERENCES.values():
        rest: list[str] = []
        for d in divs:
            ranked = order([t for t in DIVISIONS[d] if t in points])
            playoff.update(ranked[:DIVISION_SPOTS])
            if ranked:
                winners.add(ranked[0])
            rest.extend(ranked[DIVISION_SPOTS:])
        playoff.update(order(rest)[:WILD_CARDS])
    return playoff, winners


def simulate(schedule: pd.DataFrame, home_prob: Mapping[str, float], ot: tuple[float, float],
             n_sim: int = 10000, seed: int = 20261006) -> pd.DataFrame:
    """Playoff and division odds for every team in the regular season of
    `schedule` (the NHL schedule frame). `home_prob` maps an unplayed game's
    id to its home-win probability; a final game keeps its result, and a
    cancelled one counts for nobody. Returns one row per team: team,
    division, conference, points now, mean projected points, playoff_pct and
    division_pct, sorted by projected points."""
    reg = schedule[schedule['game_type'] == 'regular']
    unknown = sorted((set(reg['home']) | set(reg['away'])) - set(TEAM_DIVISION))
    if unknown:
        raise ValueError(f'teams in no division: {unknown}')
    teams = sorted(set(reg['home']) | set(reg['away']))
    idx = {t: i for i, t in enumerate(teams)}
    final = reg[reg['status'] == 'final']
    left = reg[~reg['status'].isin(['final', 'cancelled'])]
    missing = sorted(set(left['game_id']) - set(home_prob))
    if missing:
        raise ValueError(f'{len(missing)} unplayed game(s) have no probability, e.g. {missing[:3]}')

    n = len(teams)
    base_pts, base_rw, base_row = np.zeros(n), np.zeros(n), np.zeros(n)
    for _, g in final.iterrows():
        h, a = idx[g['home']], idx[g['away']]
        hw = bool(g['home_win'])
        period = {'REG': 0, 'OT': 1, 'SO': 2}[g['last_period']]
        winner, loser = (h, a) if hw else (a, h)
        base_pts[winner] += 2
        base_pts[loser] += 1 if period else 0
        base_rw[winner] += 1 if period == 0 else 0
        base_row[winner] += 1 if period < 2 else 0

    rng = np.random.default_rng(seed)
    hi = left['home'].map(idx).to_numpy()
    ai = left['away'].map(idx).to_numpy()
    p = left['game_id'].map(home_prob).to_numpy(dtype=float)
    p_ot, p_so = ot
    playoff_n, division_n, pts_sum = np.zeros(n), np.zeros(n), np.zeros(n)
    for _ in range(n_sim):
        hw = rng.random(len(p)) < p
        beyond = rng.random(len(p)) < p_ot
        so = beyond & (rng.random(len(p)) < p_so)
        periods = np.where(so, 2, np.where(beyond, 1, 0))
        hp, ap = _points(hw, periods)
        pts, rw, row = base_pts.copy(), base_rw.copy(), base_row.copy()
        np.add.at(pts, hi, hp)
        np.add.at(pts, ai, ap)
        win_idx = np.where(hw, hi, ai)
        np.add.at(rw, win_idx[periods == 0], 1)
        np.add.at(row, win_idx[periods < 2], 1)
        made, won = playoff_teams(dict(zip(teams, pts, strict=True)), dict(zip(teams, rw, strict=True)),
                                  dict(zip(teams, row, strict=True)), rng)
        for t in made:
            playoff_n[idx[t]] += 1
        for t in won:
            division_n[idx[t]] += 1
        pts_sum += pts
    out = pd.DataFrame({
        'team': teams,
        'division': [TEAM_DIVISION[t] for t in teams],
        'conference': [TEAM_CONFERENCE[t] for t in teams],
        'points_now': base_pts.astype(int),
        'projected_points': pts_sum / n_sim,
        'playoff_pct': playoff_n / n_sim,
        'division_pct': division_n / n_sim,
    })
    return out.sort_values(['projected_points', 'team'], ascending=[False, True]).reset_index(drop=True)


def unplayed_probabilities(schedule: pd.DataFrame, matchup: Callable[[str, str], Mapping[str, float]],
                           model: Any, columns: list[str]) -> dict[str, float]:
    """Each unplayed regular-season game's home-win probability from Model
    A, with today's ratings held fixed. `matchup(home, away)` gives a game's
    features; a future game's starting goalies are not known, so the caller
    passes no goalie and the goalie term is the league average's, 0."""
    reg = schedule[(schedule['game_type'] == 'regular')
                   & ~schedule['status'].isin(['final', 'cancelled'])]
    if reg.empty:
        return {}
    x = pd.DataFrame([dict(matchup(h, a)) for h, a in zip(reg['home'], reg['away'], strict=True)])[columns]
    p = model.predict_proba(x)[:, 1]
    return {str(gid): float(v) for gid, v in zip(reg['game_id'], p, strict=True)}


def to_json(table: pd.DataFrame, as_of: str, n_sim: int, ot: tuple[float, float]) -> dict[str, Any]:
    """The file the NHL's standings page reads."""
    return {
        'as_of': as_of, 'simulations': n_sim,
        'overtime_share': round(ot[0], 4), 'shootout_share_of_overtime': round(ot[1], 4),
        'teams': [{'team': r.team, 'division': r.division, 'conference': r.conference,
                   'points_now': int(r.points_now), 'projected_points': round(float(r.projected_points), 1),
                   'playoff_pct': round(float(r.playoff_pct), 4), 'division_pct': round(float(r.division_pct), 4)}
                  for r in table.itertuples()],
    }
