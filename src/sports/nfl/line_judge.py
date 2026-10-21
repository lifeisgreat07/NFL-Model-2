"""Line Judge's checks for the NFL Weekly update (Stage 44 item 1) and the
Weekend refresh (item 2).

A run can go green and still do the wrong thing. Line Judge asks, after a
Weekly update run, whether the state it left behind on main is what a
right run leaves. Each check is plain code over what is committed, so
each is tested and mutation-tested like any other guard; the agent that
explains a failure comes later and only when one fails (Stage 44's shape,
Mark's call 2026-10-13: checks first, agent on failure).

  on-time        -- a run that served a slot started under
                    start_delay.WARN_HOURS after it (one under LOCK_SLACK,
                    past which a Thursday run may miss the first kickoff).
                    A run GitHub's cron started for a slot a dispatched run
                    already served is its late copy and is not judged
                    (missed_dispatch).
  every-week     -- every week of the season whose first game has kicked
                    off is locked (predictions/nfl/) or recorded as skipped
                    (predictions/nfl/skipped/). A week silently passed over
                    is the failure determine_next_week once had (Stage 24).
  before-kickoff -- in each locked week, the commit that locked the file
                    (`locked_at`) came before every picked game's kickoff, and every
                    game with no pick had already kicked off by then (the
                    run names those; it may not drop an upcoming one).
  graded         -- every locked week whose picked games are all final has
                    a graded file with a row for every pick, leaving out
                    the cancelled games (data/nfl/cancelled_games.json).

The checks read the schedule as nflverse gives it now, and git's history
for when each week was locked (`locked_at`, which follows renames, so the
2026-10-08 move into predictions/nfl/ is crossed). A checkout with the
whole history is needed: a shallow one shows every file added at once.

    python -m src.sports.nfl.line_judge --season 2026 [--run-event schedule \
        --run-started 2026-10-15T11:00:41Z] [--report line-judge.md]

The Weekend refresh writes no pick and no grade (src/sports/nfl/weekend_refresh.py):
its job is the page's snapshot of each locked, not yet graded week. After
each of its runs (`--workflow nfl-weekend-refresh.yml`) two checks apply:

  on-time        -- as above, against the refresh's own slots.
  snapshot       -- every week the refresh keeps (`weeks_to_refresh`) has its
                    data/nfl/game_status/ file, and every picked game the
                    schedule has a final score for reads final there with
                    that score (a listed cancelled game reads cancelled). A
                    score left as "started" is what the page shows wrong.

Exit 0 when every check holds, 1 when any finding is written.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from src.core import missed_dispatch
from src.core.start_delay import WARN_HOURS, crons, latest_slot, served_delay
from src.sports.nfl.paths import (
    PRED_DIR,
    RESULTS_DIR,
    ROOT,
    SKIPPED_DIR,
    STATUS_DIR,
    parse_week,
)

WORKFLOW = ROOT / '.github' / 'workflows' / 'nfl-weekly-update.yml'
#: The runs judged, by workflow file, as the report names them.
RUNS = {'nfl-weekly-update.yml': 'Weekly update', 'nfl-weekend-refresh.yml': 'Weekend refresh'}
#: The postseason's last week; nothing is expected beyond it.
LAST_WEEK = 22


@dataclass(frozen=True)
class Finding:
    check: str
    message: str


def kickoff(game: Any) -> pd.Timestamp | None:
    """The game's kickoff in UTC, as the Weekly update reads it."""
    from src.sports.nfl.weekly_update import kickoff_utc
    return kickoff_utc(game)


def _weeks(folder: Path, season: int) -> dict[int, Path]:
    out = {}
    for f in folder.glob(f'{season}_week*.json'):
        key = parse_week(f.stem)
        if key is not None and key[0] == season:
            out[key[1]] = f
    return out


def _pair(home: str, away: str) -> tuple[str, str]:
    return str(home), str(away)


