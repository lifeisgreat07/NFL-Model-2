"""What every sport shares with the core (Stage 50 item 2; Stage 68 item 31).

Decision record 0006 is the why. Each sport lives in `src/sports/<code>/`
and imports from here the shapes the core and the site read the same way
in every sport: the schedule's columns and its checks, a game's status,
what a lock run decides, and where a sport may read and write. The core
never imports a sport; the site layer (`src/site/`) is the only code that
sees more than one.

Stage 50 also wrote a `SportModule` interface here, for a `SPORT` object
every sport would expose. No sport ever implemented it and nothing
imported it, so Stage 68 item 31 (the 2026-10-09 audit's E15, Mark's call)
deleted it rather than keep a contract that reads as protection and
checks nothing. Lifting the lock, grading and drift code the NHL and NBA
copy into the core is a separate, later item (E16).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path

import pandas as pd

#: A sport's code: lower case, letters only, two to five long ("nfl", "nhl").
#: Every name the sport owns starts with it (decision record 0006, rule 4).
SPORT_CODE = re.compile(r'^[a-z]{2,5}$')

#: The columns every sport's schedule has, in the core's own words. A sport
#: may carry more; the core reads only these. `start_utc` is a tz-aware UTC
#: timestamp, or NaT when the league has not set a time (the lock treats a
#: missing time as the start of that day, the safe direction, as the NFL
#: does today). `home_win` is 1, 0, or <NA> until the game is final.
SCHEDULE_COLUMNS: tuple[str, ...] = (
    'game_id', 'season', 'slate', 'start_utc', 'home', 'away',
    'status', 'home_score', 'away_score', 'home_win',
)


class GameStatus(StrEnum):
    """Where a game is. The core grades only FINAL games, and a game it
    locked that ends CANCELLED shows "Cancelled" and is never counted
    (Mark, 2026-10-05). POSTPONED keeps its pick only if the sport's lock
    rule says the pick was saved for the new start."""
    SCHEDULED = 'scheduled'
    IN_PROGRESS = 'in_progress'
    FINAL = 'final'
    POSTPONED = 'postponed'
    SUSPENDED = 'suspended'
    CANCELLED = 'cancelled'


class LockUnit(StrEnum):
    """What one lock saves. The NFL saves a week at once, before its first
    kickoff; the NHL and NBA save each game before its own start."""
    SLATE = 'slate'
    GAME = 'game'


@dataclass(frozen=True)
class LockDecision:
    """One run's answer for one slate: which games to save now, which are
    too late to predict, and which wait for a later run."""
    lock: tuple[str, ...]
    started: tuple[str, ...]
    hold: tuple[str, ...]
    next_run: datetime


@dataclass(frozen=True)
class SportPaths:
    """Where one sport reads and writes. Every path is under the sport's
    own folder; tests/test_sport_isolation.py holds every workflow's writes
    to these."""
    code: str
    root: Path = field(default=Path(__file__).parents[2])

    def __post_init__(self) -> None:
        if not SPORT_CODE.match(self.code):
            raise ValueError(f'sport code must match {SPORT_CODE.pattern}, got {self.code!r}')

    @property
    def data(self) -> Path:
        return self.root / 'data' / self.code

    @property
    def predictions(self) -> Path:
        return self.root / 'predictions' / self.code

    @property
    def results(self) -> Path:
        return self.root / 'results' / self.code

    @property
    def experiments(self) -> Path:
        return self.root / 'experiments' / self.code

    @property
    def site(self) -> Path:
        """The sport's built pages, published at /<code>/."""
        return self.root / 'site' / self.code


def sport_paths(code: str) -> SportPaths:
    return SportPaths(code)


def check_schedule(code: str, schedule: pd.DataFrame) -> list[str]:
    """Problems with a sport's schedule against the core's contract; empty
    when it meets it. The core calls this before it trusts a schedule."""
    problems = [f'{code}: schedule has no {c!r} column'
                for c in SCHEDULE_COLUMNS if c not in schedule.columns]
    if problems:
        return problems
    if schedule['game_id'].duplicated().any():
        problems.append(f'{code}: game_id is not unique')
    known = {s.value for s in GameStatus}
    bad = sorted(set(schedule['status'].dropna()) - known)
    if bad:
        problems.append(f'{code}: unknown status {bad}')
    starts = schedule['start_utc']
    if len(starts) and getattr(starts.dt, 'tz', None) is None:
        problems.append(f'{code}: start_utc is not timezone-aware')
    return problems
