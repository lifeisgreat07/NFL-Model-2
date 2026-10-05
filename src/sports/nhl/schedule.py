"""The NHL's schedule and results, in the core's schedule shape.

Stage 55 items 1 and 2. One season comes from the league's own feed
(api-web.nhle.com, read by `data_probe.py` from GitHub's runners in Stage
51), one club at a time: `club-schedule-season/<club>/<season>` returns a
club's whole season, past games with their scores and future ones with
their start. Every game is in two clubs' lists, so a season read this way
checks itself: a game seen from one side only means a club's list came back
short, and the load stops rather than hand the model a season with holes.

The answer has `src.core.sport.SCHEDULE_COLUMNS`, with the NHL's meanings:

- `season` is the year the season starts (2026 for 2026-27), as for the NFL;
- `slate` is the league's date for the game ('2026-10-06'): the NHL locks
  and shows games by day;
- `status` is a `GameStatus` value. The league's `gameScheduleState` wins
  over its `gameState`: a postponed game can still read 'FUT';
- `home_win` counts overtime and the shootout: the league adds the
  shootout's deciding goal to the winner's score, so the scores decide it.

Beside those: `game_type` ('regular' or 'playoff'; preseason and all-star
games are left out), `game_date`, `last_period` ('REG', 'OT', 'SO' once
final), `neutral_site` and `venue`.

Anything the feed returns that this file does not recognise (a state, a
missing field, a tied final) stops the load with every problem named:
`NHLScheduleError`. Guessing is how a wrong row reaches a lock.

A finished season can be cached: `NHL_CACHE` names a folder, and a season
before the current one whose every game is final or cancelled is written
there once and read back after. Nothing is cached when it is unset, and the
current season is never cached.
"""
from __future__ import annotations

import json
import os
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.sport import SCHEDULE_COLUMNS, GameStatus, check_schedule

WEB = 'https://api-web.nhle.com/v1'
CLUB_SEASON = WEB + '/club-schedule-season/{club}/{season_id}'

#: Every club abbreviation the feed has used since 2010-11: the 32 clubs of
#: 2026-27, then Arizona (to 2023-24), Phoenix (to 2013-14) and Atlanta (to
#: 2010-11). A club that did not exist in a season returns an empty list.
CLUBS = (
    'ANA', 'BOS', 'BUF', 'CAR', 'CBJ', 'CGY', 'CHI', 'COL', 'DAL', 'DET',
    'EDM', 'FLA', 'LAK', 'MIN', 'MTL', 'NJD', 'NSH', 'NYI', 'NYR', 'OTT',
    'PHI', 'PIT', 'SEA', 'SJS', 'STL', 'TBL', 'TOR', 'UTA', 'VAN', 'VGK',
    'WPG', 'WSH',
    'ARI', 'PHX', 'ATL',
)

#: The league's game types this pipeline keeps. 1 is preseason, 4 the
#: all-star game; neither is predicted or graded.
GAME_TYPES = {2: 'regular', 3: 'playoff'}

#: `gameState` -> status, for a game whose `gameScheduleState` is OK.
GAME_STATE = {
    'FUT': GameStatus.SCHEDULED, 'PRE': GameStatus.SCHEDULED,
    'LIVE': GameStatus.IN_PROGRESS, 'CRIT': GameStatus.IN_PROGRESS,
    'FINAL': GameStatus.FINAL, 'OFF': GameStatus.FINAL,
}

#: `gameScheduleState` -> the status it forces, or None to read `gameState`.
SCHEDULE_STATE: Mapping[str, GameStatus | None] = {
    'OK': None, 'TBD': None,
    'PPD': GameStatus.POSTPONED, 'SUSP': GameStatus.SUSPENDED, 'CNCL': GameStatus.CANCELLED,
}

LAST_PERIODS = ('REG', 'OT', 'SO')

#: The columns this file adds to the core's.
EXTRA_COLUMNS = ('game_type', 'game_date', 'last_period', 'neutral_site', 'venue')

CACHE_ENV = 'NHL_CACHE'

Json = Any


class NHLScheduleError(ValueError):
    """The feed answered with something this file will not guess about."""


def season_id(season: int) -> int:
    """The league's id for a season: 2026 -> 20262027."""
    return season * 10000 + season + 1


def current_season(now: datetime) -> int:
    """The season a date belongs to. Preseason starts in mid-September and
    the final ends in June, so July and August still belong to the season
    just finished."""
    return now.year if now.month >= 9 else now.year - 1


