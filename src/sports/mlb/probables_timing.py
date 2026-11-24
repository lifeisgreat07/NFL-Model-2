"""When MLB names its probable pitchers, measured in spring training to set the daily runs' times (Stage 101 item 2).

MLB's forward test saves each game's pick at the last of three daily runs at least an hour before first pitch, and
reads the starters the Stats API lists as probable at that run (`experiments/mlb/stage101/registry.json`,
`forward_test.runs`). The three times are not fixed in the registry: they come from this measurement, by a rule the
registry fixed before it was taken.

`record` is the measurement. `.github/workflows/mlb-spring-probables.yml` runs it every 30 minutes in February and
March. Each run reads the Stats API's spring training schedule (`gameType=S`) for today and the next two days
(Eastern) with the probable pitchers, and keeps, for each game, in `data/mlb/spring_probables_2027.json`:

- its official date and its listed first pitch, updated until the game starts (`start_utc`, `start_time_tbd`);
- the Stats API's state at the last read (`state`, its `codedGameState`);
- `first_named_utc`: the time of the first read that names both probable pitchers, with the two named
  (`home_probable`, `away_probable`); and
- `closed`: true once a read finds the game started. A game closed with no `first_named_utc` was never named.

A read can only find a naming at or after the moment it happened, and GitHub's scheduler starts runs late or skips
them, so `first_named_utc` is when the measurement saw both probables, never earlier than when MLB named them. The
times of the reads themselves are the workflow's run history; the file changes, and is committed, only when a game is
added, moves, changes state, is named or starts, so the record grows with the season rather than with every read.
Nothing is read for a game after 2027-03-21, the last day the registry measures; a run after it, or in another year,
reads nothing.

`choose` applies the registered rule once the measurement is over, and writes
`experiments/mlb/stage101/probables_timing.json`:

- the measured games are those that started (closed, or with a first pitch before the file was last read), whose
  start was set (not `start_time_tbd`) and that were not postponed or cancelled at the last read;
- a candidate is one of the 48 half-hour marks of the UTC day, and a run at a mark happens every day. For a set of
  three, a game's saving run is the latest run at any of the three marks at least one hour before its listed first
  pitch, and the game counts when both probables were named at or before it;
- the set with the highest share of counted games is the best; among sets within one percentage point of it, the
  one whose three times are latest on average is chosen. "Latest" is read on MLB's day, which starts at 10:00 UTC
  (5 or 6 AM Eastern, after every night game has ended and before any day game starts), so 23:30 UTC is earlier
  than 00:30 UTC. A tie after that goes to the earliest-listed set, so the answer never depends on the order the
  sets were scored in;
- below 90%, the times are still the rule's, and the file says so (`below_90`): the registry then asks for an
  amendment before the first pick.

Run by hand:
    python -m src.sports.mlb.probables_timing record
    python -m src.sports.mlb.probables_timing choose
"""
from __future__ import annotations

import argparse
import itertools
import json
import time
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd

from src.core.sport import sport_paths
from src.sports.mlb.schedule import STATS, games_of

PATHS = sport_paths('mlb')
SEASON = 2027
#: The registry's last measured day.
LAST_DAY = date(2027, 3, 21)
RECORD = PATHS.data / f'spring_probables_{SEASON}.json'
CHOSEN = PATHS.root / 'experiments' / 'mlb' / 'stage101' / 'probables_timing.json'
SPRING = (STATS + '/schedule?sportId=1&gameType=S&startDate={first}&endDate={last}'
          '&hydrate=probablePitcher')
ET = 'America/New_York'
#: Today and the next two days (Eastern): a saving run is never more than a day before its game, so a game is read
#: well before any run could save it.
DAYS_AHEAD = 2
#: The lock's slack: a game is saved by the last run at least this long before its first pitch.
SLACK = timedelta(hours=1)
#: The candidates: every half hour of the UTC day, as minutes after midnight.
MARKS = tuple(range(0, 24 * 60, 30))
RUNS = 3
#: Sets this close to the best share are tied, and the latest of them is chosen.
WITHIN = 0.01
FLOOR = 0.90
#: MLB's day starts here (UTC), for reading which times are "latest".
DAY_START = 10 * 60
#: Postponed and cancelled, in the Stats API's codedGameState.
NOT_PLAYED = frozenset({'D', 'C'})

Json = Any


def stamp(t: datetime) -> str:
    return t.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def parse(s: str) -> datetime:
    return datetime.fromisoformat(s.replace('Z', '+00:00'))


def fetch_json(url: str, timeout: int = 30, tries: int = 3) -> Json:
    req = urllib.request.Request(url, headers={'User-Agent': 'NFL-Model-2 MLB spring probables'})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except OSError:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)
    raise AssertionError('unreachable')


def window(now: datetime) -> tuple[date, date] | None:
    """The official dates one read covers, or None when the measurement is over or not this season's."""
    today = pd.Timestamp(now).tz_convert(ET).date()
    if today.year != SEASON or today > LAST_DAY:
        return None
    return today, min(today + timedelta(days=DAYS_AHEAD), LAST_DAY)


def _side(g: Json, side: str) -> Json:
    return ((g.get('teams') or {}).get(side) or {})


def _probable(g: Json, side: str) -> Any:
    return (_side(g, side).get('probablePitcher') or {}).get('id')


