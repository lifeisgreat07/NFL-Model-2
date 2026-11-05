"""
Line Judge's weekly digest (Stage 44 item 5).

Line Judge runs as the `line-judge` job of the four workflows that leave
state on main, and stays silent when the run was right. Silence is also what
a judge that stopped running looks like, so once a week this counts, from the
Actions API, how each of those workflows' runs in the last Monday-to-Sunday
week (UTC) were judged, and comments the count on the standing issue
"Line Judge weekly digest" through src/core/alerts.py:

    Line Judge, Mon 2026-10-05 to Sun 2026-10-11: 30 runs judged, 29 right,
    1 with findings; 2 not judged.

then a line per workflow and a link to every run that had findings. Written
by plain code (Mark, 2026-10-15): the counts are the whole message, and a
model adds nothing to them.

A run is "judged" when its line-judge job finished; "right" when that job
passed; "with findings" when it failed (its own alert says what was found).
"Not judged" is a run whose line-judge job was skipped or cancelled -- the
run itself failed, and raised its own alert -- or has none. A week with no
judged run at all is said first, in bold: it is the failure this exists for.

Stage 93 item 19 (audit 7 R10): the digest also reads the record
`src/core/start_delay.py` keeps of every copy GitHub's cron started for the
three lock-writing runs, and gives each sport's latest start in the last
30 days against its lock slack. GitHub's copy is the fallback for a slot
cron-job.org missed; when the NFL's came within an hour of its eight-hour
slack, the next late one could lock nothing, and the digest fails (after
posting) so the run's alert says so. The day sports' slack is one hour,
which a GitHub copy has never met, so for them the line is reported, not
failed: their missed slots are caught by the page build (Stage 93 item 20).

Run with: python -m src.core.line_judge_digest [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from src.core import alerts

TITLE = 'Line Judge weekly digest'
JOB = 'line-judge'
#: Workflow file -> its name in the digest, in the order the digest lists them.
JUDGED: dict[str, str] = {
    'nfl-weekly-update.yml': 'NFL Weekly update',
    'nfl-weekend-refresh.yml': 'NFL Weekend refresh',
    'nhl-daily.yml': 'NHL daily run',
    'nba-daily.yml': 'NBA daily run',
}

#: Each sport's record of late GitHub copies, and its lock slack in hours (the NFL's
#: LOCK_SLACK in weekly_update.py, the day sports' SLACK in their lock.py; a test holds them).
ROOT = Path(__file__).resolve().parents[2]
SLACK_HOURS = {'nfl': 8.0, 'nhl': 1.0, 'nba': 1.0}
#: The sports whose digest fails when a copy came within an hour of the slack.
FAILS_ON_SLACK = ('nfl',)
LATE_WINDOW = timedelta(days=30)

Api = Callable[[str], list[dict[str, Any]]]
Post = Callable[[str, str], object]


@dataclass
class Tally:
    right: int = 0
    found: list[str] = field(default_factory=list)  # run links
    not_judged: int = 0

    @property
    def judged(self) -> int:
        return self.right + len(self.found)


def last_week(now: datetime) -> tuple[date, date]:
    """The Monday and Sunday (UTC) of the last whole week before `now`."""
    today = now.astimezone(UTC).date()
    monday = today - timedelta(days=today.weekday() + 7)
    return monday, monday + timedelta(days=6)


def verdict(jobs: list[dict[str, Any]]) -> str:
    """'right', 'found', 'not judged' or 'running' for one run, from its jobs."""
    judge = next((j for j in jobs if j.get('name') == JOB), None)
    if judge is None:
        return 'not judged'
    if judge.get('status') != 'completed':
        return 'running'
    return {'success': 'right', 'failure': 'found'}.get(judge.get('conclusion') or '', 'not judged')


def tally(workflow: str, start: date, end: date, api: Api) -> Tally:
    out = Tally()
    runs = api(f'repos/{{owner}}/{{repo}}/actions/workflows/{workflow}/runs'
               f'?per_page=100&created={start:%Y-%m-%d}..{end:%Y-%m-%d}')
    for run in runs:
        v = verdict(api(f"repos/{{owner}}/{{repo}}/actions/runs/{run['id']}/jobs?per_page=100"))
        if v == 'right':
            out.right += 1
        elif v == 'found':
            out.found.append(str(run.get('html_url', run['id'])))
        elif v == 'not judged':
            out.not_judged += 1
    return out


def _runs(n: int) -> str:
    return f'{n} run' + ('' if n == 1 else 's')


def digest(tallies: dict[str, Tally], start: date, end: date) -> str:
    judged = sum(t.judged for t in tallies.values())
    found = sum(len(t.found) for t in tallies.values())
    right = sum(t.right for t in tallies.values())
    skipped = sum(t.not_judged for t in tallies.values())
    head = (f'Line Judge, {start:%a %Y-%m-%d} to {end:%a %Y-%m-%d}: {_runs(judged)} judged, '
            f'{right} right, {found} with findings; {skipped} not judged.')
    lines = []
    if judged == 0:
        lines.append('**No run was judged this week.** Either nothing ran or the line-judge jobs did not.')
        lines.append('')
    lines.append(head)
    lines.append('')
    for workflow, name in JUDGED.items():
        t = tallies.get(workflow, Tally())
        lines.append(f'- {name}: {_runs(t.judged)} judged, {t.right} right, '
                     f'{len(t.found)} with findings, {t.not_judged} not judged.')
    links = [u for wf in JUDGED for u in tallies.get(wf, Tally()).found]
    if links:
        lines.append('')
        lines.append('Runs with findings:')
        lines += [f'- {u}' for u in links]
    return '\n'.join(lines) + '\n'


def late_copies(now: datetime, root: Path = ROOT) -> tuple[list[str], list[str]]:
    """(a line per sport, the sports whose latest copy came within an hour of the slack)."""
    lines, close = [], []
    for sport, slack in SLACK_HOURS.items():
        path = root / 'data' / sport / 'run_delays.json'
        entries = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
        recent = [e for e in entries
                  if now - datetime.fromisoformat(str(e['started']).replace('Z', '+00:00')) <= LATE_WINDOW]
        if not recent:
            lines.append(f'- {sport.upper()}: no copy started by GitHub\'s cron in the last 30 days.')
            continue
        worst = max(int(e['delay_minutes']) for e in recent)
        near = worst >= (slack - 1) * 60
        copies = f'{len(recent)} cop' + ('y' if len(recent) == 1 else 'ies')
        hours = f'{slack:g} hour' + ('' if slack == 1 else 's')
        lines.append(f'- {sport.upper()}: {copies} started by GitHub\'s cron in the last 30 days, '
                     f'the latest {worst // 60}h {worst % 60:02d}m after its slot, against a lock slack of '
                     f'{hours}' + ('.' if not near else ': within an hour of it.'))
        if near and sport in FAILS_ON_SLACK:
            close.append(sport)
    return lines, close


def gh_api(path: str) -> list[dict[str, Any]]:
    """Every item of a paginated list endpoint, one JSON object a line."""
    key = 'jobs' if '/jobs' in path else 'workflow_runs'
    r = subprocess.run(['gh', 'api', '--paginate', path, '--jq', f'.{key}[] | tojson'],
                       capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f'gh api {path} failed: {(r.stderr or r.stdout).strip()}')
    return [json.loads(line) for line in r.stdout.splitlines() if line.strip()]


def main(argv: Sequence[str] | None = None, now: datetime | None = None, api: Api = gh_api,
         post: Post = alerts.open_or_comment, root: Path = ROOT) -> int:
    ap = argparse.ArgumentParser(description="Count Line Judge's verdicts for last week.")
    ap.add_argument('--dry-run', action='store_true', help='print the digest; post nothing')
    args = ap.parse_args(argv)
    now = now or datetime.now(UTC)
    start, end = last_week(now)
    body = digest({wf: tally(wf, start, end, api) for wf in JUDGED}, start, end)
    lines, close = late_copies(now, root)
    body += '\nLate copies of the lock-writing runs (Stage 93 item 19):\n\n' + '\n'.join(lines) + '\n'
    print(body)
    if not args.dry_run:
        post(TITLE, body)
    if close:
        print(f"LATE COPIES: {', '.join(s.upper() for s in close)} came within an hour of the lock slack.")
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
