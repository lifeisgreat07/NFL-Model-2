"""What a sport must provide to run the NFL's workflow (Stage 50 item 2).

Decision record 0006 is the why; this file is the contract. The shared core
(lock engine, grading, drift check, paired bootstrap, registrations, alerts,
the page shell) is written against `SportModule` and nothing else. Each
sport lives in `src/sports/<code>/` and exposes one object, `SPORT`, that
satisfies it. The core never imports a sport; the site layer
(`src/site/`) is the only code that sees more than one.

Everything a sport owns is named here, so the core cannot quietly grow an
NFL assumption: if the core needs a fact about the game, it asks the module.

Nothing imports this file yet. The NFL becomes the first module in Stage 52,
behind a byte-identical proof; until then this is the written contract the
isolation guards (tests/test_sport_isolation.py) and Stage 51's go/no-go
are checked against.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol, runtime_checkable

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


class ModelSpecLike(Protocol):
    """What the core needs of a model definition. `src/core/model_specs.py`'s
    `ModelSpec` satisfies it as it stands; the core names the shape rather
    than importing it, because until Stage 52 moves that file here,
    `src/sports/nfl` is the NFL and the core imports no sport."""
    @property
    def features(self) -> tuple[str, ...]: ...

    def fit(self, rows: pd.DataFrame) -> object: ...


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
class Team:
    """One franchise as the sport's sources name it now."""
    abbr: str
    name: str
    #: Older abbreviations the sources use for the same franchise
    #: (OAK -> LV; ARI -> UTA in the NHL). Item 5 of Stage 51 fills these.
    former: tuple[str, ...] = ()


@dataclass(frozen=True)
class GameRules:
    """The rules that change what an outcome or a table means.

    `outcome` is what Model A and Model B predict. Both sports here predict
    the home team winning, overtime and shootout included, so a game always
    has a winner except where `ties_possible`."""
    ties_possible: bool
    overtime: bool
    shootout: bool
    #: Standings points: a win, an overtime or shootout loss, a tie. The NFL
    #: ranks by win percentage and uses (1, 0, 0.5) only for display.
    points_win: float
    points_ot_loss: float
    points_tie: float
    regular_season_games: int
    teams_in_playoffs: int


@dataclass(frozen=True)
class LockDecision:
    """One run's answer for one slate: which games to save now, which are
    too late to predict, and which wait for a later run."""
    lock: tuple[str, ...]
    started: tuple[str, ...]
    hold: tuple[str, ...]
    next_run: datetime


class LockRule(Protocol):
    """When picks are saved. A lock is written once and never rewritten,
    and only locked picks are graded (decision record 0003). The core
    writes the file; the rule only decides."""
    unit: LockUnit

    def decide(self, slate: pd.DataFrame, now: datetime) -> LockDecision: ...


@dataclass(frozen=True)
class Display:
    """What the shared page shell needs to say about this sport."""
    name: str               # "NFL"
    slate_label: str        # "Week" / "Day"
    #: The one player whose late news moves the pick, and the routine that
    #: researches it: "Quarterback" for the NFL, "Starting goalie" for the NHL.
    key_player_role: str
    team_colours: Mapping[str, str]


@runtime_checkable
class SportModule(Protocol):
    """Everything the shared core needs from one sport.

    The folders are not attributes: they are `sport_paths(code)`, so no sport
    can point its writes at another sport's folder."""
    code: str
    display: Display
    rules: GameRules
    teams: Mapping[str, Team]
    lock_rule: LockRule
    #: 'model_a' is required. 'model_b' and 'market' exist only when the
    #: sport has a market source (Stage 51 item 3); without one the sport
    #: ships Model A alone and the page says so.
    model_specs: Mapping[str, ModelSpecLike]
    #: When the sport's scheduled runs start, (weekday Mon=0, hour, minute)
    #: UTC. The slot guard and the lock rule both read this one list.
    scheduled_runs_utc: Sequence[tuple[int, int, int]]

    def current_season(self, now: datetime) -> int:
        """The season a date belongs to (the NFL's January is last year's)."""
        ...

    def schedule(self, season: int) -> pd.DataFrame:
        """Every game of the season with at least SCHEDULE_COLUMNS."""
        ...

    def features(self, schedule: pd.DataFrame, as_of: datetime) -> pd.DataFrame:
        """One row per game_id with every column any model spec names,
        built only from information available before `as_of`."""
        ...

    def key_players(self, slate: pd.DataFrame) -> pd.DataFrame:
        """The late-breaking player per team per game, with its source and
        basis ('override', 'announced', 'last_game'), as the QB is today."""
        ...


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
