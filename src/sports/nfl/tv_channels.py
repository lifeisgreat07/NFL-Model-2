"""TV channel per game, from the league's own schedule page, checked before shown.

Stage 15 (CLAUDE.md, "TV channel per game"). ESPN's scoreboard refuses
GitHub's runners (#131); nfl.com's by-week schedule page does not (#132), and
its HTML embeds each game's data: the networks, a NATIONAL or REGIONAL
territory, the kickoff in UTC, both teams, and an `elias` id that equals
nflverse's `old_game_id`. It is not a documented API, so nothing about it is
assumed. Nothing can guarantee a third party is right, so the guarantee is the
narrower, checkable one the plan states: the page never shows a channel that
failed a check, and every channel it shows can be traced to where and when it
was read.

The checks, in the order the plan numbers them:

1. Exact join, then a cross-check. A game is matched on elias id =
   nflverse old_game_id, never on names or dates. Then nfl.com's two teams
   and kickoff must agree with that nflverse row; any disagreement holds the
   channel back and is reported.
2. A closed list of networks (NETWORKS). A name outside it is not shown,
   and is reported, until a person adds it here in a reviewed PR; the
   game's listed networks still show. The Spanish-
   language and alternate feeds nfl.com lists beside the main network
   (ALTERNATE_FEEDS) are known and deliberately not shown -- the card names
   where to watch the game, not every feed of it -- and are not reported,
   because a report that fires on every Monday night game gets ignored.
3. Slot rules. Thursday night is Prime Video, Sunday night NBC, Monday night
   ESPN or ABC, Sunday afternoon CBS or FOX. A game that breaks its slot's
   rule, or kicks off in a slot no rule covers (a Wednesday opener, a London
   morning), is shown only if data/nfl/tv/exceptions.json lists that game WITH
   that network and a source; otherwise it is held back and reported. An
   exception names the network, so a flexed game that moves network is
   checked again rather than waved through.
   ONE network is shown: the first nfl.com lists, which is the rights
   holder (ESPN on Monday night, NBC on Sunday night). Measured 2026-09-27
   against ESPN's own scoreboard, weeks 1-4, that first network agreed on
   all 64 games, while the full list did not: nfl.com listed an ABC
   simulcast for week 4's Falcons at Saints that ABC's own Monday Night
   Football schedule does not carry. The rest of the list is kept in the
   record as `listed`, for provenance, and never shown.
4. Provenance. Every shown channel carries the URL it came from and the time
   it was read, and a change from the last read is recorded, never
   overwritten silently.

A missing or held-back channel is a warning, never an error: no pick waits
on a TV listing.

WHEN IT RUNS. With --pending it reads every locked week not yet fully graded
-- the weeks whose cards are on the board -- chosen by the same rule as the
weekend refresh. Two workflows run it that way: "NFL weekly update", after the
Tuesday grading and the Thursday lock, so a locked week has its channels
before Thursday night; and "NFL weekend refresh", so a flexed game is caught
before it airs. Both mark the step continue-on-error: a failure here can
never cost a pick or a refresh. Their schedules cannot meet (tested in
tests/test_weekend_refresh.py), so the two never write a week at once.

Run by hand: python -m src.sports.nfl.tv_channels --season 2026 --weeks 1 2 3 4
Run as the workflows do: python -m src.sports.nfl.tv_channels --pending
"""
import argparse
import json
import sys
from datetime import UTC, datetime

import pandas as pd

from src.sports.nfl.nfl_schedule_probe import (
    URL,
    elias_id,
    extract_games,
    fetch,
)
from src.sports.nfl.paths import DATA_DIR, PRED_DIR, RESULTS_DIR

TV_DIR = DATA_DIR / 'tv'
EXCEPTIONS = TV_DIR / 'exceptions.json'
# Through pandas, not zoneinfo: Windows Python ships no tz database, so
# ZoneInfo('America/New_York') raises on markys while passing on Linux CI.
EASTERN = 'America/New_York'

#: The closed list, as the plan names it. Keys are nfl.com's spellings in
#: upper case; values are how the page names them.
NETWORKS = {
    'CBS': 'CBS', 'FOX': 'FOX', 'NBC': 'NBC', 'ESPN': 'ESPN', 'ABC': 'ABC',
    'NFL NETWORK': 'NFL Network', 'PRIME VIDEO': 'Prime Video',
    'NETFLIX': 'Netflix', 'YOUTUBE': 'YouTube', 'PEACOCK': 'Peacock',
    'ESPN+': 'ESPN+',
}

#: Listed by nfl.com beside the main network, known, and not shown.
ALTERNATE_FEEDS = {'TELEMUNDO', 'UNIVERSO', 'ESPN DEPORTES', 'ESPN2', 'FOX DEPORTES'}

