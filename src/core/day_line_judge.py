"""Line Judge's checks for the day sports' daily runs (Stage 44 item 2).

The NFL's Weekly update has its own (src/sports/nfl/line_judge.py). The NHL
and the NBA save a pick game by game, twice a day, so a right daily run
leaves a different state on main, and it is the same for both:

  on-time         -- a run that served a slot started under the sport's
                     warning hour after it (start_delay.WARN_HOURS_FOR: one
                     hour, the lock rule's slack). A run GitHub's cron
                     started for a slot a dispatched run already served is
                     its late copy and is not judged (missed_dispatch).
  before-start    -- every pick file was first committed before its game
                     started. git's commit time, not the `saved_utc` the run
                     writes for itself: a pick pushed after the start was
                     visible only once the game was under way.
  graded-right    -- every pick whose game is final has a graded row, and
                     the row's result is worked out again here from the
                     score: the winner's pick reads `correct`, the other
                     `wrong`. A wrong grade is caught, not only a missing one.
  schedule-fresh  -- the schedule file the board reads says it was written
                     today (Eastern), as every run rewrites it.

A game that started with no pick is not judged here: the daily run raises
that alert itself ("a game started with no saved pick").

The checks read what is committed: results/<sport>/schedule_<season>.json
and graded_<season>.json, predictions/<sport>/<season>/<game>.json, and
git's history for when each pick file was added (a checkout with the whole
history is needed; a shallow one shows every file added at once).

    python -m src.core.day_line_judge --sport nhl [--season 2026] \
        [--run-event schedule --run-started 2026-10-15T14:00:41Z] [--report line-judge.md]

Exit 0 when every check holds, 1 when any finding is written.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from src.core import missed_dispatch
from src.core.start_delay import (
    WARN_HOURS,
    WARN_HOURS_FOR,
    crons,
    latest_slot,
    served_delay,
)

ROOT = Path(__file__).resolve().parents[2]
SPORTS = ('nhl', 'nba')
# Through pandas, not zoneinfo: Windows Python ships no tz database, so
# ZoneInfo('America/New_York') raises at import on markys (as in
# src/sports/nfl/tv_channels.py) while passing on Linux CI.
ET = 'America/New_York'
Json = Any


@dataclass(frozen=True)
class Finding:
    check: str
    message: str


def _utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace('Z', '+00:00')).astimezone(UTC)


def workflow_name(sport: str) -> str:
    return f'{sport}-daily.yml'


def is_late_copy(sport: str, started: datetime, workflow_text: str,
                 fetch: missed_dispatch.Fetch) -> bool:
    """True when a dispatched run of this workflow already served the slot
    `started` is measured against, so this run is GitHub's own cron copy of
    it (src/core/missed_dispatch.py). That copy commits nothing, and judging
    it late would raise a finding for every slot cron-job.org served on
    time. When the Actions API cannot be read the answer is False: a late
    run is flagged rather than guessed away."""
    slot = latest_slot(crons(workflow_text), started)
    if slot is None:
        return False
    try:
        dispatches = fetch(workflow_name(sport), slot[0])
    except Exception:  # unreadable: judge the run
        return False
    return missed_dispatch.judge(slot[0], started, dispatches) == 'covered'


def check_on_time(sport: str, event: str | None, started: datetime | None, workflow_text: str,
                  fetch: missed_dispatch.Fetch | None = None) -> list[Finding]:
    """`fetch` reads when this workflow's dispatched runs started; given, a
    run GitHub's cron started for a slot a dispatched run served is not late."""
    if started is None:
        return []
    warn = WARN_HOURS_FOR.get(workflow_name(sport), WARN_HOURS)
    delay = served_delay(crons(workflow_text), started, event)
    if delay is None or delay < timedelta(hours=warn):
        return []
    if event == 'schedule' and fetch is not None and is_late_copy(sport, started, workflow_text, fetch):
        return []
    hours = delay.total_seconds() / 3600
    return [Finding('on-time', f'the run started {hours:.1f} hours after its slot (started by {event or "hand"}); '
                               f'{warn} or more can miss a game the run before left to it.')]


def check_before_start(picks: dict[str, Json], starts: dict[str, str], added: dict[str, datetime]) -> list[Finding]:
    """`picks` by game id; `starts`, the schedule's start for each game;
    `added`, when git first saw each game's pick file."""
    out = []
    for gid, pick in sorted(picks.items()):
        start = starts.get(gid) or pick.get('start_utc')
        when = added.get(gid)
        if not start or when is None:
            continue
        if when >= _utc(start):
            out.append(Finding('before-start', f'game {gid} ({pick.get("away")} at {pick.get("home")}) started '
                                               f'{_utc(start):%Y-%m-%d %H:%M} UTC; its pick was first committed '
                                               f'{when:%Y-%m-%d %H:%M} UTC.'))
    return out


def winner(game: Json) -> str | None:
    """The final game's winner from its score, or None if it has no usable one."""
    hs, as_ = game.get('home_score'), game.get('away_score')
    if game.get('status') != 'final' or hs is None or as_ is None or hs == as_:
        return None
    return str(game['home'] if hs > as_ else game['away'])


