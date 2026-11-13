"""NCAA tournament seeds for each tournament game (Stage 103 item 2).

"The higher seed wins" is the bracket's baseline, so every NCAA tournament game in the history needs both clubs'
seeds. ESPN's scoreboard gives no seed field; in an NCAA tournament game (`tournamentId` 22) a club's
`curatedRank.current` is its seed (docs/ncaam-data.md, the probe of 2026-11-13). This module re-reads the scoreboard
for each day the history holds a tournament game and writes `data/ncaam/history/seeds_<season>.csv`: one row per
tournament game, `game_id`, `home_seed`, `away_seed`.

It stops, naming each game, when a tournament game in the history is missing from the scoreboard, a seed is not
1 to 16, or a first-round game's two seeds do not add up to 17 (1 v 16, 8 v 9 and so on; a First Four game pairs
two equal seeds and is not a first-round game), or a finished tournament (its title game stored) does not
name exactly 32 first-round games (31 in 2021, whose VCU v Oregon game was a no-contest), or a club's seed differs between its games. In a First Four game, which pairs two equal seeds,
a side ESPN leaves unranked (99) takes its opponent's seed, and the row's `filled` names that side. The first
round is the round of 64: named "1st Round" from 2016,
"2nd Round" in 2011 to 2015, when the First Four was the first round.

Run by hand: python -m src.sports.ncaam.seeds 2014 2025
"""
from __future__ import annotations

import csv
import sys
import time
from collections.abc import Callable, Iterable
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from src.sports.ncaam.collector import HISTORY, CollectorError, day_board, fetch

NCAA = '22'
#: First-round games the tournament never played, by season.
NO_CONTEST = {2020: 1}  # 2021: VCU v Oregon, declared a no-contest under COVID-19 protocols
SEED_FIELDS = ('game_id', 'home_seed', 'away_seed', 'filled')


def round_of_64(note: str, season: int) -> bool:
    """Whether a tournament game's note names the round of 64 for its season (labelled by its starting year)."""
    name = '1st Round' if season >= 2015 else '2nd Round'
    return f'- {name}'.lower() in note.lower()  # 2015's notes are in capitals: "2nd ROUND"


def seeds_on(board: Any) -> dict[str, tuple[int | None, int | None]]:
    """(home seed, away seed) for each NCAA tournament game on one day's scoreboard."""
    out = {}
    for e in board.get('events') or []:
        comp = (e.get('competitions') or [{}])[0]
        if str(comp.get('tournamentId') or '') != NCAA:
            continue
        sides = {c.get('homeAway'): c for c in comp.get('competitors') or []}
        seed = {k: ((c.get('curatedRank') or {}).get('current')) for k, c in sides.items()}
        out[str(e.get('id'))] = (seed.get('home'), seed.get('away'))
    return out


def ok(seed: Any) -> bool:
    return isinstance(seed, int) and 1 <= seed <= 16


def check(games: pd.DataFrame, seeds: dict[str, tuple[int | None, int | None]], season: int) -> list[dict[str, Any]]:
    """Rows for `games` (the season's tournament games), or raise naming every game that fails a check."""
    rows, problems = [], []
    club_seed: dict[str, int] = {}
    first_round = sum(round_of_64(str(n), season) for n in games['note'])
    expected = 32 - NO_CONTEST.get(season, 0)
    finished = games['note'].str.lower().str.contains('national championship').any()
    if finished and first_round != expected:
        problems.append(f'{first_round} first-round games named, not {expected}')
    for g in games.itertuples():
        gid = str(g.game_id)
        if gid not in seeds:
            problems.append(f'game {gid}: not on the scoreboard')
            continue
        h, a = seeds[gid]
        filled = ''
        # A First Four game pairs two equal seeds, so a side ESPN leaves unranked (99) takes the other's.
        if 'first four' in str(g.note).lower() and ok(h) != ok(a):
            filled = 'home' if not ok(h) else 'away'
            h, a = (a, a) if filled == 'home' else (h, h)
        if not (ok(h) and ok(a)):
            problems.append(f'game {gid}: seeds {h} and {a}, not both 1 to 16')
            continue
        assert h is not None and a is not None
        if round_of_64(str(g.note), season) and h + a != 17:
            problems.append(f'game {gid}: a first-round game between seeds {h} and {a}')
            continue
        rows.append({'game_id': gid, 'home_seed': h, 'away_seed': a, 'filled': filled})
        for club, seed in ((g.home_id, h), (g.away_id, a)):
            if club_seed.setdefault(str(club), seed) != seed:
                problems.append(f'game {gid}: club {club} seeded {seed} here, {club_seed[str(club)]} before')
    if problems:
        raise CollectorError('; '.join(problems))
    return rows


def season_seeds(season: int, get: Callable[[str], bytes] = fetch, folder: Path = HISTORY,
                 pause: float = 0.2) -> list[dict[str, Any]]:
    g = pd.read_csv(folder / f'games_{season}.csv', dtype=str, keep_default_na=False)
    t = g[g['tournament_id'] == NCAA]
    found: dict[str, tuple[int | None, int | None]] = {}
    for day in sorted(t['day'].unique()):
        found.update(seeds_on(day_board(date.fromisoformat(day), get)))
        if pause:
            time.sleep(pause)
    return check(t, found, season)


def write(rows: Iterable[dict[str, Any]], path: Path) -> None:
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(SEED_FIELDS), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def main(argv: Iterable[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    first, last = int(args[0]), int(args[1] if len(args) > 1 else args[0])
    for season in range(first, last + 1):
        rows = season_seeds(season)
        write(rows, HISTORY / f'seeds_{season}.csv')
        print(f'{season}: {len(rows)} tournament games seeded')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
