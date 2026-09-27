"""Can GitHub's runners read the league's own schedule page, with a network per game?

Stage 15 (CLAUDE.md, "TV channel per game"). ESPN's scoreboard, the first
candidate, answers GitHub's runners with HTTP 403 (#131, closed 2026-09-27), so
Mark chose to probe another automatic source rather than route around the
block. The candidate is www.nfl.com/schedules/<season>/by-week/week-<N>, whose
server-rendered HTML embeds each game's data in a Next.js payload -- not a
documented API, so this checks its shape as well as whether it answers.

For each week it reports how many games came back and how many carry
everything a later stage needs: an elias id (the key that joins to nflverse's
old_game_id), a kickoff, two teams, a NATIONAL or REGIONAL territory, at least
one network, and a season, week and season type that match what was asked
for. The last check exists because nfl.com's ways-to-watch page served another
season's slate under the same week number on 2026-09-27: a page that answers
with the wrong week must fail, not count. It writes nothing. Exit code 0 means
every week was reachable and every game complete; 1 means something was
missing, and the report says what.

Run with: python src/nfl_schedule_probe.py [--weeks 1 2 3 4] [--season 2026]
"""
import argparse
import json
import re
import sys
import urllib.request

URL = 'https://www.nfl.com/schedules/{season}/by-week/week-{week}'
PUSH_RE = re.compile(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)')
TERRITORIES = ('NATIONAL', 'REGIONAL')


def extract_games(page):
    """Every distinct game object in the page's embedded payload, in page order."""
    payload = ''.join(json.loads(m.group(1)) for m in PUSH_RE.finditer(page))
    decoder = json.JSONDecoder()
    games, seen = [], set()
    for m in re.finditer(r'\{\s*"id"\s*:\s*"', payload):
        try:
            obj, _ = decoder.raw_decode(payload, m.start())
        except ValueError:
            continue
        if 'broadcastInfo' in obj and 'homeTeam' in obj and obj['id'] not in seen:
            seen.add(obj['id'])
            games.append(obj)
    return games


def elias_id(game):
    for ext in game.get('externalIds') or []:
        if ext.get('source') == 'elias' and re.fullmatch(r'\d{10}', str(ext.get('id', ''))):
            return ext['id']
    return None


def check_game(game, season, week):
    """What one game lacks for a later stage; an empty list means complete."""
    missing = []
    if not elias_id(game):
        missing.append('elias id')
    if not re.match(r'\d{4}-\d\d-\d\dT\d\d:\d\d', str(game.get('time') or '')):
        missing.append('kickoff')
    home = (game.get('homeTeam') or {}).get('fullName')
    away = (game.get('awayTeam') or {}).get('fullName')
    if not home or not away or home == away:
        missing.append('two teams')
    info = game.get('broadcastInfo') or {}
    if info.get('territory') not in TERRITORIES:
        missing.append('territory')
    if not [n for n in info.get('homeNetworkChannels') or [] if n]:
        missing.append('network')
    if (game.get('season'), game.get('week'), game.get('seasonType')) != (season, week, 'REG'):
        missing.append(f'this week (says {game.get("season")} week {game.get("week")} {game.get("seasonType")})')
    return missing


def summarise(games, season, week):
    """(games, complete, problems) for one week."""
    problems = []
    for g in games:
        miss = check_game(g, season, week)
        if miss:
            problems.append(f"{elias_id(g) or g.get('id', '?')}: missing {', '.join(miss)}")
    return len(games), len(games) - len(problems), problems


def fetch(week, season, timeout=20):
    req = urllib.request.Request(URL.format(week=week, season=season),
                                 headers={'User-Agent': 'NFL-Model-2 nfl_schedule_probe'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', 'replace')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--weeks', type=int, nargs='+', default=[1, 2, 3, 4])
    ap.add_argument('--season', type=int, default=2026)
    args = ap.parse_args(argv)
    ok = True
    for week in args.weeks:
        try:
            page = fetch(week, args.season)
        except Exception as exc:  # the point is to report it, whatever it is
            print(f'week {week}: UNREACHABLE ({type(exc).__name__}: {exc})')
            ok = False
            continue
        games, complete, problems = summarise(extract_games(page), args.season, week)
        print(f'week {week}: {games} games, {complete} complete')
        for p in problems:
            print(f'  {p}')
        if games == 0 or problems:
            ok = False
    print('nfl.com schedule: reachable and complete' if ok else 'nfl.com schedule: NOT usable as-is')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
