"""MLB's standings odds: the rest of the regular season simulated from each
game's home-win probability, then MLB's playoff field (Stage 100 item 3).

MLB's rules, as the simulation applies them (the 12-club field used since
2022):

- each league's 15 clubs play in three divisions of five, and standings go
  by winning percentage: an official tie is neither a win nor a loss;
- six clubs from each league reach the postseason: the three division
  winners, seeded 1 to 3 by record, then the three best of the rest (the
  wild cards), seeded 4 to 6. Seeds 1 and 2 have a bye past the Wild Card
  Series;
- no tie is played off (there is no "Game 163" since 2022). Two clubs tied
  are separated by their head-to-head record, then by each club's record
  within its own division (even when the two are in different divisions),
  then by its record within its league. Three or more clubs tied: a club
  with a better record against each of the others goes first; otherwise the
  best record in games among the tied clubs, then within the division, then
  within the league. Whenever a step leaves fewer clubs level than it
  started with, those clubs start again under the rules for their number,
  so two clubs left level go back to their head-to-head record. A tie for
  more than one place, seeding included, is settled one place at a time by
  the same rules (MLB's own text says the three-club rules order a tie for
  two or three places).

What is left out, said aloud rather than hidden: the league's last steps,
the record in intraleague games after the All-Star break and then one game
further back at a time. This pipeline does not keep the All-Star game, so a
tie that survives the record within the league goes to drawing lots.

Design choices, stated as the NHL's and NBA's simulations state their own
(`src/sports/nhl/standings.py`, `src/sports/nba/standings.py`):

- A finished game keeps its real result.
- Probabilities are given to the simulation, one per unplayed game; which
  model supplies them is decided with MLB's daily run (Stage 101). A game
  weeks ahead has no announced starter, so whatever supplies them cannot
  lean on one.
- Probabilities are held fixed for the rest of the season: real clubs
  change, so a projection far ahead is less sure than the numbers show.
  Early in the season a share of 0% or 100% means only that no simulated
  season, played with these probabilities, went the other way.
- Only the games the schedule lists are played, so a shortened season is
  simulated as listed rather than as 162 games.
- Only the field is simulated, not the rounds after it. Which club meets
  which in October is under negotiation for 2027 (MLB's proposal lets the
  top seeds pick their opponents), while the six places and the byes are not.

Clubs are the Stats API's ids as text, as the schedule writes them
(`src/sports/mlb/schedule.py`); `src/sports/mlb/teams.py` names them.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd

#: The divisions since 2013 (Houston's move to the AL), as the Stats API lists them for 2026 and 2027, by club id.
DIVISIONS: Mapping[str, tuple[str, ...]] = {
    'AL East': ('110', '111', '139', '141', '147'),
    'AL Central': ('114', '116', '118', '142', '145'),
    'AL West': ('108', '117', '133', '136', '140'),
    'NL East': ('120', '121', '143', '144', '146'),
    'NL Central': ('112', '113', '134', '138', '158'),
    'NL West': ('109', '115', '119', '135', '137'),
}
LEAGUES: Mapping[str, tuple[str, ...]] = {
    'AL': ('AL East', 'AL Central', 'AL West'),
    'NL': ('NL East', 'NL Central', 'NL West'),
}
TEAM_DIVISION = {t: d for d, teams in DIVISIONS.items() for t in teams}
TEAM_LEAGUE = {t: lg for lg, divs in LEAGUES.items() for d in divs for t in DIVISIONS[d]}
LEAGUE_CLUBS = {lg: tuple(t for d in divs for t in DIVISIONS[d]) for lg, divs in LEAGUES.items()}

#: Each league's field: three division winners, three wild cards, the top two seeds with a bye.
WILD_CARDS = 3
BYES = 2


def _pct(won: float, lost: float) -> float:
    return won / (won + lost) if won + lost else 0.0


class Record:
    """One season's results between clubs: `h2h[i, j]` is club i's wins over club j."""

    def __init__(self, h2h: npt.NDArray[np.float64], idx: Mapping[str, int]) -> None:
        self.h2h = h2h
        self.idx = idx

    def won(self, a: str, b: str) -> float:
        return float(self.h2h[self.idx[a], self.idx[b]])

    def pct(self, t: str) -> float:
        i = self.idx[t]
        return _pct(float(self.h2h[i].sum()), float(self.h2h[:, i].sum()))

    def pct_against(self, t: str, clubs: Sequence[str]) -> float:
        others = [c for c in clubs if c != t]
        return _pct(sum(self.won(t, c) for c in others), sum(self.won(c, t) for c in others))

    def division_pct(self, t: str) -> float:
        return self.pct_against(t, DIVISIONS[TEAM_DIVISION[t]])

    def league_pct(self, t: str) -> float:
        return self.pct_against(t, LEAGUE_CLUBS[TEAM_LEAGUE[t]])


def best(tied: Sequence[str], rec: Record, lots: Mapping[str, float]) -> str:
    """The club that takes the one place a group level on record is playing for, by the rules in the module's
    docstring."""
    group = list(tied)
    if len(group) == 1:
        return group[0]
    over_each = [t for t in group if all(rec.won(t, o) > rec.won(o, t) for o in group if o != t)]
    if over_each:
        return over_each[0]
    steps: list[Callable[[str], float]] = [
        lambda t: rec.pct_against(t, group), rec.division_pct, rec.league_pct, lambda t: lots[t]]
    for step in steps:
        value = {t: step(t) for t in group}
        top = max(value.values())
        leaders = [t for t in group if value[t] == top]
        if len(leaders) == 1:
            return leaders[0]
        if len(leaders) < len(group):
            return best(leaders, rec, lots)
    raise ValueError(f'no draw separates {group}')


def ordered(clubs: Sequence[str], rec: Record, lots: Mapping[str, float]) -> list[str]:
    """Clubs best first: by winning percentage, each level group settled one place at a time by `best`."""
    rest = sorted(clubs, key=rec.pct, reverse=True)
    out: list[str] = []
    while rest:
        level = [t for t in rest if rec.pct(t) == rec.pct(rest[0])]
        while level:
            first = best(level, rec, lots)
            out.append(first)
            level.remove(first)
            rest.remove(first)
    return out


def seeds(league: str, rec: Record, lots: Mapping[str, float]) -> list[str]:
    """One league's six postseason clubs, seed 1 first: the division winners by record, then the wild cards."""
    winners = []
    for division in LEAGUES[league]:
        clubs = DIVISIONS[division]
        top = max(rec.pct(t) for t in clubs)
        winners.append(best([t for t in clubs if rec.pct(t) == top], rec, lots))
    rest = [t for t in LEAGUE_CLUBS[league] if t not in winners]
    return ordered(winners, rec, lots) + ordered(rest, rec, lots)[:WILD_CARDS]


