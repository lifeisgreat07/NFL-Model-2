"""Which MLB sources can GitHub's runners read, and in what shape?

Stage 97 item 1 (Mark, 2026-11-11; docs/history/12-mlb-and-more-2026-11-11.md),
as Stage 51 was the NHL's and Stage 61 the NBA's. Every source is tested on a
runner, not assumed: the NBA's league feeds refused cloud servers, and ESPN
once refused GitHub's runners (#131) before answering them later (#357). This
probe reads two groups.

**Required**: the MLB Stats API (statsapi.mlb.com), the likely primary, each in
the shape a later stage needs, or the probe fails:

- one past day's schedule with its probable pitchers: each game's gamePk, a UTC
  start, its official date, two different clubs, a state, and its
  doubleheader flag and game number;
- a past doubleheader: two games between the same clubs on one date carry two
  gamePks and game numbers 1 and 2, so a game is told apart by its gamePk,
  never by its clubs and date;
- the season ahead's regular-season schedule, listed;
- a past game's box score, with the team totals a run-scoring and
  run-prevention rating is built from, and its pitchers (the first is the
  starter);
- the season's 30 clubs.

**Candidates**: each read is reported, and none decides the exit code:
Retrosheet's game log for the last finished season (the likely fallback),
ESPN's scoreboard and a past game's moneyline (the market for Model B, as the
NHL's and the NBA's backtests used ESPN's), and the live prices DraftKings,
Kalshi and Polymarket publish. Out of season a live price list may be empty;
that is reported, not failed.

On a runner, one `::notice` line sums every source up, so the answer can be
read from the run's annotations without signing in to read its log.

It writes nothing. Exit 0 means every required source answered in shape.

Run with: python -m src.sports.mlb.data_probe
"""
from __future__ import annotations

import io
import json
import os
import sys
import urllib.request
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

STATS = 'https://statsapi.mlb.com/api/v1'
#: A regular-season day with fifteen finished games.
PAST_DATE = '2025-07-04'
#: A day with a doubleheader between two clubs, both games final.
DOUBLEHEADER_DATE = '2025-04-26'
RETRO = 'https://www.retrosheet.org/gamelogs'
SITE = 'https://site.api.espn.com/apis/site/v2/sports/baseball/mlb'
CORE = 'https://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb'
DRAFTKINGS = 'https://sportsbook-nash.draftkings.com/api/sportscontent/dkusoh/v1/leagues/84240'
KALSHI = 'https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=KXMLBGAME&limit=200'
POLYMARKET = 'https://gamma-api.polymarket.com/events?tag_slug=mlb&limit=100'
#: Each club's totals a run-scoring and run-prevention rating reads.
BOX_STATS = {'batting': ('runs', 'hits', 'atBats', 'baseOnBalls'),
             'pitching': ('runs', 'earnedRuns', 'inningsPitched', 'strikeOuts')}
#: A regular season is 2,430 games; a season's list can run a little short of that before it is played.
SEASON_GAMES_FLOOR = 2400
CLUBS = 30
#: A Retrosheet game-log line holds the date, game number, weekday, visiting club, its league and game,
#: home club, its league and game, then the two scores: eleven fields before anything else.
RETRO_FIELDS = 11

Json = Any


def _games(data: Json) -> list[Json]:
    return [g for d in data.get('dates') or [] for g in d.get('games') or []]


def _club(g: Json, side: str) -> Any:
    return (((g.get('teams') or {}).get(side) or {}).get('team') or {}).get('id')


def check_schedule(data: Json) -> list[str]:
    games = _games(data)
    if not games:
        return ['no games on a date that had games']
    out = []
    for g in games:
        miss = [k for k in ('gamePk', 'officialDate', 'doubleHeader', 'gameNumber') if g.get(k) in (None, '')]
        if not g.get('gameDate') or not str(g['gameDate']).endswith('Z'):
            miss.append('a UTC start')
        if not _club(g, 'home') or not _club(g, 'away') or _club(g, 'home') == _club(g, 'away'):
            miss.append('two clubs')
        if not (g.get('status') or {}).get('detailedState'):
            miss.append('a state')
        if miss:
            out.append(f"game {g.get('gamePk', '?')}: missing {', '.join(miss)}")
    return out


