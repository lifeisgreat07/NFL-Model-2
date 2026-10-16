"""Did cron-job.org start this slot? (Stage 42 item 4.)

cron-job.org starts each scheduled workflow on time with `workflow_dispatch`
(decision record 0005), and GitHub's own `schedule:` cron stays as the
fallback. That record said a missed request would be seen through
cron-job.org's failure e-mail and the delay line of the run that did start.
Neither sees a job that never sends at all: cron-job.org e-mails only when
GitHub refuses a request, and the delay line is a warning annotation on a
run nobody opens, written for every late GitHub copy whether or not the
dispatch came. Two jobs made on 2026-10-09 (the NBA's 16:00 and the NFL's
Saturday 05:17) never fired, and that was found days later by reading the
Actions history by hand.

So every run GitHub's cron starts, for a slot cron-job.org is meant to
cover, asks the Actions API whether a `workflow_dispatch` run of the same
workflow started within `GRACE` of that slot:

  covered   -- one did. This run is GitHub's late copy; the summary says so.
  missed    -- none did. cron-job.org did not start this slot, so the alert
               issue for this workflow and slot time is opened, or commented
               on when it is already open (src/core/alerts.py: one issue per
               problem, not one per day).
  too early -- GitHub's cron itself started within GRACE of the slot, so a
               dispatch could still be on its way. Nothing is judged.

`DISPATCHED` lists the cron lines cron-job.org covers and `NOT_DISPATCHED`
the workflows it deliberately does not, each with its reason;
tests/test_missed_dispatch.py holds every cron line of every workflow to
exactly one of the two, and every covered workflow to running this step.

The check never fails its run. An Actions API that cannot be read, or an
alert that cannot be raised, is said in the summary and left there: the run
itself matters more than knowing who started it.

Run with: python -m src.core.missed_dispatch .github/workflows/<file>.yml
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.core import alerts
from src.core.start_delay import latest_slot

#: A dispatch this long after its slot still covers it; cron-job.org's start
#: within a minute (decision record 0005). Also how late GitHub's own run
#: must start before a missing dispatch is judged.
GRACE = timedelta(minutes=15)
#: A dispatch this long BEFORE the slot covers it too: a run's start can
#: read a few seconds early against a whole-minute cron.
EARLY = timedelta(minutes=2)

#: Workflow file -> the cron lines cron-job.org sends a dispatch for
#: (decision record 0005; the NHL's and NBA's from Stages 61 and 65).
DISPATCHED: dict[str, tuple[str, ...]] = {
    'nfl-weekly-update.yml': ('0 11 * * 2', '0 11 * * 4'),
    'nfl-weekend-refresh.yml': ('17 5 * * 5', '17 5 * * 6', '47 21 * * 0', '47 1 * * 1',
                                '37 5 * * 1'),
    'nfl-nightly-canary.yml': ('0 6 * * *',),
    'nightly-mutation.yml': ('30 6 * * *',),
    'nightly-dependency-audit.yml': ('45 7 * * *',),
    'nhl-daily.yml': ('0 14 * * *', '0 21 * * *'),
    'nhl-canary.yml': ('40 6 * * *',),
    'nba-daily.yml': ('0 16 * * *', '30 21 * * *'),
    'nba-canary.yml': ('50 6 * * *',),
}
#: Workflow file -> why its cron is left to GitHub alone.
NOT_DISPATCHED: dict[str, str] = {
    'nightly-random-order.yml': 'reads main and writes nothing, so a late start costs nothing',
    'line-judge-digest.yml': 'a weekly count posted a few hours late costs nothing',
}

Fetch = Callable[[str, datetime], list[datetime]]
Alert = Callable[[str, str], object]


def judge(slot: datetime, started: datetime, dispatches: Sequence[datetime]) -> str:
    """'covered', 'missed' or 'too early', for a GitHub cron run that started
    at `started` for `slot`, given when this workflow's dispatched runs
    started."""
    if any(slot - EARLY <= d <= slot + GRACE for d in dispatches):
        return 'covered'
    if started - slot < GRACE:
        return 'too early'
    return 'missed'


def _gh_fetch(workflow: str, slot: datetime) -> list[datetime]:
    """Start times of this workflow's dispatched runs created from just
    before `slot`, read with the run's own token (`actions: read`)."""
    repo = os.environ['GITHUB_REPOSITORY']
    since = (slot - EARLY).strftime('%Y-%m-%dT%H:%M:%SZ')
    r = subprocess.run(['gh', 'api', f'repos/{repo}/actions/workflows/{workflow}/runs'
                        f'?event=workflow_dispatch&per_page=30&created=%3E%3D{since}'],
                       capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout).strip())
    return [datetime.fromisoformat(x['run_started_at'].replace('Z', '+00:00'))
            for x in json.loads(r.stdout)['workflow_runs'] if x.get('run_started_at')]


