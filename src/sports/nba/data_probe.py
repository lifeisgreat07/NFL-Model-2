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

Stage 65 (Mark, 2026-10-09: the NBA goes live on GitHub's runners only)
adds the candidates a live run would need beyond the schedule, none of them
ESPN's own API or the league's:

- a pre-game price: DraftKings' NBA moneylines (the book the NHL's price
  comes from), Kalshi's NBA game markets and Polymarket's NBA games, each a
  public read with no key;
- an injury list: SportsDataverse's `espn_nba_injuries` release, the same
  daily copy of ESPN's list the NHL's run reads (`src/sports/nhl/injuries.py`),
  and its `timestamp.json`.

On a runner, one `::notice` line sums every source up, so the answer can be
read from the run's annotations without signing in to read its log.

It writes nothing. Exit 0 means every required source answered in shape.

Run with: python -m src.sports.nba.data_probe
"""
from __future__ import annotations

import json
import os
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
INJURIES = 'https://github.com/sportsdataverse/sportsdataverse-data/releases/download/espn_nba_injuries'
DRAFTKINGS = 'https://sportsbook-nash.draftkings.com/api/sportscontent/dkusoh/v1/leagues/42648'
KALSHI = 'https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=KXNBAGAME&status=open&limit=200'
POLYMARKET = 'https://gamma-api.polymarket.com/events?tag_slug=nba&closed=false&limit=100'
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


def check_draftkings(data: Json) -> list[str]:
    """A moneyline for a game: an event with a start time and a Moneyline
    market whose two selections each carry decimal odds above 1."""
    events = {str(e.get('id')): e for e in data.get('events') or []}
    if not events:
        return ['no NBA events']
    lines = [m for m in data.get('markets') or [] if (m.get('marketType') or {}).get('name') == 'Moneyline']
    if not lines:
        return ['no Moneyline market']
    picks: dict[str, list[float]] = {}
    for s in data.get('selections') or []:
        if isinstance(s.get('trueOdds'), (int, float)) and s['trueOdds'] > 1:
            picks.setdefault(str(s.get('marketId')), []).append(float(s['trueOdds']))
    priced = [m for m in lines if len(picks.get(str(m.get('id')), [])) == 2
              and (events.get(str(m.get('eventId'))) or {}).get('startEventDate')]
    return [] if priced else ['no game with both sides of a moneyline and a start time']


def check_kalshi(data: Json) -> list[str]:
    """A price on a game's winner: an NBA game market with a bid and an ask."""
    markets = [m for m in data.get('markets') or [] if str(m.get('event_ticker', '')).startswith('KXNBAGAME-')]
    if not markets:
        return ['no NBA game markets']

    def quote(m: dict[str, Any], k: str) -> float:
        try:
            return float(m.get(k) or 0)
        except ValueError:
            return 0.0
    quoted = [m for m in markets if 0 < quote(m, 'yes_bid_dollars') <= quote(m, 'yes_ask_dollars') < 1]
    return [] if quoted else ['no NBA game market with a bid and an ask']


def check_polymarket(data: Json) -> list[str]:
    """A price on a game: an event tagged as a game, with a two-way market
    whose two prices sum to about 1."""
    if not isinstance(data, list):
        return ['no list of events']
    games = [e for e in data if any(t.get('slug') == 'games' for t in e.get('tags') or [])]
    if not games:
        return ['no NBA game events']
    for e in games:
        for m in e.get('markets') or []:
            try:
                prices = [float(x) for x in json.loads(m.get('outcomePrices') or '[]')]
            except (TypeError, ValueError):
                continue
            if len(prices) == 2 and abs(sum(prices) - 1) < 0.05:
                return []
    return ['no NBA game with a two-way price']


def check_timestamp(data: Json) -> list[str]:
    return [] if isinstance(data, dict) and data.get('last_updated') else ['no last_updated']


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


def candidates(get: Callable[[str], str], get_bytes: Callable[[str], bytes] | None = None,
               now: datetime | None = None) -> list[Source]:
    end = season_end_year(now or datetime.now(UTC))
    stage65: list[Source] = [
        ('DraftKings NBA moneylines', lambda: json.loads(get(DRAFTKINGS)), check_draftkings),
        ('Kalshi NBA game markets', lambda: json.loads(get(KALSHI)), check_kalshi),
        ('Polymarket NBA games', lambda: json.loads(get(POLYMARKET)), check_polymarket),
        ('SportsDataverse injuries timestamp', lambda: json.loads(get(f'{INJURIES}/timestamp.json')),
         check_timestamp),
    ]
    if get_bytes is not None:
        stage65.append((f'SportsDataverse injuries {end}',
                        lambda: get_bytes(f'{INJURIES}/injuries_{end}.parquet'), check_parquet))
    return stage65 + [
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


def report(name: str, read: Callable[[], Any], check: Callable[[Any], list[str]],
           seen: list[str] | None = None) -> bool:
    try:
        data = read()
    except Exception as exc:  # the point is to report it, whatever it is
        print(f'  {name}: UNREACHABLE ({type(exc).__name__}: {exc})')
        if seen is not None:
            seen.append(f'{name}: UNREACHABLE')
        return False
    problems = check(data)
    if seen is not None:
        seen.append(f'{name}: {"ok" if not problems else "NOT usable"}')
    print(f'  {name}: {"ok" if not problems else "NOT usable as-is"}')
    for p in problems:
        print(f'    {p}')
    return not problems


def main(argv: list[str] | None = None, get: Callable[[str], str] = fetch,
         get_bytes: Callable[[str], bytes] = fetch_bytes, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    seen: list[str] = []
    print('Required (the live run reads these):')
    ok = all([report(*src, seen=seen) for src in required(get_bytes, now)])
    print('Candidates (reported; none decides the result):')
    for src in candidates(get, get_bytes, now):
        report(*src, seen=seen)
    print('NBA required sources: all usable from here' if ok else 'NBA required sources: NOT all usable from here')
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        # One annotation with every answer: annotations can be read without
        # signing in, a run's log cannot.
        print('::notice title=NBA data probe::' + '; '.join(seen))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