def check_graded(picks: dict[str, Json], games: dict[str, Json], graded: list[Json]) -> list[Finding]:
    rows = {str(r.get('game_id')): r for r in graded}
    out = []
    for gid, pick in sorted(picks.items()):
        g = games.get(gid)
        if g is None or g.get('status') != 'final':
            continue
        w = winner(g)
        if w is None:
            out.append(Finding('graded-right', f'game {gid} is final with no usable score '
                                               f'({g.get("away_score")}-{g.get("home_score")}).'))
            continue
        want = 'correct' if pick.get('pick') == w else 'wrong'
        row = rows.get(gid)
        if row is None:
            out.append(Finding('graded-right', f'game {gid} is final and has no graded row.'))
        elif row.get('result') != want:
            out.append(Finding('graded-right', f'game {gid}: {w} won and the pick was {pick.get("pick")}, '
                                               f'so it is {want}; the graded row says {row.get("result")}.'))
    return out


def check_fresh(as_of: str | None, now: datetime) -> list[Finding]:
    today = pd.Timestamp(now).tz_convert(ET).strftime('%Y-%m-%d')
    if as_of == today:
        return []
    return [Finding('schedule-fresh', f'the schedule file says it was written {as_of or "never"}; '
                                      f'every run rewrites it, and today is {today} (Eastern).')]


def latest_season(sport: str, root: Path = ROOT) -> int | None:
    folder = root / 'results' / sport
    seasons = sorted(int(m.group(1)) for p in folder.glob('schedule_*.json')
                     if (m := re.fullmatch(r'schedule_(\d{4})', p.stem)))
    return seasons[-1] if seasons else None


def _git(args: list[str], cwd: Path) -> str:
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, check=True,
                          encoding='utf-8').stdout


def added_at(folder: Path, root: Path = ROOT, git: Callable[[list[str], Path], str] = _git) -> dict[str, datetime]:
    """When each pick file in `folder` was first committed, by game id (the
    file's stem). A pick file is written once and never rewritten, but should
    one be removed and added again, the first add is the one that counts."""
    rel = folder.resolve().relative_to(root.resolve()).as_posix()
    out = git(['log', '--diff-filter=A', '--name-only', '--format=%x00%cI', '--', rel], root)
    first: dict[str, datetime] = {}
    for block in out.split('\x00'):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        when = datetime.fromisoformat(lines[0]).astimezone(UTC)
        for path in lines[1:]:
            if path.endswith('.json'):
                first[Path(path).stem] = when  # newest first, so the last write is the oldest add
    return first


def judge(sport: str, season: int, now: datetime, added: dict[str, datetime], root: Path = ROOT,
          event: str | None = None, started: datetime | None = None, workflow_text: str = '',
          fetch: missed_dispatch.Fetch | None = None) -> list[Finding]:
    """Every finding, in check order."""
    results = root / 'results' / sport
    sched_doc = json.loads((results / f'schedule_{season}.json').read_text(encoding='utf-8'))
    games = {str(g['game_id']): g for g in sched_doc.get('games', [])}
    graded_file = results / f'graded_{season}.json'
    graded = json.loads(graded_file.read_text(encoding='utf-8')) if graded_file.exists() else []
    picks = {}
    for path in sorted((root / 'predictions' / sport / str(season)).glob('*.json')):
        pick = json.loads(path.read_text(encoding='utf-8'))
        picks[str(pick.get('game_id', path.stem))] = pick
    findings = check_on_time(sport, event, started, workflow_text, fetch)
    findings += check_before_start(picks, {gid: g.get('start_utc') for gid, g in games.items()}, added)
    findings += check_graded(picks, games, graded)
    findings += check_fresh(sched_doc.get('as_of'), now)
    return findings


def report(findings: list[Finding], sport: str, season: int) -> str:
    name = sport.upper()
    if not findings:
        return f'Line Judge: every check holds for the {name} {season} daily run.'
    lines = [f'Line Judge found {len(findings)} thing(s) the {name} {season} daily run left wrong:', '']
    lines += [f'- **{f.check}**: {f.message}' for f in findings]
    return '\n'.join(lines)


def main(argv: list[str] | None = None, now: datetime | None = None, root: Path = ROOT,
         fetch: missed_dispatch.Fetch | None = missed_dispatch._gh_fetch) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--sport', choices=SPORTS, required=True)
    ap.add_argument('--season', type=int, help='default: the newest results/<sport>/schedule_<season>.json')
    ap.add_argument('--run-event')
    ap.add_argument('--run-started', help="the judged run's start, ISO 8601")
    ap.add_argument('--report', help='also write the report to this file')
    args = ap.parse_args(argv)
    season = args.season or latest_season(args.sport, root)
    if season is None:
        print(f'Line Judge: no {args.sport.upper()} schedule file yet; nothing to judge.')
        return 0
    started = _utc(args.run_started) if args.run_started else None
    wf = root / '.github' / 'workflows' / workflow_name(args.sport)
    findings = judge(args.sport, season, now or datetime.now(UTC),
                     added_at(root / 'predictions' / args.sport / str(season), root), root,
                     args.run_event, started, wf.read_text(encoding='utf-8'), fetch)
    text = report(findings, args.sport, season)
    print(text)
    if args.report:
        Path(args.report).write_text(text + '\n', encoding='utf-8')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
