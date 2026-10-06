"""The NHL's injury report, read for each saved pick (Stage 55 item 3).

The source is SportsDataverse's `espn_nhl_injuries` release
(`docs/nhl-data.md` section 4): one parquet file per season, ESPN's injury
list as it stood each day it was read (`as_of_date`). This takes the latest
day in the file and, for one game, each club's players on it with their
status (Out, Day-To-Day, Injured Reserve, Suspension).

Context only, as the NFL's injury data turned out to be: no model reads it.
It is stored in the pick with where it came from, the day the list is as of
and when it was read, so a reader can see what was known when the pick was
saved. A list older than the pick by days says so through its `as_of`; a
failed read stores None and the pick is saved regardless.

ESPN numbers seasons by the year they end, so the NHL's 2026 (2026-27) is
`injuries_2027.parquet`.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any

import pandas as pd

from src.sports.nhl import teams

RELEASE = 'https://github.com/sportsdataverse/sportsdataverse-data/releases/download/espn_nhl_injuries'
NAME = 'espn_nhl_injuries'
#: The columns this reads; a file without them is refused, not guessed at.
COLUMNS = ('as_of_date', 'team_display_name', 'athlete_display_name', 'athlete_position', 'status')


class InjurySourceError(ValueError):
    """The file is not the injury list this reads."""


def source(season: int) -> str:
    """The file for the NHL season starting in `season`."""
    return f'{RELEASE}/injuries_{season + 1}.parquet'


def latest(raw: bytes) -> tuple[str, pd.DataFrame]:
    """The latest day in the file and that day's list, one row per player,
    with the club as its abbreviation. A club the names do not match is
    refused, so a renamed club is reported rather than dropped."""
    try:
        df = pd.read_parquet(io.BytesIO(raw))
    except Exception as exc:  # pyarrow raises its own types for a bad file
        raise InjurySourceError(f'not a parquet file: {exc}') from exc
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise InjurySourceError(f'columns missing: {missing}')
    if df.empty:
        raise InjurySourceError('the file has no rows')
    day = str(df['as_of_date'].astype(str).max())
    today = df[df['as_of_date'].astype(str) == day].copy()
    today['team'] = [teams.abbr_for(str(n)) for n in today['team_display_name']]
    unknown = sorted(set(today.loc[today['team'].isna(), 'team_display_name'].astype(str)))
    if unknown:
        raise InjurySourceError(f'clubs not recognised: {unknown}')
    today = today.drop_duplicates(['team', 'athlete_display_name'], keep='last')
    return day, today


def for_game(day: str, table: pd.DataFrame, home: str, away: str, read: datetime) -> dict[str, Any]:
    """What the pick stores: the source, the list's day, when it was read,
    and each side's players sorted by name."""
    def side(club: str) -> list[dict[str, str]]:
        rows = table[table['team'] == club].sort_values('athlete_display_name', kind='stable')
        return [{'name': str(r.athlete_display_name), 'position': str(r.athlete_position), 'status': str(r.status)}
                for r in rows.itertuples()]
    return {'source': NAME, 'as_of': day, 'read_utc': read.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'home': side(home), 'away': side(away)}
