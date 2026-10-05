"""Can GitHub's runners read every NHL source the go/no-go relies on?

Stage 51 item 1. `docs/nhl-data.md` was written from reads on the local
Windows machine, and a home connection is not a runner: ESPN's scoreboard
answers GitHub's runners with HTTP 403 (#131) while answering a browser.
So each source is read again from where the scheduled jobs will run, and
judged on the shape a later stage needs, not only on answering:

- the league's schedule: games with an id, a UTC start, two teams and a state;
- a finished game's play-by-play: shots with coordinates and the goalie in net;
- its box score: exactly one starting goalie per team;
- the league's live odds feed: a two-way moneyline for both teams;
- ESPN's odds for a past game: a moneyline for both teams (Model B's history);
- the fallback's files on GitHub (SportsDataverse);
- Daily Faceoff's starting goalies, with their Confirmed/Likely label.

It writes nothing. Exit 0 means every source answered with the shape asked
for; 1 means at least one did not, and the report says which and why.

Run with: python -m src.sports.nhl.data_probe
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from collections.abc import Callable
from typing import Any

WEB = 'https://api-web.nhle.com/v1'
#: A finished regular-season game used for the play-by-play and box score
#: checks (Toronto, 2025-26), and an ESPN event from 2024-25 with odds.
FINISHED_GAME = 2025020672
SCHEDULE_DATE = '2026-10-06'
ESPN_ODDS = ('https://sports.core.api.espn.com/v2/sports/hockey/leagues/nhl/'
             'events/{e}/competitions/{e}/odds')
ESPN_SCOREBOARD = 'https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard?dates={d}'
ESPN_PAST_DATE = '20241215'
FALLBACK = 'https://api.github.com/repos/sportsdataverse/fastRhockey-nhl-data/contents/nhl'
FACEOFF = 'https://www.dailyfaceoff.com/starting-goalies'
SHOT_TYPES = ('shot-on-goal', 'goal', 'missed-shot')

Json = Any


def check_schedule(data: Json) -> list[str]:
    games = [g for day in data.get('gameWeek', []) for g in day.get('games', [])]
    if not games:
        return ['no games in the week']
    problems = []
    for g in games:
        miss = [k for k in ('id', 'startTimeUTC', 'gameState') if not g.get(k)]
        home = (g.get('homeTeam') or {}).get('abbrev')
        away = (g.get('awayTeam') or {}).get('abbrev')
        if not home or not away or home == away:
            miss.append('two teams')
        if g.get('startTimeUTC') and not str(g['startTimeUTC']).endswith('Z'):
            miss.append('a UTC start')
        if miss:
            problems.append(f"game {g.get('id', '?')}: missing {', '.join(miss)}")
    return problems


def check_play_by_play(data: Json) -> list[str]:
    shots = [p for p in data.get('plays', []) if p.get('typeDescKey') in SHOT_TYPES]
    if len(shots) < 20:
        return [f'only {len(shots)} shots in a finished game']
    no_xy = sum(1 for s in shots if 'xCoord' not in (s.get('details') or {}))
    no_goalie = sum(1 for s in shots if s.get('typeDescKey') == 'shot-on-goal'
                    and 'goalieInNetId' not in (s.get('details') or {}))
    out = []
    if no_xy:
        out.append(f'{no_xy} of {len(shots)} shots have no coordinates')
    if no_goalie:
        out.append(f'{no_goalie} shots on goal have no goalie in net')
    return out


def check_box_score(data: Json) -> list[str]:
    stats = data.get('playerByGameStats') or {}
    out = []
    for side in ('homeTeam', 'awayTeam'):
        starters = [g for g in (stats.get(side) or {}).get('goalies', []) if g.get('starter')]
        if len(starters) != 1:
            out.append(f'{side}: {len(starters)} starting goalies flagged, not 1')
    return out


def _has_moneyline(team: Json) -> bool:
    return any(o.get('description') == 'MONEY_LINE_2_WAY' and o.get('value') is not None
               for o in team.get('odds') or [])


def check_live_odds(data: Json) -> list[str]:
    games = data.get('games')
    if games is None:
        return ['no games list in the odds feed']
    if not games:
        return []  # a day with no games is not a broken feed
    missing = [str(g.get('gameId', '?')) for g in games
               if not (_has_moneyline(g.get('homeTeam') or {}) and _has_moneyline(g.get('awayTeam') or {}))]
    return [f'no two-way moneyline for games {", ".join(missing)}'] if missing else []


def check_espn_odds(data: Json) -> list[str]:
    items = data.get('items') or []
    if not items:
        return ['no odds for a past game']
    item = items[0]
    lines = [(item.get(side) or {}).get('moneyLine') for side in ('homeTeamOdds', 'awayTeamOdds')]
    if None in lines:
        return ['a moneyline is missing for one team']
    return []


def check_fallback(data: Json) -> list[str]:
    names = {x.get('name') for x in data} if isinstance(data, list) else set()
    missing = sorted({'pbp', 'schedules', 'goalie_box'} - names)
    return [f'the fallback has no {", ".join(missing)} folder'] if missing else []


def check_faceoff(page: str) -> list[str]:
    out = []
    if '__NEXT_DATA__' not in page:
        out.append('no embedded data payload')
    if 'homeGoalieName' not in page:
        out.append('no goalie names')
    if not re.search(r'\b(Confirmed|Likely)\b', page):
        out.append('no Confirmed or Likely label')
    return out


def fetch(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (NFL-Model-2 nhl data probe)'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body: bytes = r.read()
    return body.decode('utf-8', 'replace')


def _espn_odds_for_past_game(get: Callable[[str], str]) -> Json:
    events = json.loads(get(ESPN_SCOREBOARD.format(d=ESPN_PAST_DATE))).get('events', [])
    if not events:
        return {}
    return json.loads(get(ESPN_ODDS.format(e=events[0]['id'])))


def sources(get: Callable[[str], str]) -> list[tuple[str, Callable[[], Json], Callable[[Json], list[str]]]]:
    return [
        ('league schedule', lambda: json.loads(get(f'{WEB}/schedule/{SCHEDULE_DATE}')), check_schedule),
        ('league play-by-play', lambda: json.loads(get(f'{WEB}/gamecenter/{FINISHED_GAME}/play-by-play')),
         check_play_by_play),
        ('league box score', lambda: json.loads(get(f'{WEB}/gamecenter/{FINISHED_GAME}/boxscore')), check_box_score),
        ('league live odds', lambda: json.loads(get(f'{WEB}/partner-game/US/now')), check_live_odds),
        ('ESPN past odds', lambda: _espn_odds_for_past_game(get), check_espn_odds),
        ('SportsDataverse fallback', lambda: json.loads(get(FALLBACK)), check_fallback),
        ('Daily Faceoff goalies', lambda: get(FACEOFF), check_faceoff),
    ]


def main(argv: list[str] | None = None, get: Callable[[str], str] = fetch) -> int:
    ok = True
    for name, read, check in sources(get):
        try:
            data = read()
        except Exception as exc:  # the point is to report it, whatever it is
            print(f'{name}: UNREACHABLE ({type(exc).__name__}: {exc})')
            ok = False
            continue
        problems = check(data)
        print(f'{name}: {"ok" if not problems else "NOT usable as-is"}')
        for p in problems:
            print(f'  {p}')
        ok = ok and not problems
    print('NHL sources: all usable from here' if ok else 'NHL sources: NOT all usable from here')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
