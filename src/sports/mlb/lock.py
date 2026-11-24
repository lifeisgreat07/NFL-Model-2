"""When an MLB pick is saved: each game on its own, at the last run at least an hour before its first pitch.

Stage 101 item 3, as registered in `experiments/mlb/stage101/registry.json` (`forward_test.runs.lock`). The rule is
the NBA's and the NHL's (`src/sports/nba/lock.py`): a game is saved by the last scheduled run before its listed
start with an hour of slack, and a game already under way is never predicted. The sports keep their own copies so
neither reads the other's code.

`GameLock.decide(slate, now)` answers for one run, in the core's words (`src.core.sport.LockDecision`):

- **lock**: scheduled games that start before the next run plus `SLACK`;
- **started**: games already under way or over (the start has passed, or the Stats API says so). Never predicted;
- **hold**: scheduled games a later run can still save in time.

A postponed, suspended or cancelled game is in none of the three. A postponed game is listed again on the day it is
played, as a scheduled game of that date, and is decided then.

A game whose start the league has not set (`start_time_tbd`, as for game 2 of a traditional doubleheader, whose
listed time is a placeholder or an estimate) is saved by the run that saves the other game of its doubleheader: it
locks when that game locks, and at once if that game has already started. With no such game to follow (no other
game of the same two clubs that day, or that game postponed or cancelled), it is decided by its placeholder time like
any other game.

The run times are not written here. They are chosen once, before the first pick, by the registered rule from spring
training's measurement (`src/sports/mlb/probables_timing.py`), and read from the file that rule writes,
`experiments/mlb/stage101/probables_timing.json` (`times_utc`). Until that file exists no run can be placed, and
`decide` stops with `MLBLockError` rather than guess times: a pick saved at a time the rule did not choose is not the
registered forward test.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from src.core.sport import GameStatus, LockDecision, LockUnit, sport_paths

#: Where the registered rule writes the run times (`probables_timing.CHOSEN`).
RUN_TIMES = sport_paths('mlb').root / 'experiments' / 'mlb' / 'stage101' / 'probables_timing.json'

#: How late a run may start and still be trusted to save a game in time.
SLACK = timedelta(hours=1)

Runs = tuple[tuple[int, int, int], ...]


class MLBLockError(RuntimeError):
    """No run times to lock by."""


def registered_runs(path: Path = RUN_TIMES) -> Runs:
    """(weekday Mon=0, hour, minute) UTC for every day, from the times the registered rule chose."""
    if not path.exists():
        raise MLBLockError(f'MLB run times are not set: {path.name} is written by '
                           '`python -m src.sports.mlb.probables_timing choose` once spring training is measured')
    times = json.loads(path.read_text(encoding='utf-8'))['times_utc']
    pairs = sorted({(int(t[:2]), int(t[3:5])) for t in times})
    if len(pairs) != 3 or any(not (0 <= h < 24 and m in (0, 30)) for h, m in pairs):
        raise MLBLockError(f'{path.name} must name three different half-hour times, not {times!r}')
    return tuple((day, h, m) for day in range(7) for h, m in pairs)


def next_run(now: datetime, runs: Sequence[tuple[int, int, int]]) -> pd.Timestamp:
    """The first scheduled run strictly after `now` (UTC)."""
    now_ts = pd.Timestamp(now).tz_convert('UTC')
    times = []
    for weekday, hour, minute in runs:
        day = now_ts.normalize() + pd.Timedelta(days=(weekday - now_ts.weekday()) % 7)
        t = day + pd.Timedelta(hours=hour, minutes=minute)
        if t <= now_ts:
            t += pd.Timedelta(days=7)
        times.append(t)
    return min(times)


def _scheduled(g: pd.Series) -> bool:
    return bool(g['status'] == GameStatus.SCHEDULED.value)


def _tbd(g: pd.Series) -> bool:
    value = g.get('start_time_tbd', False)
    return bool(value) if isinstance(value, bool | np.bool_) else False


def partner(slate: pd.DataFrame, g: pd.Series) -> pd.Series | None:
    """The other game of `g`'s doubleheader: the same two clubs on the same official date, played or still to
    be played. None when there is none."""
    same = slate[(slate['slate'] == g['slate']) & (slate['home'] == g['home']) & (slate['away'] == g['away'])
                 & (slate['game_id'].astype(str) != str(g['game_id']))]
    live = same[~same['status'].isin([GameStatus.POSTPONED.value, GameStatus.CANCELLED.value])]
    return None if live.empty else live.iloc[0]


@dataclass(frozen=True)
class GameLock:
    """MLB's lock rule: one game at a time (`LockUnit.GAME`). `runs` defaults to the registered times."""
    runs: Runs | None = None
    slack: timedelta = SLACK
    unit: LockUnit = field(default=LockUnit.GAME)

    def _own(self, g: pd.Series, now_ts: pd.Timestamp, after: pd.Timestamp) -> str:
        start = pd.Timestamp(g['start_utc']).tz_convert('UTC')
        if start <= now_ts:
            return 'started'
        return 'lock' if start < after + self.slack else 'hold'

    def decide(self, slate: pd.DataFrame, now: datetime) -> LockDecision:
        runs = self.runs if self.runs is not None else registered_runs()
        now_ts = pd.Timestamp(now).tz_convert('UTC')
        after = next_run(now_ts, runs)
        out: dict[str, list[str]] = {'lock': [], 'started': [], 'hold': []}
        for _, g in slate.iterrows():
            gid = str(g['game_id'])
            if g['status'] in (GameStatus.IN_PROGRESS.value, GameStatus.FINAL.value):
                out['started'].append(gid)
                continue
            if not _scheduled(g):
                continue
            other = partner(slate, g) if _tbd(g) else None
            if other is None or _tbd(other):
                out[self._own(g, now_ts, after)].append(gid)
            elif not _scheduled(other):
                out['lock'].append(gid)  # the game it follows is under way or over: save it now
            else:
                follows = self._own(other, now_ts, after)
                out['lock' if follows in ('lock', 'started') else 'hold'].append(gid)
        return LockDecision(tuple(out['lock']), tuple(out['started']), tuple(out['hold']), after.to_pydatetime())