def is_late_copy(workflow: str, started: datetime, workflow_text: str, fetch: missed_dispatch.Fetch) -> bool:
    """True when a dispatched run of this workflow already served the slot
    `started` is measured against, so this run is GitHub's own cron copy of
    it (src/core/missed_dispatch.py). That copy commits nothing, and judging
    it late would raise a finding for every slot cron-job.org served on
    time (the daily runs' fix, src/core/day_line_judge.py). When the Actions
    API cannot be read the answer is False: a late run is flagged rather
    than guessed away."""
    slot = latest_slot(crons(workflow_text), started)
    if slot is None:
        return False
    try:
        dispatches = fetch(workflow, slot[0])
    except Exception:  # unreadable: judge the run
        return False
    return missed_dispatch.judge(slot[0], started, dispatches) == 'covered'


def check_on_time(event: str | None, started: datetime | None, workflow_text: str,
                  fetch: missed_dispatch.Fetch | None = None, workflow: str = WORKFLOW.name) -> list[Finding]:
    """`fetch` reads when `workflow`'s dispatched runs started; given, a run
    GitHub's cron started for a slot a dispatched run served is not late."""
    if started is None:
        return []
    delay = served_delay(crons(workflow_text), started, event)
    if delay is None or delay < timedelta(hours=WARN_HOURS):
        return []
    if event == 'schedule' and fetch is not None and is_late_copy(workflow, started, workflow_text, fetch):
        return []
    hours = delay.total_seconds() / 3600
    return [Finding('on-time', f'the run started {hours:.1f} hours after its slot '
                               f'(started by {event or "hand"}); {WARN_HOURS} or more risks a lock '
                               f'landing after the first kickoff.')]


def check_every_week(schedule: pd.DataFrame, locked: Iterable[int], skipped: Iterable[int],
                     now: datetime) -> list[Finding]:
    done = set(locked) | set(skipped)
    out = []
    for week, games in schedule.groupby('week'):
        week = int(week)
        if week > LAST_WEEK or week in done:
            continue
        kicks = [k for _, g in games.iterrows() if (k := kickoff(g)) is not None]
        if kicks and min(kicks) <= pd.Timestamp(now):
            out.append(Finding('every-week', f'week {week} kicked off {min(kicks):%a %Y-%m-%d %H:%M} UTC '
                                             f'and is neither locked nor recorded as skipped.'))
    return out


def check_before_kickoff(week: int, saved: datetime, picks: list[dict], games: pd.DataFrame,
                         cancelled: set[tuple[str, str]]) -> list[Finding]:
    saved_at = pd.Timestamp(saved)
    picked = {_pair(p['home'], p['away']) for p in picks}
    out = []
    for _, g in games.iterrows():
        pair = _pair(g['home_team'], g['away_team'])
        k = kickoff(g)
        if k is None:
            continue
        if pair in picked and k <= saved_at:
            out.append(Finding('before-kickoff', f'week {week}: {pair[1]} at {pair[0]} kicked off '
                                                 f'{k:%Y-%m-%d %H:%M} UTC, before its pick was first saved '
                                                 f'({saved_at:%Y-%m-%d %H:%M} UTC).'))
        if pair not in picked and pair not in cancelled and k > saved_at:
            out.append(Finding('before-kickoff', f'week {week}: {pair[1]} at {pair[0]} had not kicked off '
                                                 f'when the week was saved, and has no pick.'))
    return out


def check_graded(week: int, picks: list[dict], games: pd.DataFrame, graded: list[dict] | None,
                 cancelled: set[tuple[str, str]]) -> list[Finding]:
    by_pair = {_pair(g['home_team'], g['away_team']): g for _, g in games.iterrows()}
    due = []
    for p in picks:
        pair = _pair(p['home'], p['away'])
        if pair in cancelled:
            continue
        g = by_pair.get(pair)
        if g is None or pd.isna(g.get('home_score')) or pd.isna(g.get('away_score')):
            return []  # not every picked game is final yet: nothing is due
        due.append(pair)
    if not due:
        return []
    if graded is None:
        return [Finding('graded', f'week {week}: every picked game is final and there is no graded file.')]
    have = {_pair(r['home'], r['away']) for r in graded}
    missing = [f'{a} at {h}' for h, a in due if (h, a) not in have]
    if missing:
        return [Finding('graded', f'week {week}: final but not graded: {", ".join(missing)}.')]
    return []


