"""When an NBA pick is saved: each game on its own, before its own start.

Stage 65, as registered in `experiments/nba/stage65/registry.json`. The NBA
plays most days, and its late news (who is listed Out) arrives through the
day, so each game is saved by the last scheduled run before it starts: as
late as possible, and never after the start, since a pick saved then is not
a prediction. The rule is the NHL's (`src/sports/nhl/lock.py`); only the run
times differ, and the sports keep their own copies so neither reads the
other's code.

`GameLock.decide(slate, now)` answers for one run, in the core's words
(`src.core.sport.LockDecision`):

- **lock**: scheduled games that start before the next run plus `slack`;
  waiting for the next run would risk saving them late.
- **started**: games already under way or over (the start has passed, or
  ESPN says so). They are never predicted.
- **hold**: scheduled games the next run can still save in time.

A postponed, suspended or cancelled game is in none of the three. A game
with no start time counts from the start of its ESPN date (Eastern), the
earliest it could be, which locks it sooner rather than later.

The runs are `RUNS_UTC`: 16:00 UTC (noon Eastern in October, after the
morning shootarounds and the first injury updates) and 21:30 UTC (5:30 PM
Eastern, ninety minutes before the usual 7 PM tip). Weekend afternoon games
lock at 16:00 or the night before.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd

from src.core.sport import GameStatus, LockDecision, LockUnit

#: (weekday Mon=0, hour, minute) UTC, every day.
RUNS_UTC: tuple[tuple[int, int, int], ...] = tuple(
    (day, hour, minute) for day in range(7) for hour, minute in ((16, 0), (21, 30)))

#: How late a run may start and still be trusted to save a game in time.
SLACK = timedelta(hours=1)


def next_run(now: datetime, runs: Sequence[tuple[int, int, int]] = RUNS_UTC) -> pd.Timestamp:
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


def start_of(game: pd.Series) -> pd.Timestamp:
    """The game's start, or the start of its ESPN date (Eastern) when there
    is no time."""
    start = game['start_utc']
    if isinstance(start, pd.Timestamp) and not pd.isna(start):
        return start.tz_convert('UTC')
    day = pd.Timestamp(str(game['slate']))
    return day.tz_localize('America/New_York').tz_convert('UTC')


@dataclass(frozen=True)
class GameLock:
    """The NBA's lock rule: one game at a time (`LockUnit.GAME`)."""
    runs: tuple[tuple[int, int, int], ...] = RUNS_UTC
    slack: timedelta = SLACK
    unit: LockUnit = field(default=LockUnit.GAME)

    def decide(self, slate: pd.DataFrame, now: datetime) -> LockDecision:
        now_ts = pd.Timestamp(now).tz_convert('UTC')
        after = next_run(now_ts, self.runs)
        lock, started, hold = [], [], []
        for _, g in slate.iterrows():
            status = g['status']
            gid = str(g['game_id'])
            if status in (GameStatus.IN_PROGRESS.value, GameStatus.FINAL.value):
                started.append(gid)
                continue
            if status != GameStatus.SCHEDULED.value:
                continue
            start = start_of(g)
            if start <= now_ts:
                started.append(gid)
            elif start < after + self.slack:
                lock.append(gid)
            else:
                hold.append(gid)
        return LockDecision(tuple(lock), tuple(started), tuple(hold), after.to_pydatetime())