def check_probables(data: Json) -> list[str]:
    """Every game of a past day names both clubs' probable pitchers."""
    games = _games(data)
    named = [g for g in games if all((((g.get('teams') or {}).get(s) or {}).get('probablePitcher') or {}).get('id')
                                     for s in ('home', 'away'))]
    return [] if games and len(named) == len(games) else [f'{len(named)} of {len(games)} games name both probables']


def check_doubleheader(data: Json) -> list[str]:
    """Two games between the same clubs on one date: two gamePks, game numbers 1 and 2."""
    pairs: dict[tuple[Any, Any], list[Json]] = {}
    for g in _games(data):
        pairs.setdefault((_club(g, 'away'), _club(g, 'home')), []).append(g)
    doubles = [gs for gs in pairs.values() if len(gs) == 2]
    if not doubles:
        return ['no doubleheader on a date that had one']
    out = []
    for gs in doubles:
        if len({g.get('gamePk') for g in gs}) != 2:
            out.append('a doubleheader whose two games share a gamePk')
        if sorted(int(g.get('gameNumber') or 0) for g in gs) != [1, 2]:
            out.append('a doubleheader without game numbers 1 and 2')
    return out


def check_season(data: Json) -> list[str]:
    n = data.get('totalGames')
    if not isinstance(n, int) or n < SEASON_GAMES_FLOOR:
        return [f'{n} games listed, fewer than {SEASON_GAMES_FLOOR}']
    return []


def check_box_score(data: Json) -> list[str]:
    teams = data.get('teams') or {}
    if not {'home', 'away'} <= set(teams):
        return ['no home and away in the box score']
    out = []
    for side in ('home', 'away'):
        t = teams[side] or {}
        stats = t.get('teamStats') or {}
        for group, names in BOX_STATS.items():
            missing = [n for n in names if n not in (stats.get(group) or {})]
            if missing:
                out.append(f"{side} {group}: no {', '.join(missing)}")
        if not t.get('pitchers'):
            out.append(f'{side}: no pitchers, so no starter')
    return out


def check_teams(data: Json) -> list[str]:
    ids = {t.get('id') for t in data.get('teams') or [] if t.get('id')}
    return [] if len(ids) == CLUBS else [f'{len(ids)} clubs, not {CLUBS}']


def check_retro(data: bytes) -> list[str]:
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        rows = z.read(z.namelist()[0]).decode('latin-1').splitlines()
    except (zipfile.BadZipFile, IndexError, KeyError):
        return [f'not a zip with a game log ({len(data)} bytes)']
    if len(rows) < SEASON_GAMES_FLOOR:
        return [f'{len(rows)} games, fewer than {SEASON_GAMES_FLOOR}']
    short = [r for r in rows if len(r.split(',')) < RETRO_FIELDS]
    return [f'{len(short)} lines too short to hold the score'] if short else []


def check_espn_scoreboard(data: Json) -> list[str]:
    return [] if data.get('events') else ['no games on a date that had games']


def check_odds(data: Json) -> list[str]:
    items = data.get('items') or []
    if not items:
        return ['no odds for a past game']
    lines = [(items[0].get(side) or {}).get('moneyLine') for side in ('homeTeamOdds', 'awayTeamOdds')]
    return ['a moneyline is missing for one club'] if None in lines else []


def check_events(data: Json) -> list[str]:
    """A live price list answered and holds something."""
    if isinstance(data, list):
        return [] if data else ['no events listed']
    if isinstance(data, dict) and any(data.get(k) for k in ('events', 'markets')):
        return []
    return ['no events listed']


def last_finished_season(now: datetime) -> int:
    """The World Series ends by early November; until then the last finished season is last year's."""
    return now.year if now.month >= 11 else now.year - 1