def check_snapshot(week: int, picks: list[dict], games: pd.DataFrame, snapshot: dict | None,
                   cancelled: set[tuple[str, str]]) -> list[Finding]:
    """The page's snapshot of one kept week against the schedule."""
    if snapshot is None:
        return [Finding('snapshot', f'week {week} is locked and not fully graded, and has no game_status file.')]
    shown = {_pair(g['home'], g['away']): g for g in snapshot.get('games', [])}
    by_pair = {_pair(g['home_team'], g['away_team']): g for _, g in games.iterrows()}
    out = []
    for p in picks:
        pair = _pair(p['home'], p['away'])
        g, s = by_pair.get(pair), shown.get(pair)
        if g is None:
            continue  # the schedule no longer lists it: the refresh leaves it out and says so
        name = f'{pair[1]} at {pair[0]}'
        if s is None:
            out.append(Finding('snapshot', f'week {week}: {name} is picked and missing from the snapshot.'))
            continue
        final = not (pd.isna(g.get('home_score')) or pd.isna(g.get('away_score')))
        if final:
            want = (int(g['home_score']), int(g['away_score']))
            if s.get('status') != 'final' or (s.get('home_score'), s.get('away_score')) != want:
                out.append(Finding('snapshot', f'week {week}: {name} ended {want[1]}-{want[0]}; the snapshot reads '
                                               f'{s.get("status")} {s.get("away_score")}-{s.get("home_score")}.'))
        elif pair in cancelled and s.get('status') != 'cancelled':
            out.append(Finding('snapshot', f'week {week}: {name} is listed as cancelled; the snapshot reads '
                                           f'{s.get("status")}.'))
    return out


def judge_refresh(season: int, schedule: pd.DataFrame, cancelled: set[tuple[str, str]], weeks: Iterable[int],
                  event: str | None = None, started: datetime | None = None, workflow_text: str = '',
                  pred_dir: Path = PRED_DIR, status_dir: Path = STATUS_DIR,
                  fetch: missed_dispatch.Fetch | None = None) -> list[Finding]:
    """Every finding for a Weekend refresh run, in check order. `weeks`: the
    weeks the refresh keeps (weekend_refresh.weeks_to_refresh)."""
    findings = check_on_time(event, started, workflow_text, fetch, 'nfl-weekend-refresh.yml')
    for week in sorted(weeks):
        picks = json.loads((pred_dir / f'{season}_week{week}.json').read_text(encoding='utf-8'))
        snap_file = status_dir / f'{season}_week{week}.json'
        snap = json.loads(snap_file.read_text(encoding='utf-8')) if snap_file.exists() else None
        findings += check_snapshot(week, picks, schedule[schedule['week'] == week], snap, cancelled)
    return findings


def load_cancelled_pairs(season: int) -> set[tuple[str, str]]:
    from src.sports.nfl.weekend_refresh import load_cancelled
    return {(h, a) for s, _, a, h in load_cancelled() if s == season}


def judge(season: int, schedule: pd.DataFrame, now: datetime, saved_at: Callable[[Path], datetime | None],
          cancelled: set[tuple[str, str]], event: str | None = None, started: datetime | None = None,
          workflow_text: str = '', pred_dir: Path = PRED_DIR, skipped_dir: Path = SKIPPED_DIR,
          results_dir: Path = RESULTS_DIR, fetch: missed_dispatch.Fetch | None = None) -> list[Finding]:
    """Every finding, in check order."""
    locked = _weeks(pred_dir, season)
    findings = check_on_time(event, started, workflow_text, fetch)
    findings += check_every_week(schedule, locked, _weeks(skipped_dir, season), now)
    for week, path in sorted(locked.items()):
        picks = json.loads(path.read_text(encoding='utf-8'))
        games = schedule[schedule['week'] == week]
        first = saved_at(path)
        if first is not None:
            findings += check_before_kickoff(week, first, picks, games, cancelled)
        graded_file = results_dir / f'{season}_week{week}_graded.json'
        graded = json.loads(graded_file.read_text(encoding='utf-8')) if graded_file.exists() else None
        findings += check_graded(week, picks, games, graded, cancelled)
    return findings