def title(name: str, slot: datetime) -> str:
    """One issue per workflow and slot time: a job that never fires comments
    on the same issue each day until it is fixed and the issue closed."""
    return f'{name}: cron-job.org did not start the {slot:%H:%M} UTC run'


def check(workflow: str, name: str, event: str | None, cron: str | None, now: datetime,
          fetch: Fetch = _gh_fetch, alert: Alert = alerts.open_or_comment,
          run_url: str = '') -> str:
    """This run's summary line, raising the alert when its slot was missed.
    Only a run GitHub's cron started, on a covered line, is judged."""
    if event != 'schedule':
        return f"Dispatch check: not judged; this run was started by {event or 'hand'}."
    if cron not in DISPATCHED.get(workflow, ()):
        return f'Dispatch check: not judged; cron-job.org does not cover {cron!r} for {workflow}.'
    found = latest_slot([cron], now)
    if found is None:
        return f'Dispatch check: no {cron!r} slot found before now; not judged.'
    at = found[0]
    try:
        dispatches = fetch(workflow, at)
    except Exception as e:  # the run matters more than this check
        return f'Dispatch check: could not read the Actions API ({e}); not judged.'
    verdict = judge(at, now, dispatches)
    if verdict == 'covered':
        return (f"Dispatch check: cron-job.org started the {at:%a %H:%M} UTC slot; "
                f"this is GitHub's late copy of it.")
    if verdict == 'too early':
        return f'Dispatch check: GitHub started the {at:%a %H:%M} UTC slot on time; not judged.'
    minutes = int((now - at).total_seconds() // 60)
    body = (f"cron-job.org did not start `{workflow}`'s {at:%a %Y-%m-%d %H:%M} UTC slot "
            f"(cron `{cron}`): no `workflow_dispatch` run began within "
            f"{int(GRACE.total_seconds() // 60)} minutes of it. GitHub's own cron "
            f"started it {minutes // 60}h {minutes % 60:02d}m late instead.\n\n"
            f"Check this job in the cron-job.org account: enabled, its URL naming "
            f"`{workflow}`, and its token not expired. Close this issue once it fires "
            f"on time; the next miss opens a fresh one.\n\n{run_url}").strip()
    alert(title(name, at), body)
    return f'Dispatch check: **cron-job.org did not start the {at:%a %H:%M} UTC slot**; alert raised.'


def workflow_name(text: str, fallback: str) -> str:
    """The workflow's top-level `name:`."""
    for line in text.splitlines():
        if line.startswith('name:'):
            return line.split(':', 1)[1].strip().strip('\'"')
    return fallback


def main(argv: Sequence[str] | None = None, now: datetime | None = None,
         fetch: Fetch = _gh_fetch, alert: Alert = alerts.open_or_comment) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    if len(args) != 1:
        print('usage: python -m src.core.missed_dispatch .github/workflows/<file>.yml')
        return 2
    path = Path(args[0])
    env = os.environ
    run_url = ''
    if env.get('GITHUB_RUN_ID'):
        run_url = (f"{env.get('GITHUB_SERVER_URL', 'https://github.com')}/"
                   f"{env.get('GITHUB_REPOSITORY')}/actions/runs/{env['GITHUB_RUN_ID']}")
    try:
        line = check(path.name, workflow_name(path.read_text(encoding='utf-8'), path.stem),
                     env.get('GITHUB_EVENT_NAME'), env.get('CRON_SCHEDULE') or None,
                     now or datetime.now(UTC), fetch=fetch, alert=alert, run_url=run_url)
    except Exception as e:  # e.g. the alert itself could not be raised
        line = f'Dispatch check: failed ({e}); not judged.'
    print(line)
    summary = env.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as fh:
            fh.write(line + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
