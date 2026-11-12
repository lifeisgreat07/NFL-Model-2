"""MLB's starting pitchers, probable and confirmed, stored per game with where and when each was read (Stage 98
item 3).

Model A's starter term (experiments/mlb/stage98/registry.json) reads the box score's starter in the backtest and the
Stats API's probable pitcher live, and measurement M2 compares the two over the forward test. So each read is kept
as a row, never overwritten:

- `probable_rows`: from one day's schedule (`schedule.DAY`, hydrated with `probablePitcher`), each club's named
  probable, or a row with no pitcher where a club has not named one yet, so a later read that names one shows when
  it was first known;
- `confirmed_rows`: from a final game's box score, each club's first listed pitcher, the starter.

Each row says what was read (`kind`), from which address (`source`) and when (`read_at`, UTC). `append` adds rows to
a CSV and keeps every earlier one: a row that repeats the last read of the same game, club and kind (same pitcher) is
not added again, so a run every few hours stores only changes.
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.sports.mlb import schedule

FIELDS = ('game_id', 'side', 'club', 'kind', 'pitcher_id', 'source', 'read_at')
KINDS = ('probable', 'confirmed')
BOX = schedule.STATS + '/game/{gid}/boxscore'

Json = Any


class StarterError(ValueError):
    """A read this file will not guess about."""


def _stamp(read_at: datetime) -> str:
    if read_at.tzinfo is None:
        raise StarterError('read_at must carry its time zone')
    return str(pd.Timestamp(read_at).tz_convert('UTC').isoformat())


def probable_rows(day: Json, source: str, read_at: datetime) -> list[dict[str, Any]]:
    """One row per club per game of a day's schedule: its probable pitcher's Stats API id, or None."""
    stamp = _stamp(read_at)
    rows = []
    for g in schedule.last_listings(schedule.games_of(day)):
        if g.get('gameType') not in schedule.GAME_TYPES:
            continue
        for side in ('home', 'away'):
            t = (g.get('teams') or {}).get(side) or {}
            club = (t.get('team') or {}).get('id')
            if not isinstance(club, int):
                raise StarterError(f"game {g.get('gamePk')}: no {side} club")
            pid = (t.get('probablePitcher') or {}).get('id')
            rows.append({'game_id': str(g['gamePk']), 'side': side, 'club': str(club), 'kind': 'probable',
                         'pitcher_id': str(pid) if pid is not None else None, 'source': source, 'read_at': stamp})
    return rows


def confirmed_rows(box: Json, game_id: str, source: str, read_at: datetime) -> list[dict[str, Any]]:
    """Each club's starter in a final game's box score: the first pitcher it lists. Raises when a club lists none."""
    stamp = _stamp(read_at)
    teams = (box or {}).get('teams') or {}
    rows = []
    for side in ('home', 'away'):
        t = teams.get(side) or {}
        club = (t.get('team') or {}).get('id')
        pitchers = t.get('pitchers') or []
        if not isinstance(club, int) or not pitchers:
            raise StarterError(f'game {game_id}: the {side} box lists no club or no pitcher')
        rows.append({'game_id': str(game_id), 'side': side, 'club': str(club), 'kind': 'confirmed',
                     'pitcher_id': str(pitchers[0]), 'source': source, 'read_at': stamp})
    return rows


def read(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=list(FIELDS))
    return pd.read_csv(path, dtype=str, keep_default_na=False).replace({'': None})


def append(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    """Add the rows that change what the file last said for their game, club and kind; earlier rows are never
    touched. Returns how many were added."""
    old = read(path)
    last: dict[tuple[str, str, str], Any] = {}
    for r in old.itertuples(index=False):
        last[(r.game_id, r.side, r.kind)] = r.pitcher_id
    new = []
    for r in rows:
        if r['kind'] not in KINDS:
            raise StarterError(f"unknown kind {r['kind']!r}")
        key = (r['game_id'], r['side'], r['kind'])
        if key in last and last[key] == r['pitcher_id']:
            continue
        last[key] = r['pitcher_id']
        new.append({k: r[k] for k in FIELDS})
    if new:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame(new, columns=list(FIELDS))
        frame.to_csv(path, mode='a', header=not path.exists(), index=False, lineterminator='\n')
    return len(new)
