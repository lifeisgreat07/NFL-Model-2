"""Can GitHub's runners read ESPN's public scoreboard, and is it shaped as expected?

Stage 15 (CLAUDE.md, "TV channel per game"). The channel data would come from
ESPN's undocumented scoreboard feed, which was reachable from markys on
2026-09-26. Before any code depends on it, the plan asks for the first thing
checked to be whether GitHub's runners can reach it at all: a scheduled
refresh that works on one laptop and not in Actions is no refresh.

This reads regular-season weeks 1-4 of 2026 and reports, per week, how many
games came back and how many carry everything the later stages need: an event
id, a kickoff, two team abbreviations, a status, and at least one broadcast
network. It writes nothing. Exit code 0 means every week was reachable and
every game was complete; 1 means something was missing, and the report says
what.

Run with: python src/espn_probe.py [--weeks 1 2 3 4] [--season 2026]
"""
import argparse
import json
import sys
import urllib.request

URL = ('https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard'
       '?seasontype=2&week={week}&dates={season}')


def check_event(event):
    """The fields a later stage reads from one event; returns the missing ones."""
    missing = []
    comps = event.get('competitions') or [{}]
    comp = comps[0]
    if not event.get('id'):
        missing.append('id')
    if not event.get('date'):
        missing.append('date')
    teams = [c.get('team', {}).get('abbreviation') for c in comp.get('competitors', [])]
    sides = sorted(c.get('homeAway') or '' for c in comp.get('competitors', []))
    if len([t for t in teams if t]) != 2 or sides != ['away', 'home']:
        missing.append('two teams, home and away')
    if not (event.get('status') or {}).get('type', {}).get('name'):
        missing.append('status')
    names = [n for b in comp.get('broadcasts') or [] for n in b.get('names') or []]
    if not names:
        missing.append('broadcast')
    return missing


def summarise(payload):
    """(games, complete, problems) for one week's payload."""
    events = payload.get('events') or []
    problems = []
    for e in events:
        miss = check_event(e)
        if miss:
            problems.append(f"{e.get('id', '?')}: missing {', '.join(miss)}")
    return len(events), len(events) - len(problems), problems


def fetch(week, season, timeout=20):
    req = urllib.request.Request(URL.format(week=week, season=season),
                                 headers={'User-Agent': 'NFL-Model-2 espn_probe'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--weeks', type=int, nargs='+', default=[1, 2, 3, 4])
    ap.add_argument('--season', type=int, default=2026)
    args = ap.parse_args(argv)
    ok = True
    for week in args.weeks:
        try:
            payload = fetch(week, args.season)
        except Exception as exc:  # the point is to report it, whatever it is
            print(f'week {week}: UNREACHABLE ({type(exc).__name__}: {exc})')
            ok = False
            continue
        games, complete, problems = summarise(payload)
        print(f'week {week}: {games} games, {complete} complete')
        for p in problems:
            print(f'  {p}')
        if games == 0 or problems:
            ok = False
    print('ESPN scoreboard: reachable and complete' if ok else 'ESPN scoreboard: NOT usable as-is')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