def _git(args: list[str], cwd: Path) -> str:
    import subprocess
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, check=True,
                          encoding='utf-8').stdout


def locked_at(path: Path, root: Path = ROOT, git: Callable[[list[str], Path], str] = _git) -> datetime | None:
    """When the week was locked: the first commit that put this file anywhere
    but predictions/.../preview/, following renames, or None if git has no
    such commit.

    Not simply the file's first commit. Since Stage 30 the lock run moves
    Tuesday's preview into place, so git's rename-following reaches back to
    the preview's creation (2026 week 5: added as a preview 10-06 17:00,
    locked 10-08 17:43, moved into predictions/nfl/ 10-08 by #351). Judged
    from the first commit, a lock saved after kickoff would pass whenever a
    preview existed."""
    rel = path.resolve().relative_to(root.resolve()).as_posix()
    out = git(['log', '--follow', '--name-status', '--format=%x00%cI', '--', rel], root)
    found = None
    for block in out.split('\x00'):
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        when, changes = lines[0], lines[1:]
        # The path this commit left the file at: the last field of its
        # name-status line (A/M <path>, or R<n> <old> <new>).
        dest = [c.split('\t')[-1] for c in changes]
        if dest and not any('/preview/' in d for d in dest):
            found = when  # log runs newest first, so the last match is the oldest
    if found is None:
        return None
    return datetime.fromisoformat(found).astimezone(UTC)


def report(findings: list[Finding], season: int, run: str = 'Weekly update') -> str:
    if not findings:
        return f'Line Judge: every check holds for the {season} {run}.'
    lines = [f'Line Judge found {len(findings)} thing(s) the {season} {run} left wrong:', '']
    lines += [f'- **{f.check}**: {f.message}' for f in findings]
    return '\n'.join(lines)


def main(argv: list[str] | None = None, now: datetime | None = None,
         fetch: missed_dispatch.Fetch | None = missed_dispatch._gh_fetch) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('--season', type=int, required=True)
    ap.add_argument('--run-event')
    ap.add_argument('--run-started', help='the judged run\'s start, ISO 8601')
    ap.add_argument('--report', help='also write the report to this file')
    ap.add_argument('--workflow', choices=sorted(RUNS), default=WORKFLOW.name,
                    help="the judged run's workflow file: which checks apply and whose slots on-time reads")
    args = ap.parse_args(argv)
    from src.sports.nfl.data_loader import load_schedule
    started = (datetime.fromisoformat(args.run_started.replace('Z', '+00:00'))
               if args.run_started else None)
    text_wf = (WORKFLOW.parent / args.workflow).read_text(encoding='utf-8')
    schedule, cancelled = load_schedule(args.season), load_cancelled_pairs(args.season)
    if args.workflow == 'nfl-weekend-refresh.yml':
        from src.sports.nfl.weekend_refresh import weeks_to_refresh
        findings = judge_refresh(args.season, schedule, cancelled, weeks_to_refresh(args.season),
                                 args.run_event, started, text_wf, fetch=fetch)
    else:
        findings = judge(args.season, schedule, now or datetime.now(UTC), locked_at, cancelled,
                         args.run_event, started, text_wf, fetch=fetch)
    text = report(findings, args.season, RUNS[args.workflow])
    print(text)
    if args.report:
        Path(args.report).write_text(text + '\n', encoding='utf-8')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
