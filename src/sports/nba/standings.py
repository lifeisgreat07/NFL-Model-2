"""The NBA's standings odds: the rest of the regular season simulated from
each game's home-win probability, then the play-in (Stage 104 item 4).

The NBA's rules, as the simulation applies them:

- each conference's 15 clubs are seeded by win percentage;
- seeds 1 to 6 go straight to the playoffs; seeds 7 to 10 play in: 7 hosts
  8 and its winner is the seventh seed; 9 hosts 10 and its loser is out;
  the loser of 7 v 8 hosts the winner of 9 v 10, and that game's winner is
  the eighth seed;
- a tie in win percentage is broken by the tied clubs' win percentage in
  games among themselves, then by win percentage against their own
  conference, then by drawing lots. The league's further steps (division
  winner, records against playoff clubs, point differential) are left out:
  the draw is said aloud rather than hidden.

Design choices, stated rather than buried, as the NHL's simulation states its
own (`src/sports/nhl/standings.py`):

- A finished game keeps its real result.
- An unplayed game, and each play-in game, is decided by Model A's home-win
  probability without its availability term, with today's ratings held
  fixed: who will be available weeks ahead is not known, so the model the
  daily run fits for a pick made without the injury report is the one used.
  The higher seed hosts a play-in game.
- Probabilities are held fixed for the rest of the season: real clubs change,
  so a projection far ahead is less sure than the numbers show. Early in the
  season a share of 0% or 100% means only that no simulated season, played
  with today's ratings, went the other way.
- Only the games the schedule lists are played. Each club's last two games
  are set by the NBA Cup's group stage and are listed once the league sets
  them, so until then projected wins count 80 games, not 82. The Cup final,
  which ESPN lists as a regular-season game and the league does not count,
  is counted here if it is listed: one game for two clubs, in December.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd

#: The 2026-27 conferences, in ESPN's codes.
CONFERENCES: Mapping[str, tuple[str, ...]] = {
    'East': ('ATL', 'BKN', 'BOS', 'CHA', 'CHI', 'CLE', 'DET', 'IND', 'MIA', 'MIL', 'NY', 'ORL', 'PHI', 'TOR', 'WSH'),
    'West': ('DAL', 'DEN', 'GS', 'HOU', 'LAC', 'LAL', 'MEM', 'MIN', 'NO', 'OKC', 'PHX', 'POR', 'SA', 'SAC', 'UTAH'),
}
TEAM_CONFERENCE = {t: c for c, teams in CONFERENCES.items() for t in teams}
DIRECT = 6
PLAY_IN = 4


def seed(teams: Sequence[str], wins: Mapping[str, float], played: Mapping[str, float],
         h2h: Callable[[str, str], float], conf_wins: Mapping[str, float], conf_played: Mapping[str, float],
         lots: Mapping[str, float]) -> list[str]:
    """One conference's clubs, best seed first, by the rules in the module's
    docstring. `h2h(a, b)` is a's wins over b."""
    def pct(w: float, n: float) -> float:
        return w / n if n else 0.0

    order = sorted(teams, key=lambda t: pct(wins[t], played[t]), reverse=True)
    out: list[str] = []
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and pct(wins[order[j + 1]], played[order[j + 1]]) == pct(wins[order[i]], played[order[i]]):
            j += 1
        tied = order[i:j + 1]
        if len(tied) > 1:
            def among(t: str, group: list[str] = tied) -> float:
                won = sum(h2h(t, o) for o in group if o != t)
                lost = sum(h2h(o, t) for o in group if o != t)
                return pct(won, won + lost)
            tied = sorted(tied, key=lambda t: (among(t), pct(conf_wins[t], conf_played[t]), lots[t]), reverse=True)
        out.extend(tied)
        i = j + 1
    return out


def play_in(seeds: Sequence[str], home_prob: Mapping[tuple[str, str], float],
            rng: np.random.Generator) -> tuple[str, str]:
    """(the seventh seed, the eighth) from seeds 7 to 10, by the play-in's
    three games, the higher seed at home."""
    s7, s8, s9, s10 = seeds[DIRECT:DIRECT + PLAY_IN]

    def game(home: str, away: str) -> tuple[str, str]:
        return (home, away) if rng.random() < home_prob[(home, away)] else (away, home)

    seventh, loser78 = game(s7, s8)
    winner910, _ = game(s9, s10)
    eighth, _ = game(loser78, winner910)
    return seventh, eighth


