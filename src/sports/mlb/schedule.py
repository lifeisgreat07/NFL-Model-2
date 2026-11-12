"""MLB's schedule and results, in the core's schedule shape (Stage 98 item 2).

One season comes from the MLB Stats API (statsapi.mlb.com), read by
`data_probe.py` from GitHub's runners in #711: `schedule?sportId=1&season=<s>`
returns every game of the season, with its `gamePk`, UTC start, official
date, clubs, state, doubleheader flag, game number, venue and score.

What the registration (`experiments/mlb/stage98/registry.json`) fixes, this
file does:

- a game is its `gamePk`. A postponed game keeps its `gamePk` and is listed
  again on the day it is played, and a suspended game again on the day it is
  completed: one row per `gamePk`, the last listing (by official date, then
  start) wins;
- only regular-season and postseason games are kept: spring training,
  exhibitions and the All-Star game are left out;
- a game whose venue is not the home club's own venue for that season (the
  Stats API's club record for the season) is `neutral_site`; the Stats API's
  home club stays home.

The answer has `src.core.sport.SCHEDULE_COLUMNS`, with MLB's meanings:
`season` is the calendar year; `slate` is the official date ('2026-04-01');
`status` is a `GameStatus` value read from the Stats API's `codedGameState`
(a 'Completed Early' game is final); `home_win` is 1 or 0 once final, extra
innings included. Beside those: `game_type`, `game_number`, `double_header`,
`venue_id`, `venue` and `neutral_site`.

Anything this file does not recognise (a state, a game type, a missing
field, a tied final) stops the load with every problem named:
`MLBScheduleError`. Guessing is how a wrong row reaches a lock.

A finished season can be cached: `MLB_CACHE` names a folder, and a season
before the current one whose every game is final or cancelled is written
there once and read back after. Nothing is cached when it is unset, and the
current season is never cached.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.sport import SCHEDULE_COLUMNS, GameStatus, check_schedule

STATS = 'https://statsapi.mlb.com/api/v1'
#: The game types this pipeline keeps: the regular season, then the wild card, division, league
#: championship series and the World Series. S (spring), E (exhibition) and A (All-Star) are left out.
GAME_TYPES: Mapping[str, str] = {'R': 'regular', 'F': 'wild_card', 'D': 'division', 'L': 'league', 'W': 'world_series'}
#: Every game type the Stats API lists, kept or not; any other stops the load.
KNOWN_TYPES = frozenset({*GAME_TYPES, 'S', 'E', 'A'})
SEASON = STATS + '/schedule?sportId=1&season={season}&gameType=' + ','.join(GAME_TYPES) + '&hydrate=venue'
DAY = STATS + '/schedule?sportId=1&date={day}&gameType=' + ','.join(GAME_TYPES) + '&hydrate=venue,probablePitcher'
CLUBS = STATS + '/teams?sportId=1&season={season}'

#: `codedGameState` -> status. 'O' is "Game Over": the score is in but the league has not marked the game
#: final yet, so it waits as in progress; nothing grades it until 'F'. Every state of 2020, 2025 and 2026's
#: finished schedules is here (F, D, C), with the ones a live day shows.
CODED_STATE: Mapping[str, GameStatus] = {
    'S': GameStatus.SCHEDULED, 'P': GameStatus.SCHEDULED,
    'I': GameStatus.IN_PROGRESS, 'M': GameStatus.IN_PROGRESS, 'O': GameStatus.IN_PROGRESS,
    'F': GameStatus.FINAL,
    'D': GameStatus.POSTPONED, 'U': GameStatus.SUSPENDED, 'C': GameStatus.CANCELLED,
}

#: The columns this file adds to the core's.
EXTRA_COLUMNS = ('game_type', 'game_number', 'double_header', 'venue_id', 'venue', 'neutral_site')

#: A date as the Stats API writes it.
DATE = re.compile(r'\d{4}-\d{2}-\d{2}')

CACHE_ENV = 'MLB_CACHE'

Json = Any


class MLBScheduleError(ValueError):
    """The Stats API answered with something this file will not guess about."""


def current_season(now: datetime) -> int:
    """The season a date belongs to: spring training opens in February and the World Series ends by early
    November, so January still belongs to the season just finished."""
    return now.year if now.month >= 2 else now.year - 1


def fetch_json(url: str, timeout: int = 60) -> Json:
    req = urllib.request.Request(url, headers={'User-Agent': 'NFL-Model-2 MLB pipeline'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def games_of(data: Json) -> list[Json]:
    return [g for d in data.get('dates') or [] for g in d.get('games') or []]


def _side(g: Json, side: str) -> Json:
    return ((g.get('teams') or {}).get(side) or {})


def _club(g: Json, side: str) -> Any:
    return (_side(g, side).get('team') or {}).get('id')


def raw_problems(g: Json) -> list[str]:
    """What is wrong with one game as listed; empty when usable."""
    gid = g.get('gamePk', '?')
    out = [f'game {gid}: no {k}' for k in ('gamePk', 'gameType', 'gameDate', 'officialDate', 'gameNumber')
           if g.get(k) in (None, '')]
    gtype = g.get('gameType')
    if gtype and gtype not in KNOWN_TYPES:
        out.append(f'game {gid}: unknown gameType {gtype!r}')
    home, away = _club(g, 'home'), _club(g, 'away')
    if not isinstance(home, int) or not isinstance(away, int) or home == away:
        out.append(f'game {gid}: not two clubs ({home} v {away})')
    start = g.get('gameDate')
    if start and not str(start).endswith('Z'):
        out.append(f'game {gid}: start {start!r} is not UTC')
    day = g.get('officialDate')
    if day and not DATE.fullmatch(str(day)):
        out.append(f'game {gid}: official date {day!r} is not a date')
    if not isinstance((g.get('venue') or {}).get('id'), int):
        out.append(f'game {gid}: no venue')
    coded = (g.get('status') or {}).get('codedGameState')
    if coded not in CODED_STATE:
        out.append(f'game {gid}: unknown codedGameState {coded!r}')
    elif CODED_STATE[coded] is GameStatus.FINAL:
        hs, as_ = _side(g, 'home').get('score'), _side(g, 'away').get('score')
        if not isinstance(hs, int) or not isinstance(as_, int):
            out.append(f'game {gid}: final without both scores')
        elif hs == as_:
            out.append(f'game {gid}: final with a tied score {hs}-{as_}')
    return out


def last_listings(games: list[Json]) -> list[Json]:
    """One listing per gamePk: the last by official date, then start. A postponed game is listed on its first
    date as postponed and again on the day it is played; a suspended one again on the day it is completed."""
    out: dict[Any, Json] = {}
    for g in sorted(games, key=lambda g: (str(g.get('officialDate')), str(g.get('gameDate')))):
        out[g.get('gamePk')] = g
    return list(out.values())


def home_venues(data: Json) -> dict[int, int]:
    """Each club's own venue for one season, from the Stats API's club list for that season."""
    out = {}
    for t in data.get('teams') or []:
        venue = (t.get('venue') or {}).get('id')
        if isinstance(t.get('id'), int) and isinstance(venue, int):
            out[t['id']] = venue
    return out


def to_schedule(games: list[Json], season: int, venues: Mapping[int, int]) -> pd.DataFrame:
    """The core's schedule frame from the Stats API's games and the season's home venues. Raises
    MLBScheduleError naming every unusable game."""
    problems = [p for g in games for p in raw_problems(g)]
    wrong_season = sorted({str(g.get('season')) for g in games} - {str(season), 'None'})
    if wrong_season:
        problems.append(f'games from another season: {wrong_season}')
    kept = [g for g in games if g.get('gameType') in GAME_TYPES]
    no_venue = sorted({c for g in kept for c in (_club(g, 'home'),) if isinstance(c, int) and c not in venues})
    if no_venue:
        problems.append(f'clubs with no home venue for {season}: {no_venue}')
    if problems:
        raise MLBScheduleError('; '.join(problems))
    rows = []
    for g in last_listings(kept):
        status = CODED_STATE[g['status']['codedGameState']]
        final = status is GameStatus.FINAL
        hs = _side(g, 'home').get('score') if final else None
        as_ = _side(g, 'away').get('score') if final else None
        home = _club(g, 'home')
        venue = g['venue']
        rows.append({
            'game_id': str(g['gamePk']),
            'season': season,
            'slate': g['officialDate'],
            'start_utc': g['gameDate'],
            'home': str(home),
            'away': str(_club(g, 'away')),
            'status': status.value,
            'home_score': hs,
            'away_score': as_,
            'home_win': int(hs > as_) if final else None,
            'game_type': GAME_TYPES[g['gameType']],
            'game_number': int(g['gameNumber']),
            'double_header': str(g.get('doubleHeader') or 'N'),
            'venue_id': venue['id'],
            'venue': venue.get('name'),
            'neutral_site': venue['id'] != venues[home],
        })
    df = pd.DataFrame(rows, columns=[*SCHEDULE_COLUMNS, *EXTRA_COLUMNS])
    df['start_utc'] = pd.to_datetime(df['start_utc'], utc=True)
    for col in ('home_score', 'away_score', 'home_win'):
        df[col] = df[col].astype('Int64')
    df = df.sort_values(['start_utc', 'game_id'], kind='stable').reset_index(drop=True)
    contract = check_schedule('mlb', df)
    if contract:
        raise MLBScheduleError('; '.join(contract))
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
    """One season's schedule and results. `cache` defaults to `MLB_CACHE`; only a finished season before the
    current one is read from or written to it."""
    cache = cache if cache is not None else cache_dir()
    now = now or datetime.now(UTC)
    cacheable = cache is not None and season < current_season(now)
    path = cache / f'schedule_{season}.parquet' if cache is not None else None
    if cacheable and path is not None and path.exists():
        df: pd.DataFrame = pd.read_parquet(path)
        return df
    venues = home_venues(get(CLUBS.format(season=season)))
    df = to_schedule(games_of(get(SEASON.format(season=season))), season, venues)
    if cacheable and path is not None and finished(df):
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.tmp')
        df.to_parquet(tmp, index=False)
        tmp.replace(path)
    return df


def slate(schedule: pd.DataFrame, day: str) -> pd.DataFrame:
    """The games of one official date ('2026-04-01'), earliest first."""
    return schedule[schedule['slate'] == day].reset_index(drop=True)


def probables(data: Json) -> dict[str, tuple[Any, Any]]:
    """Each game's probable pitchers from one day's schedule (`DAY`), as (home, away) Stats API person ids;
    None where a club has not named one."""
    return {str(g.get('gamePk')): ((_side(g, 'home').get('probablePitcher') or {}).get('id'),
                                   (_side(g, 'away').get('probablePitcher') or {}).get('id'))
            for g in last_listings(games_of(data))}
