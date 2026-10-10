"""The NBA's schedule and results, in the core's schedule shape.

Stage 61, as the NHL's schedule was Stage 55. The league's own feeds refuse this
project (docs/nba-data.md), so a season comes from ESPN's public
scoreboard, one game day at a time. Any day's scoreboard carries the
season's calendar: every date with a game, preseason to the finals. The
load reads that calendar from a mid-January date, then each date on it.

The answer has `src.core.sport.SCHEDULE_COLUMNS`, with the NBA's meanings:

- `season` is the year the season starts (2026 for 2026-27), as for the
  NFL and the NHL;
- `slate` is ESPN's date for the game ('2026-10-21'), the US date it is
  listed under: the NBA locks and shows games by day;
- `status` is a `GameStatus` value, from ESPN's status name;
- `home_win` counts overtime, which every game that ends tied gets.

Beside those: `game_type` ('regular', 'playin' or 'playoff'), `neutral_site`
and `venue`. Preseason games and All-Star games are left out, and so is a
game not yet played whose teams ESPN still lists as `TBD`. ESPN files
the All-Star games under the regular season, so the season type alone does
not keep them out; the competition's own type (`ALLSTAR`) does. The NBA
Cup final (competition type `CC`) is a real game at a neutral site and is
kept, as a regular-season game.

Anything ESPN returns that this file does not recognise (a status, a
competition type, a missing field, a tied final) stops the load with every
problem named: `NBAScheduleError`. Guessing is how a wrong row reaches a
lock.

A finished season can be cached: `NBA_CACHE` names a folder, and a season
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

SITE = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba'
SCOREBOARD = SITE + '/scoreboard?dates={day}&limit=1000'

#: ESPN's season types this pipeline keeps. 1 is preseason, never used.
SEASON_TYPES = {2: 'regular', 3: 'playoff', 5: 'playin'}

#: ESPN's competition types, each seen on a real game. `STD` is an ordinary
#: game, `CC` the NBA Cup final, and the playoff rounds have their own (first
#: round, conference semifinals, conference finals, finals). Only the
#: All-Star games are left out.
COMPETITION_TYPES: Mapping[str, bool] = {
    'STD': True, 'CC': True, 'RD16': True, 'QTR': True, 'SEMI': True, 'FINAL': True,
    'ALLSTAR': False,
}

#: ESPN's status name -> status.
STATUS: Mapping[str, GameStatus] = {
    'STATUS_SCHEDULED': GameStatus.SCHEDULED,
    'STATUS_IN_PROGRESS': GameStatus.IN_PROGRESS,
    'STATUS_HALFTIME': GameStatus.IN_PROGRESS,
    'STATUS_END_PERIOD': GameStatus.IN_PROGRESS,
    'STATUS_DELAYED': GameStatus.IN_PROGRESS,
    'STATUS_FINAL': GameStatus.FINAL,
    'STATUS_POSTPONED': GameStatus.POSTPONED,
    'STATUS_SUSPENDED': GameStatus.SUSPENDED,
    'STATUS_CANCELED': GameStatus.CANCELLED,
}

#: ESPN's team for a side not yet decided.
PLACEHOLDER = 'TBD'

EXTRA_COLUMNS = ('game_type', 'neutral_site', 'venue')

CACHE_ENV = 'NBA_CACHE'

Json = Any


class NBAScheduleError(ValueError):
    """ESPN answered with something this file will not guess about."""


def current_season(now: datetime) -> int:
    """The season a date belongs to. Preseason starts in early October and
    the finals end in June, so July to September still belong to the season
    just finished."""
    return now.year if now.month >= 10 else now.year - 1


def calendar_day(season: int) -> str:
    """A date inside every season's regular season, for reading its calendar:
    15 January. 1 November is not: 2020-21 began on 22 December, and on
    1 November 2020 the scoreboard still carried 2019-20's calendar."""
    return f'{season + 1}0115'