def record(store: dict[str, Any], data: Json, read_at: datetime) -> bool:
    """Add one read of the spring schedule to `store`; True when anything in it changed."""
    games: dict[str, Any] = store.setdefault('games', {})
    before = json.dumps(games, sort_keys=True)
    for g in games_of(data):
        if g.get('gameType') != 'S' or not g.get('gamePk') or not g.get('gameDate'):
            continue
        gid = str(g['gamePk'])
        row = games.setdefault(gid, {'official_date': g.get('officialDate'), 'start_utc': g['gameDate'],
                                     'start_time_tbd': False, 'state': None, 'first_named_utc': None,
                                     'home_probable': None, 'away_probable': None, 'closed': False})
        if row['closed']:
            continue
        status = g.get('status') or {}
        row['state'] = status.get('codedGameState')
        row['official_date'] = g.get('officialDate')
        row['start_utc'] = g['gameDate']
        row['start_time_tbd'] = status.get('startTimeTBD') is True
        if read_at >= parse(row['start_utc']):
            row['closed'] = True
            continue
        home, away = _probable(g, 'home'), _probable(g, 'away')
        if row['first_named_utc'] is None and home is not None and away is not None:
            row.update(first_named_utc=stamp(read_at), home_probable=home, away_probable=away)
    changed = json.dumps(games, sort_keys=True) != before
    if changed:
        store['season'] = SEASON
        store['last_change_utc'] = stamp(read_at)
    return changed


def load(path: Path = RECORD) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'season': SEASON, 'games': {}}


def save(store: Mapping[str, Any], path: Path = RECORD) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=1, sort_keys=True) + '\n', encoding='utf-8')


def measured(store: Mapping[str, Any], now: datetime) -> list[tuple[datetime, datetime | None]]:
    """(listed first pitch, first read naming both probables or None) for each game the rule counts."""
    out = []
    for row in (store.get('games') or {}).values():
        start = parse(row['start_utc'])
        if not (row['closed'] or start <= now) or row['start_time_tbd'] or row['state'] in NOT_PLAYED:
            continue
        named = parse(row['first_named_utc']) if row['first_named_utc'] else None
        out.append((start, named))
    return sorted(out, key=lambda r: r[0])


def saving_run(start: datetime, mark: int) -> datetime:
    """The latest run at `mark` (minutes after midnight UTC) at least `SLACK` before `start`."""
    latest = start.astimezone(UTC) - SLACK
    run = latest.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(minutes=mark)
    return run if run <= latest else run - timedelta(days=1)


def named_at(games: Iterable[tuple[datetime, datetime | None]]) -> npt.NDArray[np.bool_]:
    """games x marks: whether both probables were named by the run at each mark that would save the game."""
    return np.array([[named is not None and named <= saving_run(start, m) for m in MARKS]
                     for start, named in games], dtype=bool).reshape(-1, len(MARKS))


def shares(n: npt.NDArray[np.bool_]) -> list[float]:
    """The share of games named at the saving run for every set of three marks, in
    `itertools.combinations(range(len(MARKS)), 3)` order: a game counts when any of the three marks named it."""
    m = n.shape[1]
    out: list[float] = []
    for i in range(m):
        for j in range(i + 1, m):
            pair = n[:, i] | n[:, j]
            out.extend((pair[:, None] | n[:, j + 1:]).mean(axis=0).tolist())
    return out


def lateness(marks: Iterable[int]) -> float:
    """The mean of the times, in minutes after MLB's day starts (`DAY_START`)."""
    return float(np.mean([(m - DAY_START) % (24 * 60) for m in marks]))


def hhmm(mark: int) -> str:
    return f'{mark // 60:02d}:{mark % 60:02d}'


def choose(store: Mapping[str, Any], now: datetime) -> dict[str, Any]:
    """The registered rule: the run times and what the measurement says of them."""
    games = measured(store, now)
    if not games:
        raise ValueError('no measured spring game: nothing to choose from')
    n = named_at(games)
    scored = list(zip(shares(n), itertools.combinations(range(len(MARKS)), RUNS), strict=True))
    best = max(share for share, _ in scored)
    near = [(share, s) for share, s in scored if share >= best - WITHIN - 1e-12]
    share, chosen = min(near, key=lambda r: (-lateness(MARKS[i] for i in r[1]), r[1]))
    marks = sorted((MARKS[i] for i in chosen), key=lambda m: (m - DAY_START) % (24 * 60))
    return {
        'times_utc': [hhmm(m) for m in marks],
        'share': round(share, 4),
        'best_share': round(best, 4),
        'below_90': share < FLOOR,
        'games': len(games),
        'never_named': sum(1 for _, named in games if named is None),
        'first_game_utc': stamp(games[0][0]),
        'last_game_utc': stamp(games[-1][0]),
        'record': RECORD.relative_to(PATHS.root).as_posix(),
        'rule': 'experiments/mlb/stage101/registry.json, forward_test.runs.rule',
    }


def run_record(now: datetime, get: Callable[[str], Json] = fetch_json, path: Path = RECORD) -> str:
    span = window(now)
    if span is None:
        return f'outside the measurement (to {LAST_DAY}): nothing read'
    store = load(path)
    changed = record(store, get(SPRING.format(first=span[0], last=span[1])), now)
    if changed:
        save(store, path)
    games = store.get('games') or {}
    named = sum(1 for r in games.values() if r['first_named_utc'])
    return (f'read {span[0]} to {span[1]}: {len(games)} spring games kept, {named} with both probables named'
            + ('' if changed else '; nothing changed'))


def main(argv: Iterable[str] | None = None, now: datetime | None = None,
         get: Callable[[str], Json] = fetch_json) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    ap.add_argument('action', choices=('record', 'choose'))
    args = ap.parse_args(list(argv) if argv is not None else None)
    now = now or datetime.now(UTC)
    if args.action == 'record':
        print(run_record(now, get))
        return 0
    result = choose(load(), now)
    CHOSEN.write_text(json.dumps(result, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
