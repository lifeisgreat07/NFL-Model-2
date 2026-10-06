"""Which NBA sources can GitHub's runners read, and in what shape?

Stage 61's first step, the NBA's Stage 51. From the local Windows machine on
2026-10-05, ESPN's public API answered for everything, while the league's
own feeds refused it (`cdn.nba.com` 403) or timed out (`stats.nba.com`).
ESPN refuses GitHub's runners (#131), and Mark ruled out routing around
that. So the NBA's live run, which runs on a runner, can only be built on a
source a runner can read. This probe reads two groups.

**Required**: what the live run will read, each of which must answer in the
shape it needs, or the probe fails:

- SportsDataverse's hoopR schedule file for the current season (the
  repository is on GitHub, so a runner can read it);
- its team box and player box files for the last finished season.

**Candidates**: each read is reported, and none decides the exit code.
They are ESPN's scoreboard, a box score, a past game's odds and the injury
report, and the league's own scoreboard, odds and schedule on
`cdn.nba.com`. One that answers from a runner is worth a later stage's
look: the league's odds feed would give a live Model B a price
(`docs/nba-data.md`).

It writes nothing. Exit 0 means every required source answered in shape.

Run with: python -m src.sports.nba.data_probe
"""
from __future__ import annotations

import json
import sys
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

SITE = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba'
CORE = 'https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba'
PAST_DATE = '20250315'
HOOPR = 'https://raw.githubusercontent.com/sportsdataverse/hoopR-nba-data/main/nba'
CDN = 'https://cdn.nba.com/static/json'
#: A parquet file starts and ends with these four bytes.
PARQUET_MAGIC = b'PAR1'
#: The box-score figures possessions are built from.
POSSESSION_STATS = ('fieldGoalsMade-fieldGoalsAttempted', 'freeThrowsMade-freeThrowsAttempted',
                    'offensiveRebounds', 'turnovers')

Json = Any


def check_scoreboard(data: Json) -> list[str]:
    events = data.get('events') or []
    if not events:
        return ['no games on a date that had games']
    out = []
    for ev in events:
        comp = (ev.get('competitions') or [{}])[0]
        sides = {c.get('homeAway'): (c.get('team') or {}).get('abbreviation') for c in comp.get('competitors') or []}
        miss = [k for k in ('id', 'date') if not ev.get(k)]
        if not sides.get('home') or not sides.get('away') or sides['home'] == sides['away']:
            miss.append('two teams')
        if ev.get('date') and not str(ev['date']).endswith('Z'):
            miss.append('a UTC start')
        if not ((comp.get('status') or {}).get('type') or {}).get('name'):
            miss.append('a state')
        if miss:
            out.append(f"game {ev.get('id', '?')}: missing {', '.join(miss)}")
    return out


def check_box_score(data: Json) -> list[str]:
    teams = (data.get('boxscore') or {}).get('teams') or []
    if len(teams) != 2:
        return [f'{len(teams)} teams in the box score, not 2']
    out = []
    for t in teams:
        names = {s.get('name') for s in t.get('statistics') or []}
        missing = [s for s in POSSESSION_STATS if s not in names]
        if missing:
            out.append(f"{(t.get('team') or {}).get('abbreviation', '?')}: no {', '.join(missing)}")
    return out


def check_odds(data: Json) -> list[str]:
    items = data.get('items') or []
    if not items:
        return ['no odds for a past game']
    lines = [(items[0].get(side) or {}).get('moneyLine') for side in ('homeTeamOdds', 'awayTeamOdds')]
    return ['a moneyline is missing for one team'] if None in lines else []


def check_injuries(data: Json) -> list[str]:
    teams = data.get('injuries')
    if not isinstance(teams, list) or not teams:
        return ['no injury list']
    players = [p for t in teams for p in t.get('injuries') or []]
    if not players:
        return ['an injury list with no players']
    unlabelled = [p for p in players if not p.get('status')]
    return [f'{len(unlabelled)} of {len(players)} injuries have no status'] if unlabelled else []


def check_parquet(data: bytes) -> list[str]:
    if len(data) < 12 or not (data.startswith(PARQUET_MAGIC) and data.endswith(PARQUET_MAGIC)):
        return [f'not a parquet file ({len(data)} bytes)']
    return []