#: nfl.com's full team names to nflverse's abbreviations.
TEAMS = {
    'Arizona Cardinals': 'ARI', 'Atlanta Falcons': 'ATL', 'Baltimore Ravens': 'BAL',
    'Buffalo Bills': 'BUF', 'Carolina Panthers': 'CAR', 'Chicago Bears': 'CHI',
    'Cincinnati Bengals': 'CIN', 'Cleveland Browns': 'CLE', 'Dallas Cowboys': 'DAL',
    'Denver Broncos': 'DEN', 'Detroit Lions': 'DET', 'Green Bay Packers': 'GB',
    'Houston Texans': 'HOU', 'Indianapolis Colts': 'IND', 'Jacksonville Jaguars': 'JAX',
    'Kansas City Chiefs': 'KC', 'Las Vegas Raiders': 'LV', 'Los Angeles Chargers': 'LAC',
    'Los Angeles Rams': 'LA', 'Miami Dolphins': 'MIA', 'Minnesota Vikings': 'MIN',
    'New England Patriots': 'NE', 'New Orleans Saints': 'NO', 'New York Giants': 'NYG',
    'New York Jets': 'NYJ', 'Philadelphia Eagles': 'PHI', 'Pittsburgh Steelers': 'PIT',
    'San Francisco 49ers': 'SF', 'Seattle Seahawks': 'SEA', 'Tampa Bay Buccaneers': 'TB',
    'Tennessee Titans': 'TEN', 'Washington Commanders': 'WAS',
}

NIGHT_HOUR = 19  # 7 PM Eastern and later is a night game


def slot(kickoff_utc):
    """(name, allowed networks) for a kickoff, or (name, None) when no rule
    covers it. Times are judged in Eastern, where the rules are written."""
    t = pd.Timestamp(kickoff_utc).tz_convert(EASTERN)
    day, night = t.strftime('%A'), t.hour >= NIGHT_HOUR
    if day == 'Thursday' and night:
        return 'Thursday night', {'Prime Video'}
    if day == 'Sunday' and night:
        return 'Sunday night', {'NBC'}
    if day == 'Monday' and night:
        return 'Monday night', {'ESPN', 'ABC'}
    if day == 'Sunday' and 12 <= t.hour < NIGHT_HOUR:
        return 'Sunday afternoon', {'CBS', 'FOX'}
    return f"{day} {'night' if night else t.strftime('%H:%M')} Eastern", None


def networks_of(game):
    """(shown, unlisted) from nfl.com's home-market channel list."""
    shown, unlisted = [], []
    for name in (game.get('broadcastInfo') or {}).get('homeNetworkChannels') or []:
        key = str(name).strip().upper()
        if key in NETWORKS:
            if NETWORKS[key] not in shown:
                shown.append(NETWORKS[key])
        elif key not in ALTERNATE_FEEDS and key:
            unlisted.append(str(name))
    return shown, unlisted


def _kickoff(value):
    return datetime.fromisoformat(str(value).replace('Z', '+00:00')).astimezone(UTC)


def check_game(game, row, exceptions):
    """The channel record for one nfl.com game against its nflverse row.
    `row` is a dict with old_game_id, away_team, home_team and kickoff (UTC
    datetime), or None when no nflverse game has this elias id."""
    eid = elias_id(game)
    record = {'elias': eid, 'networks': [], 'held_back': [], 'reported': []}
    if row is None:
        record['held_back'].append('no nflverse game has this id')
        return record
    record.update(away=row['away_team'], home=row['home_team'])
    away = TEAMS.get((game.get('awayTeam') or {}).get('fullName'))
    home = TEAMS.get((game.get('homeTeam') or {}).get('fullName'))
    if (away, home) != (row['away_team'], row['home_team']):
        record['held_back'].append(f'teams disagree: nfl.com {away} at {home}')
    try:
        kickoff = _kickoff(game.get('time'))
    except (TypeError, ValueError):
        kickoff = None
    if kickoff is None or kickoff != row['kickoff']:
        record['held_back'].append(f'kickoff disagrees: nfl.com {game.get("time")}')
    shown, unlisted = networks_of(game)
    for name in unlisted:
        record['reported'].append(f'unlisted network {name} not shown')
    if not shown:
        record['held_back'].append('no listed network')
    elif kickoff is not None:
        primary = shown[0]
        name, allowed = slot(kickoff)
        excused = {e['network'] for e in exceptions if e.get('elias') == eid}
        if (allowed is None or primary not in allowed) and primary not in excused:
            record['held_back'].append(f'{name} slot rule broken by {primary} with no exception')
    record['territory'] = (game.get('broadcastInfo') or {}).get('territory')
    record['listed'] = shown
    if not record['held_back']:
        record['networks'] = shown[:1]
    return record


