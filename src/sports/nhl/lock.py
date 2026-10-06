"""When an NHL pick is saved: each game on its own, before its own start.

Stage 54 item 1. The NFL saves a whole week before its first kickoff. The
NHL plays most days and its late news (the starting goalie) arrives through
the day, so each game is saved by the last scheduled run before it starts:
as late as possible, so the goalie is as settled as it will get, and never
after the start, since a pick saved then is not a prediction.

`GameLock.decide(slate, now)` answers for one run, in the core's words
(`src.core.sport.LockDecision`):

- **lock**: scheduled games that start before the next run plus `slack`;
  waiting for the next run would risk saving them late.
- **started**: games already under way or over (the start has passed, or
  the league says so). They are never predicted.
- **hold**: scheduled games the next run can still save in time.

A postponed, suspended or cancelled game is in none of the three: there is
no start to lock before. A game with no start time counts from the start of
its league date, the earliest it could be, which locks it sooner rather
than later (the same safe direction the NFL takes).

The runs are `RUNS_UTC`: 14:00 UTC (10 AM Eastern, after the morning skates
and the first goalie reports) and 21:00 UTC (5 PM Eastern, two hours before
the usual 7 PM puck drop). Early afternoon weekend games lock at 14:00.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd

from src.core.sport import GameStatus, LockDecision, LockUnit

#: (weekday Mon=0, hour, minute) UTC, every day.
RUNS_UTC: tuple[tuple[int, int, int], ...] = tuple(
    (day, hour, 0) for day in range(7) for hour in (14, 21))

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
    """The game's start, or the start of its league date (Eastern) when the
    league has not set a time."""
    start = game['start_utc']
    if isinstance(start, pd.Timestamp) and not pd.isna(start):
        return start.tz_convert('UTC')
    day = pd.Timestamp(str(game['slate']))
    return day.tz_localize('America/New_York').tz_convert('UTC')


@dataclass(frozen=True)
class GameLock:
    """The NHL's lock rule: one game at a time (`LockUnit.GAME`)."""
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