def simulate(schedule: pd.DataFrame, home_prob: Mapping[str, float], pair_prob: Mapping[tuple[str, str], float],
             n_sim: int = 10000, seed_: int = 20261111) -> pd.DataFrame:
    """Every club's odds over the rest of the regular season of `schedule`
    (the NBA schedule frame). `home_prob` maps an unplayed game's id to its
    home-win probability, `pair_prob` any (home, away) pair's, for the
    play-in. Returns one row per club: team, conference, wins and losses
    now, projected wins, and the shares of seasons in the top six, in the
    play-in (seeds 7 to 10) and in the playoffs, sorted by projected wins."""
    reg = schedule[schedule['game_type'] == 'regular']
    unknown = sorted((set(reg['home']) | set(reg['away'])) - set(TEAM_CONFERENCE))
    if unknown:
        raise ValueError(f'clubs in no conference: {unknown}')
    teams = sorted(set(reg['home']) | set(reg['away']))
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    final = reg[reg['status'] == 'final']
    left = reg[~reg['status'].isin(['final', 'cancelled'])]
    missing = sorted(set(left['game_id'].astype(str)) - set(home_prob))
    if missing:
        raise ValueError(f'{len(missing)} unplayed game(s) have no probability, e.g. {missing[:3]}')

    base_h2h = np.zeros((n, n))
    for _, g in final.iterrows():
        home_won = float(g['home_score']) > float(g['away_score'])
        w, lo = (idx[g['home']], idx[g['away']]) if home_won else (idx[g['away']], idx[g['home']])
        base_h2h[w, lo] += 1
    hi = left['home'].map(idx).to_numpy()
    ai = left['away'].map(idx).to_numpy()
    p = left['game_id'].astype(str).map(home_prob).to_numpy(dtype=float)
    conf = np.array([TEAM_CONFERENCE[t] for t in teams])
    same = conf[:, None] == conf[None, :]
    rng = np.random.default_rng(seed_)
    top6, playin, playoff, wins_sum = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    for _ in range(n_sim):
        hw = rng.random(len(p)) < p
        h2h = base_h2h.copy()
        np.add.at(h2h, (np.where(hw, hi, ai), np.where(hw, ai, hi)), 1)
        wins = h2h.sum(axis=1)
        played = wins + h2h.sum(axis=0)
        cw = (h2h * same).sum(axis=1)
        cp = cw + (h2h * same).sum(axis=0)
        wins_sum += wins
        lots = {t: rng.random() for t in teams}
        def pair(a: str, b: str, m: npt.NDArray[np.float64] = h2h) -> float:
            return float(m[idx[a], idx[b]])
        w_ = dict(zip(teams, wins, strict=True))
        pl_ = dict(zip(teams, played, strict=True))
        cw_ = dict(zip(teams, cw, strict=True))
        cp_ = dict(zip(teams, cp, strict=True))
        for clubs in CONFERENCES.values():
            ranked = seed([t for t in clubs if t in idx], w_, pl_, pair, cw_, cp_, lots)
            for t in ranked[:DIRECT]:
                top6[idx[t]] += 1
                playoff[idx[t]] += 1
            for t in ranked[DIRECT:DIRECT + PLAY_IN]:
                playin[idx[t]] += 1
            if len(ranked) >= DIRECT + PLAY_IN:
                for t in play_in(ranked, pair_prob, rng):
                    playoff[idx[t]] += 1
    now = base_h2h.sum(axis=1), base_h2h.sum(axis=0)
    out = pd.DataFrame({
        'team': teams, 'conference': conf, 'wins_now': now[0].astype(int), 'losses_now': now[1].astype(int),
        'projected_wins': wins_sum / n_sim, 'top6_pct': top6 / n_sim, 'playin_pct': playin / n_sim,
        'playoff_pct': playoff / n_sim,
    })
    return out.sort_values(['projected_wins', 'team'], ascending=[False, True]).reset_index(drop=True)


def games_listed(schedule: pd.DataFrame) -> tuple[int, int]:
    """(fewest, most) regular-season games the schedule lists for a club."""
    reg = schedule[schedule['game_type'] == 'regular']
    counts = pd.concat([reg['home'], reg['away']]).value_counts()
    return int(counts.min()), int(counts.max())


def to_json(table: pd.DataFrame, as_of: str, n_sim: int, listed: tuple[int, int]) -> dict[str, Any]:
    """The file the NBA's standings page reads."""
    return {
        'as_of': as_of, 'simulations': n_sim, 'games_listed': list(listed),
        'teams': [{'team': r.team, 'conference': r.conference, 'wins_now': int(r.wins_now),
                   'losses_now': int(r.losses_now), 'projected_wins': round(float(r.projected_wins), 1),
                   'top6_pct': round(float(r.top6_pct), 4), 'playin_pct': round(float(r.playin_pct), 4),
                   'playoff_pct': round(float(r.playoff_pct), 4)} for r in table.itertuples()],
    }
