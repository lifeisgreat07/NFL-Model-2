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


def gh_api(path: str) -> list[dict[str, Any]]:
    """Every item of a paginated list endpoint, one JSON object a line."""
    key = 'jobs' if '/jobs' in path else 'workflow_runs'
    r = subprocess.run(['gh', 'api', '--paginate', path, '--jq', f'.{key}[] | tojson'],
                       capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f'gh api {path} failed: {(r.stderr or r.stdout).strip()}')
    return [json.loads(line) for line in r.stdout.splitlines() if line.strip()]


def main(argv: Sequence[str] | None = None, now: datetime | None = None, api: Api = gh_api,
         post: Post = alerts.open_or_comment) -> int:
    ap = argparse.ArgumentParser(description="Count Line Judge's verdicts for last week.")
    ap.add_argument('--dry-run', action='store_true', help='print the digest; post nothing')
    args = ap.parse_args(argv)
    start, end = last_week(now or datetime.now(UTC))
    body = digest({wf: tally(wf, start, end, api) for wf in JUDGED}, start, end)
    print(body)
    if not args.dry_run:
        post(TITLE, body)
    return 0


if __name__ == '__main__':
    sys.exit(main())