def fetch_json(url: str, timeout: int = 30) -> Json:
    req = urllib.request.Request(url, headers={'User-Agent': 'NFL-Model-2 NBA pipeline'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def calendar(board: Json) -> list[str]:
    """The season's game dates ('20261021') from any of its scoreboards."""
    leagues = board.get('leagues') or [{}]
    days = leagues[0].get('calendar') or []
    if not days:
        raise NBAScheduleError('the scoreboard carries no calendar')
    return sorted({str(d)[:10].replace('-', '') for d in days})


def _sides(comp: Json) -> dict[str, Json]:
    return {c.get('homeAway'): c for c in comp.get('competitors') or []}


def placeholder(comp: Json) -> bool:
    """A game listed before its teams are known: the NBA Cup's knockout
    games and the playoffs are on the calendar with `TBD` for a team until
    the bracket fills. Nothing can be predicted for it yet, and a finished
    game never has one."""
    abbrs = {((c.get('team') or {}).get('abbreviation')) for c in comp.get('competitors') or []}
    name = ((comp.get('status') or {}).get('type') or {}).get('name')
    return PLACEHOLDER in abbrs and name == 'STATUS_SCHEDULED'


def kept(ev: Json) -> bool:
    """Whether a game is one this pipeline predicts: regular season, play-in
    or playoffs, not an All-Star game, and with both teams known. An unknown
    competition type is kept here and stopped by `raw_problems`."""
    if (ev.get('season') or {}).get('type') not in SEASON_TYPES:
        return False
    comp = (ev.get('competitions') or [{}])[0]
    if placeholder(comp):
        return False
    kind = str((comp.get('type') or {}).get('abbreviation'))
    return COMPETITION_TYPES.get(kind, True)


#: A team code as the feed sends it (BOS, NY, UTAH). The page draws codes
#: into its HTML, so anything else is refused here rather than escaped later
#: (Stage 68 item 8, the 2026-10-09 audit).
TEAM_CODE = re.compile(r'[A-Z]{2,4}')


def raw_problems(ev: Json) -> list[str]:
    """What is wrong with one kept game; empty when usable."""
    gid = ev.get('id', '?')
    out = [f'game {gid}: no {k}' for k in ('id', 'date') if not ev.get(k)]
    comps = ev.get('competitions') or []
    if len(comps) != 1:
        return out + [f'game {gid}: {len(comps)} competitions']
    comp = comps[0]
    kind = (comp.get('type') or {}).get('abbreviation')
    if kind not in COMPETITION_TYPES:
        out.append(f'game {gid}: unknown competition type {kind!r}')
    sides = _sides(comp)
    home = ((sides.get('home') or {}).get('team') or {}).get('abbreviation')
    away = ((sides.get('away') or {}).get('team') or {}).get('abbreviation')
    if not home or not away or home == away:
        out.append(f'game {gid}: not two teams ({home} v {away})')
    for code in (home, away):
        if code and not TEAM_CODE.fullmatch(str(code)):
            out.append(f'game {gid}: team code {code!r} is not two to four capital letters')
    start = ev.get('date')
    if start and not str(start).endswith('Z'):
        out.append(f'game {gid}: start {start!r} is not UTC')
    name = str(((comp.get('status') or {}).get('type') or {}).get('name'))
    if name not in STATUS:
        out.append(f'game {gid}: unknown status {name!r}')
    elif STATUS[name] is GameStatus.FINAL and home and away:
        try:
            hs, as_ = int(sides['home']['score']), int(sides['away']['score'])
        except (KeyError, TypeError, ValueError):
            out.append(f'game {gid}: final without both scores')
        else:
            if hs == as_:
                out.append(f'game {gid}: final with a tied score {hs}-{as_}')
    return out


def season_games(season: int, get: Callable[[str], Json] = fetch_json) -> list[tuple[str, Json]]:
    """Every kept game of a season with the date it was listed under, each
    once, read date by date along the season's calendar. A game listed on
    two dates (a postponed game shown on its old and its new date) keeps
    the later listing."""
    days = calendar(get(SCOREBOARD.format(day=calendar_day(season))))
    seen: dict[str, tuple[str, Json]] = {}
    for day in days:
        for ev in get(SCOREBOARD.format(day=day)).get('events') or []:
            if (ev.get('season') or {}).get('year') not in (season + 1, None):
                continue
            if kept(ev):
                seen[str(ev.get('id'))] = (f'{day[:4]}-{day[4:6]}-{day[6:]}', ev)
    return [seen[gid] for gid in sorted(seen)]


def to_schedule(games: list[tuple[str, Json]], season: int) -> pd.DataFrame:
    """The core's schedule frame from ESPN's games. Raises NBAScheduleError
    naming every unusable game."""
    problems = [p for _, ev in games for p in raw_problems(ev)]
    if problems:
        raise NBAScheduleError('; '.join(problems))
    rows = []
    for day, ev in games:
        comp = ev['competitions'][0]
        sides = _sides(comp)
        status = STATUS[comp['status']['type']['name']]
        final = status is GameStatus.FINAL
        hs = int(sides['home']['score']) if final else None
        as_ = int(sides['away']['score']) if final else None
        rows.append({
            'game_id': str(ev['id']),
            'season': season,
            'slate': day,
            'start_utc': ev['date'],
            'home': sides['home']['team']['abbreviation'],
            'away': sides['away']['team']['abbreviation'],
            'status': status.value,
            'home_score': hs,
            'away_score': as_,
            'home_win': int(hs > as_) if hs is not None and as_ is not None else None,
            'game_type': SEASON_TYPES[ev['season']['type']],
            'neutral_site': bool(comp.get('neutralSite', False)),
            'venue': (comp.get('venue') or {}).get('fullName'),
        })
    df = pd.DataFrame(rows, columns=[*SCHEDULE_COLUMNS, *EXTRA_COLUMNS])
    df['start_utc'] = pd.to_datetime(df['start_utc'], utc=True)
    for col in ('home_score', 'away_score', 'home_win'):
        df[col] = df[col].astype('Int64')
    df = df.sort_values(['start_utc', 'game_id'], kind='stable').reset_index(drop=True)
    contract = check_schedule('nba', df)
    if contract:
        raise NBAScheduleError('; '.join(contract))
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
    """One season's schedule and results. `cache` defaults to `NBA_CACHE`;
    only a finished season before the current one is read from or written
    to it."""
    cache = cache if cache is not None else cache_dir()
    now = now or datetime.now(UTC)
    cacheable = cache is not None and season < current_season(now)
    path = cache / f'schedule_{season}.parquet' if cache is not None else None
    if cacheable and path is not None and path.exists():
        df: pd.DataFrame = pd.read_parquet(path)
        return df
    df = to_schedule(season_games(season, get), season)
    if cacheable and path is not None and finished(df):
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.tmp')
        df.to_parquet(tmp, index=False)
        tmp.replace(path)
    return df


def slate(schedule: pd.DataFrame, day: str) -> pd.DataFrame:
    """The games on one ESPN date ('2026-10-21'), earliest first."""
    return schedule[schedule['slate'] == day].reset_index(drop=True)