def check_cdn_scoreboard(data: Json) -> list[str]:
    games = (data.get('scoreboard') or {}).get('games')
    return [] if isinstance(games, list) else ['no games list']


def check_cdn_odds(data: Json) -> list[str]:
    games = data.get('games')
    return [] if isinstance(games, list) else ['no games list']


def check_cdn_schedule(data: Json) -> list[str]:
    dates = (data.get('leagueSchedule') or {}).get('gameDates')
    return [] if isinstance(dates, list) and dates else ['no game dates']


def season_end_year(now: datetime) -> int:
    """hoopR names a season by the year it ends: 2026-27 is 2027. A season
    starts in October."""
    return now.year + 1 if now.month >= 10 else now.year


def fetch_bytes(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (NFL-Model-2 nba data probe)'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body: bytes = r.read()
    return body


def fetch(url: str, timeout: int = 30) -> str:
    return fetch_bytes(url, timeout).decode('utf-8', 'replace')


def _first_final_event(get: Callable[[str], str]) -> str:
    events = json.loads(get(f'{SITE}/scoreboard?dates={PAST_DATE}')).get('events') or []
    for ev in events:
        if (((ev.get('competitions') or [{}])[0].get('status') or {}).get('type') or {}).get('completed'):
            return str(ev['id'])
    raise LookupError(f'no finished game on {PAST_DATE}')


Source = tuple[str, Callable[[], Any], Callable[[Any], list[str]]]


def required(get_bytes: Callable[[str], bytes], now: datetime) -> list[Source]:
    end = season_end_year(now)
    return [
        (f'hoopR schedule {end}', lambda: get_bytes(f'{HOOPR}/schedules/parquet/nba_schedule_{end}.parquet'),
         check_parquet),
        (f'hoopR team box {end - 1}', lambda: get_bytes(f'{HOOPR}/team_box/parquet/team_box_{end - 1}.parquet'),
         check_parquet),
        (f'hoopR player box {end - 1}',
         lambda: get_bytes(f'{HOOPR}/player_box/parquet/player_box_{end - 1}.parquet'), check_parquet),
    ]


def candidates(get: Callable[[str], str]) -> list[Source]:
    return [
        ('ESPN scoreboard', lambda: json.loads(get(f'{SITE}/scoreboard?dates={PAST_DATE}')), check_scoreboard),
        ('ESPN box score', lambda: json.loads(get(f'{SITE}/summary?event={_first_final_event(get)}')), check_box_score),
        ('ESPN past odds', lambda: json.loads(get('{c}/events/{e}/competitions/{e}/odds'.format(
            c=CORE, e=_first_final_event(get)))), check_odds),
        ('ESPN injuries', lambda: json.loads(get(f'{SITE}/injuries')), check_injuries),
        ('league scoreboard (cdn.nba.com)',
         lambda: json.loads(get(f'{CDN}/liveData/scoreboard/todaysScoreboard_00.json')), check_cdn_scoreboard),
        ('league odds (cdn.nba.com)', lambda: json.loads(get(f'{CDN}/liveData/odds/odds_todaysGames.json')),
         check_cdn_odds),
        ('league schedule (cdn.nba.com)', lambda: json.loads(get(f'{CDN}/staticData/scheduleLeagueV2.json')),
         check_cdn_schedule),
    ]


def report(name: str, read: Callable[[], Any], check: Callable[[Any], list[str]]) -> bool:
    try:
        data = read()
    except Exception as exc:  # the point is to report it, whatever it is
        print(f'  {name}: UNREACHABLE ({type(exc).__name__}: {exc})')
        return False
    problems = check(data)
    print(f'  {name}: {"ok" if not problems else "NOT usable as-is"}')
    for p in problems:
        print(f'    {p}')
    return not problems


def main(argv: list[str] | None = None, get: Callable[[str], str] = fetch,
         get_bytes: Callable[[str], bytes] = fetch_bytes, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    print('Required (the live run reads these):')
    ok = all([report(*src) for src in required(get_bytes, now)])
    print('Candidates (reported; none decides the result):')
    for src in candidates(get):
        report(*src)
    print('NBA required sources: all usable from here' if ok else 'NBA required sources: NOT all usable from here')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