def nflverse_rows(schedule, week):
    """{old_game_id: row} for one week of nflverse's schedule, each row with
    its kickoff in UTC (Eastern gameday and gametime, localised)."""
    from src.sports.nfl.weekly_update import kickoff_utc
    rows = {}
    for _, r in schedule[schedule['week'] == week].iterrows():
        k = kickoff_utc(r)
        rows[str(r['old_game_id'])] = {
            'old_game_id': str(r['old_game_id']), 'away_team': r['away_team'],
            'home_team': r['home_team'],
            'kickoff': None if k is None else k.to_pydatetime().astimezone(UTC),
        }
    return rows


def build_week(games, rows, exceptions, url, read_at):
    """One record per nfl.com game, plus the nflverse games nfl.com lacked."""
    records, seen = [], set()
    for g in games:
        eid = elias_id(g)
        rec = check_game(g, rows.get(eid), exceptions)
        if rec['networks']:
            rec.update(source=url, read_at=read_at)
        records.append(rec)
        seen.add(eid)
    for eid, row in rows.items():
        if eid not in seen:
            records.append({'elias': eid, 'away': row['away_team'], 'home': row['home_team'],
                            'networks': [], 'held_back': ['not on the nfl.com page'],
                            'reported': []})
    return records


def merge(previous, records, read_at):
    """The new file content: current records, every read time kept, and a
    change entry wherever a game's shown networks differ from the last read.
    A change is recorded, never overwritten in silence (a flexed game)."""
    before = {r['elias']: r.get('networks', []) for r in (previous or {}).get('games', [])}
    changes = list((previous or {}).get('changes', []))
    for r in records:
        old = before.get(r['elias'])
        if old is not None and old != r['networks']:
            changes.append({'elias': r['elias'], 'away': r.get('away'), 'home': r.get('home'),
                            'from': old, 'to': r['networks'], 'read_at': read_at})
    reads = list((previous or {}).get('reads', [])) + [read_at]
    return {'reads': reads, 'changes': changes, 'games': records}


def load_exceptions(path=EXCEPTIONS):
    with open(path, encoding='utf-8') as f:
        entries = json.load(f)['exceptions']
    for e in entries:
        missing = [k for k in ('elias', 'network', 'reason', 'source') if not e.get(k)]
        if missing or not str(e['source']).startswith('https://'):
            raise ValueError(f'exception {e.get("elias")} lacks {missing or ["an https source"]}; '
                             f'an exception without a source is a claim nobody can check')
        if e['network'] not in NETWORKS.values():
            raise ValueError(f'exception {e["elias"]} names {e["network"]}, which is not on the list')
    return entries


def main(argv=None, now=None, load=None, fetch_page=fetch, tv_dir=TV_DIR,
         pred_dir=PRED_DIR, results_dir=RESULTS_DIR):
    ap = argparse.ArgumentParser()
    ap.add_argument('--season', type=int, default=None)
    which = ap.add_mutually_exclusive_group(required=True)
    which.add_argument('--weeks', type=int, nargs='+')
    which.add_argument('--pending', action='store_true',
                       help='every locked week not yet fully graded')
    args = ap.parse_args(argv)
    now = now or datetime.now(UTC)
    read_at = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    from src.sports.nfl.weekend_refresh import current_season, weeks_to_refresh
    args.season = args.season or current_season(now)
    if args.pending:
        args.weeks = weeks_to_refresh(args.season, pred_dir, results_dir)
        if not args.weeks:
            print(f'{args.season}: no locked week is waiting on grading; no channels to read.')
            return 0
    exceptions = load_exceptions(tv_dir / 'exceptions.json')
    if load is None:
        from src.sports.nfl.data_loader import load_schedule as load
    schedule = load(args.season)
    for week in args.weeks:
        url = URL.format(season=args.season, week=week)
        try:
            page = fetch_page(week, args.season)
        except Exception as exc:  # a warning, never an error: no pick waits on TV
            print(f'WARNING week {week}: nfl.com unreachable ({type(exc).__name__}: {exc}); '
                  f'channels left as they were')
            continue
        games = [g for g in extract_games(page)
                 if (g.get('season'), g.get('week'), g.get('seasonType')) == (args.season, week, 'REG')]
        records = build_week(games, nflverse_rows(schedule, week), exceptions, url, read_at)
        path = tv_dir / f'{args.season}_week{week}.json'
        previous = json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
        merged = merge(previous, records, read_at)
        path.write_text(json.dumps(merged, indent=2) + '\n', encoding='utf-8')
        shown = sum(bool(r['networks']) for r in records)
        print(f'week {week}: {shown} of {len(records)} games have a channel shown')
        for r in records:
            for why in r['held_back']:
                print(f"  WARNING {r.get('away')} at {r.get('home')} ({r['elias']}): held back -- {why}")
            for note in r['reported']:
                print(f"  NOTE {r.get('away')} at {r.get('home')} ({r['elias']}): {note}")
        for c in merged['changes'][len((previous or {}).get('changes', [])):]:
            print(f"  CHANGED {c['away']} at {c['home']}: {c['from']} -> {c['to']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