def fetch_json(url: str, timeout: int = 30) -> Json:
    req = urllib.request.Request(url, headers={'User-Agent': 'NFL-Model-2 NHL pipeline'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _abbrev(side: Json) -> str | None:
    return (side or {}).get('abbrev')


def raw_problems(g: Json) -> list[str]:
    """What is wrong with one game from a club's list; empty when usable."""
    gid = g.get('id', '?')
    out = [f'game {gid}: no {k}' for k in ('id', 'season', 'gameType', 'gameDate', 'startTimeUTC',
                                            'gameState', 'gameScheduleState') if g.get(k) in (None, '')]
    home, away = _abbrev(g.get('homeTeam')), _abbrev(g.get('awayTeam'))
    if not home or not away or home == away:
        out.append(f'game {gid}: not two teams ({home} v {away})')
    start = g.get('startTimeUTC')
    if start and not str(start).endswith('Z'):
        out.append(f'game {gid}: start {start!r} is not UTC')
    state, sched = g.get('gameState'), g.get('gameScheduleState')
    if state and state not in GAME_STATE:
        out.append(f'game {gid}: unknown gameState {state!r}')
    if sched and sched not in SCHEDULE_STATE:
        out.append(f'game {gid}: unknown gameScheduleState {sched!r}')
    if GAME_STATE.get(state) is GameStatus.FINAL and SCHEDULE_STATE.get(sched) is None:
        hs, as_ = (g.get('homeTeam') or {}).get('score'), (g.get('awayTeam') or {}).get('score')
        if not isinstance(hs, int) or not isinstance(as_, int):
            out.append(f'game {gid}: final without both scores')
        elif hs == as_:
            out.append(f'game {gid}: final with a tied score {hs}-{as_}')
        period = (g.get('gameOutcome') or {}).get('lastPeriodType')
        if period not in LAST_PERIODS:
            out.append(f'game {gid}: final without a last period (got {period!r})')
    return out


def status_of(g: Json) -> GameStatus:
    forced = SCHEDULE_STATE[g['gameScheduleState']]
    return forced if forced is not None else GAME_STATE[g['gameState']]


def club_games(season: int, get: Callable[[str], Json] = fetch_json,
               clubs: Iterable[str] = CLUBS) -> list[Json]:
    """Every regular-season and playoff game of a season, read club by club,
    each once. Raises if a game appears in only one of its clubs' lists."""
    seen: dict[int, Json] = {}
    sides: dict[int, set[str]] = {}
    for club in clubs:
        data = get(CLUB_SEASON.format(club=club, season_id=season_id(season)))
        for g in data.get('games') or []:
            if g.get('gameType') not in GAME_TYPES:
                continue
            gid = g.get('id')
            seen.setdefault(gid, g)
            sides.setdefault(gid, set()).add(club)
    one_sided = sorted(str(gid) for gid, s in sides.items() if len(s) < 2)
    if one_sided:
        raise NHLScheduleError(
            f'{len(one_sided)} game(s) came back from only one club\'s list, so a list is short: '
            + ', '.join(one_sided[:10]))
    return [seen[gid] for gid in sorted(seen)]


def to_schedule(games: list[Json], season: int) -> pd.DataFrame:
    """The core's schedule frame from the feed's games. Raises
    NHLScheduleError naming every unusable game."""
    problems = [p for g in games for p in raw_problems(g)]
    wrong_season = sorted({g.get('season') for g in games} - {season_id(season), None})
    if wrong_season:
        problems.append(f'games from another season: {wrong_season}')
    if problems:
        raise NHLScheduleError('; '.join(problems))
    rows = []
    for g in games:
        status = status_of(g)
        final = status is GameStatus.FINAL
        hs = g['homeTeam'].get('score') if final else None
        as_ = g['awayTeam'].get('score') if final else None
        home_win = None
        if final and hs is not None and as_ is not None:
            home_win = int(hs > as_)
        rows.append({
            'game_id': str(g['id']),
            'season': season,
            'slate': g['gameDate'],
            'start_utc': g['startTimeUTC'],
            'home': g['homeTeam']['abbrev'],
            'away': g['awayTeam']['abbrev'],
            'status': status.value,
            'home_score': hs,
            'away_score': as_,
            'home_win': home_win,
            'game_type': GAME_TYPES[g['gameType']],
            'game_date': g['gameDate'],
            'last_period': (g.get('gameOutcome') or {}).get('lastPeriodType') if final else None,
            'neutral_site': bool(g.get('neutralSite', False)),
            'venue': (g.get('venue') or {}).get('default'),
        })
    df = pd.DataFrame(rows, columns=[*SCHEDULE_COLUMNS, *EXTRA_COLUMNS])
    df['start_utc'] = pd.to_datetime(df['start_utc'], utc=True)
    for col in ('home_score', 'away_score', 'home_win'):
        df[col] = df[col].astype('Int64')
    df = df.sort_values(['start_utc', 'game_id'], kind='stable').reset_index(drop=True)
    contract = check_schedule('nhl', df)
    if contract:
        raise NHLScheduleError('; '.join(contract))
    return df


def finished(schedule: pd.DataFrame) -> bool:
    """Every game is final or cancelled: nothing in it will change."""
    done = {GameStatus.FINAL.value, GameStatus.CANCELLED.value}
    return bool(len(schedule)) and bool(schedule['status'].isin(done).all())


def cache_dir() -> Path | None:
    value = os.environ.get(CACHE_ENV, '').strip()
    return Path(value) if value else None


def load_schedule(season: int, get: Callable[[str], Json] = fetch_json,
                  cache: Path | None = None, now: datetime | None = None) -> pd.DataFrame:
    """One season's schedule and results. `cache` defaults to `NHL_CACHE`;
    only a finished season before the current one is read from or written
    to it."""
    cache = cache if cache is not None else cache_dir()
    now = now or datetime.now(UTC)
    cacheable = cache is not None and season < current_season(now)
    path = cache / f'schedule_{season}.parquet' if cache is not None else None
    if cacheable and path is not None and path.exists():
        df: pd.DataFrame = pd.read_parquet(path)
        return df
    df = to_schedule(club_games(season, get), season)
    if cacheable and path is not None and finished(df):
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.tmp')
        df.to_parquet(tmp, index=False)
        tmp.replace(path)
    return df


def slate(schedule: pd.DataFrame, day: str) -> pd.DataFrame:
    """The games on one league date ('2026-10-06'), earliest first."""
    return schedule[schedule['slate'] == day].reset_index(drop=True)