def fetch_bytes(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (NFL-Model-2 mlb data probe)'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body: bytes = r.read()
    return body


def fetch(url: str, timeout: int = 60) -> str:
    return fetch_bytes(url, timeout).decode('utf-8', 'replace')


def _first_final(get: Callable[[str], str]) -> int:
    for g in _games(json.loads(get(f'{STATS}/schedule?sportId=1&date={PAST_DATE}'))):
        if (g.get('status') or {}).get('detailedState') == 'Final':
            return int(g['gamePk'])
    raise LookupError(f'no finished game on {PAST_DATE}')


def _first_espn_event(get: Callable[[str], str]) -> str:
    events = json.loads(get(f"{SITE}/scoreboard?dates={PAST_DATE.replace('-', '')}")).get('events') or []
    if not events:
        raise LookupError(f'no ESPN game on {PAST_DATE}')
    return str(events[0]['id'])


Source = tuple[str, Callable[[], Any], Callable[[Any], list[str]]]


def required(get: Callable[[str], str], now: datetime) -> list[Source]:
    ahead = last_finished_season(now) + 1
    day = f'{STATS}/schedule?sportId=1&date={PAST_DATE}&hydrate=probablePitcher'
    return [
        (f'Stats API schedule {PAST_DATE}', lambda: json.loads(get(day)), check_schedule),
        (f'Stats API probable pitchers {PAST_DATE}', lambda: json.loads(get(day)), check_probables),
        (f'Stats API doubleheader {DOUBLEHEADER_DATE}',
         lambda: json.loads(get(f'{STATS}/schedule?sportId=1&date={DOUBLEHEADER_DATE}')), check_doubleheader),
        (f'Stats API season {ahead}',
         lambda: json.loads(get(f'{STATS}/schedule?sportId=1&season={ahead}&gameType=R')), check_season),
        ('Stats API box score', lambda: json.loads(get(f'{STATS}/game/{_first_final(get)}/boxscore')),
         check_box_score),
        (f'Stats API clubs {ahead}', lambda: json.loads(get(f'{STATS}/teams?sportId=1&season={ahead}')), check_teams),
    ]


def candidates(get: Callable[[str], str], get_bytes: Callable[[str], bytes], now: datetime) -> list[Source]:
    # Retrosheet posts a season's game log some weeks after the World Series (on 2026-11-11 the 2026 log
    # was a 404 and 2025's was there), so the season before the last is read for its shape.
    retro = last_finished_season(now) - 1
    return [
        (f'Retrosheet game log {retro}', lambda: get_bytes(f'{RETRO}/gl{retro}.zip'), check_retro),
        ('ESPN scoreboard', lambda: json.loads(get(f"{SITE}/scoreboard?dates={PAST_DATE.replace('-', '')}")),
         check_espn_scoreboard),
        ('ESPN past moneyline', lambda: json.loads(get('{c}/events/{e}/competitions/{e}/odds'.format(
            c=CORE, e=_first_espn_event(get)))), check_odds),
        ('DraftKings MLB', lambda: json.loads(get(DRAFTKINGS)), check_events),
        ('Kalshi MLB game markets', lambda: json.loads(get(KALSHI)), check_events),
        ('Polymarket MLB', lambda: json.loads(get(POLYMARKET)), check_events),
    ]


def report(name: str, read: Callable[[], Any], check: Callable[[Any], list[str]], seen: list[str]) -> bool:
    try:
        data = read()
    except Exception as exc:  # the point is to report it, whatever it is
        print(f'  {name}: UNREACHABLE ({type(exc).__name__}: {exc})')
        seen.append(f'{name}: UNREACHABLE')
        return False
    problems = check(data)
    seen.append(f'{name}: {"ok" if not problems else "NOT usable"}')
    print(f'  {name}: {"ok" if not problems else "NOT usable as-is"}')
    for p in problems:
        print(f'    {p}')
    return not problems


def main(get: Callable[[str], str] = fetch, get_bytes: Callable[[str], bytes] = fetch_bytes,
         now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    seen: list[str] = []
    print('Required (the Stats API, the likely primary):')
    ok = all([report(*src, seen=seen) for src in required(get, now)])
    print('Candidates (reported; none decides the result):')
    for src in candidates(get, get_bytes, now):
        report(*src, seen=seen)
    print('MLB required sources: all usable from here' if ok else 'MLB required sources: NOT all usable from here')
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        # One annotation with every answer: annotations can be read without
        # signing in, a run's log cannot.
        print('::notice title=MLB data probe::' + '; '.join(seen))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