def results(games: pd.DataFrame, idx: Mapping[str, int]) -> npt.NDArray[np.float64]:
    """The head-to-head wins of finished games with a winner (an official tie counts for neither club)."""
    h2h = np.zeros((len(idx), len(idx)))
    hs = pd.to_numeric(games['home_score']).to_numpy(dtype=float)
    as_ = pd.to_numeric(games['away_score']).to_numpy(dtype=float)
    hi = games['home'].astype(str).map(idx).to_numpy()
    ai = games['away'].astype(str).map(idx).to_numpy()
    home_won, away_won = hs > as_, as_ > hs
    np.add.at(h2h, (hi[home_won], ai[home_won]), 1)
    np.add.at(h2h, (ai[away_won], hi[away_won]), 1)
    return h2h


def simulate(schedule: pd.DataFrame, home_prob: Mapping[str, float], n_sim: int = 10000,
             seed_: int = 20261123) -> pd.DataFrame:
    """Every club's odds over the rest of the regular season of `schedule` (the MLB schedule frame).
    `home_prob` maps each unplayed game's id to its home-win probability. Returns one row per club: club, league,
    division, wins and losses now, projected wins, and the shares of seasons winning the division, with a bye,
    as a wild card and in the postseason, sorted by projected wins."""
    reg = schedule[schedule['game_type'] == 'regular']
    clubs_listed = set(reg['home'].astype(str)) | set(reg['away'].astype(str))
    unknown = sorted(clubs_listed - set(TEAM_DIVISION))
    if unknown:
        raise ValueError(f'clubs in no division: {unknown}')
    absent = sorted(set(TEAM_DIVISION) - clubs_listed)
    if absent:
        raise ValueError(f'clubs with no regular-season game listed: {absent}')
    teams = sorted(clubs_listed)
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    final = reg[reg['status'] == 'final']
    left = reg[~reg['status'].isin(['final', 'cancelled'])]
    missing = sorted(set(left['game_id'].astype(str)) - set(home_prob))
    if missing:
        raise ValueError(f'{len(missing)} unplayed game(s) have no probability, e.g. {missing[:3]}')
    base = results(final, idx)
    hi = left['home'].astype(str).map(idx).to_numpy()
    ai = left['away'].astype(str).map(idx).to_numpy()
    p = left['game_id'].astype(str).map(home_prob).to_numpy(dtype=float)
    rng = np.random.default_rng(seed_)
    division, bye, wild, field, wins_sum = (np.zeros(n) for _ in range(5))
    for _ in range(n_sim):
        hw = rng.random(len(p)) < p
        h2h = base.copy()
        np.add.at(h2h, (np.where(hw, hi, ai), np.where(hw, ai, hi)), 1)
        wins_sum += h2h.sum(axis=1)
        rec = Record(h2h, idx)
        lots = {t: float(rng.random()) for t in teams}
        for league in LEAGUES:
            top = seeds(league, rec, lots)
            for place, t in enumerate(top):
                i = idx[t]
                field[i] += 1
                if place < len(LEAGUES[league]):
                    division[i] += 1
                else:
                    wild[i] += 1
                if place < BYES:
                    bye[i] += 1
    out = pd.DataFrame({
        'team': teams, 'league': [TEAM_LEAGUE[t] for t in teams], 'division': [TEAM_DIVISION[t] for t in teams],
        'wins_now': base.sum(axis=1).astype(int), 'losses_now': base.sum(axis=0).astype(int),
        'projected_wins': wins_sum / n_sim, 'division_pct': division / n_sim, 'bye_pct': bye / n_sim,
        'wildcard_pct': wild / n_sim, 'playoff_pct': field / n_sim,
    })
    return out.sort_values(['projected_wins', 'team'], ascending=[False, True]).reset_index(drop=True)


def games_listed(schedule: pd.DataFrame) -> tuple[int, int]:
    """(fewest, most) regular-season games the schedule lists for a club."""
    reg = schedule[schedule['game_type'] == 'regular']
    counts = pd.concat([reg['home'], reg['away']]).astype(str).value_counts()
    return int(counts.min()), int(counts.max())


def to_json(table: pd.DataFrame, as_of: str, n_sim: int, listed: tuple[int, int]) -> dict[str, Any]:
    """The file MLB's standings page will read."""
    return {
        'as_of': as_of, 'simulations': n_sim, 'games_listed': list(listed),
        'teams': [{'team': r.team, 'league': r.league, 'division': r.division, 'wins_now': int(r.wins_now),
                   'losses_now': int(r.losses_now), 'projected_wins': round(float(r.projected_wins), 1),
                   'division_pct': round(float(r.division_pct), 4), 'bye_pct': round(float(r.bye_pct), 4),
                   'wildcard_pct': round(float(r.wildcard_pct), 4), 'playoff_pct': round(float(r.playoff_pct), 4)}
                  for r in table.itertuples()],
    }
