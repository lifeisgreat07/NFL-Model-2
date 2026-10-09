"""How late a scheduled run started (Stage 42 item 1).

GitHub's `schedule:` trigger is best effort: from 2026-09-22 its runs here
started 3.5 to 6.5 hours late. cron-job.org now dispatches each slot on time
(Stage 42 item 2) and GitHub's own cron is the fallback, so a late start
should be rare, and it should never be silent. Every scheduled workflow runs
this as its first step after Python is set up. It reads the workflow's own
`cron:` lines, finds the latest slot at or before now, and writes one line to
the run's summary:

    Start delay: 0h 03m after the Fri 05:17 UTC slot (cron '17 5 * * 5'), started by workflow_dispatch.

At `WARN_HOURS` or more it also writes a `::warning` annotation, which shows
on the run's page and is readable without signing in. Seven hours is one
under the Weekly update's `LOCK_SLACK` (eight), past which a Thursday run
would no longer lock before the first kickoff; tests/test_start_delay.py
holds the two together.

The clock is read when this step runs, a few seconds after the job starts
(checkout and Python's set-up), so the delay is that much later than the
run's own `run_started_at`: small next to the hours it is there to show.

A run started by hand at an odd time is measured against the latest slot
before it, which is the slot it serves.

Run with: python -m src.core.start_delay .github/workflows/<file>.yml
"""
from __future__ import annotations

import os
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

#: A start this late or later is warned about.
WARN_HOURS = 7
#: How far back to look for a slot: every workflow here runs at least weekly.
LOOKBACK = timedelta(days=8)
CRON_LINE = re.compile(r'''^\s*-\s*cron:\s*['"]([^'"]+)['"]''', re.M)
RANGES = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7))


def crons(workflow_text: str) -> list[str]:
    """The workflow's cron expressions, in file order."""
    return CRON_LINE.findall(workflow_text)


def _field(spec: str, lo: int, hi: int) -> set[int]:
    out: set[int] = set()
    for part in spec.split(','):
        step = 1
        if '/' in part:
            part, s = part.split('/', 1)
            step = int(s)
        if part == '*':
            a, b = lo, hi
        elif '-' in part:
            a, b = (int(x) for x in part.split('-', 1))
        else:
            a = b = int(part)
            if step != 1:
                b = hi
        if not (lo <= a <= b <= hi) or step < 1:
            raise ValueError(f'cron field {spec!r} is out of range {lo}-{hi}')
        out.update(range(a, b + 1, step))
    return out


class Cron:
    """A five-field cron expression, as GitHub reads one (UTC; day of month
    and day of week OR together when both are restricted; 7 is Sunday)."""

    def __init__(self, expr: str) -> None:
        fields = expr.split()
        if len(fields) != 5:
            raise ValueError(f'{expr!r} is not five fields')
        self.expr = expr
        sets = [_field(f, lo, hi) for f, (lo, hi) in zip(fields, RANGES)]
        self.minutes, self.hours, self.dom, self.months, dow = sets
        self.dow = {d % 7 for d in dow}
        self.dom_any = fields[2] == '*'
        self.dow_any = fields[4] == '*'

    def matches(self, t: datetime) -> bool:
        if t.minute not in self.minutes or t.hour not in self.hours or t.month not in self.months:
            return False
        dom_ok = t.day in self.dom
        dow_ok = (t.isoweekday() % 7) in self.dow
        if self.dom_any and self.dow_any:
            return True
        if self.dom_any:
            return dow_ok
        if self.dow_any:
            return dom_ok
        return dom_ok or dow_ok

    def latest(self, now: datetime) -> datetime | None:
        """The latest minute at or before `now` that this expression fires on."""
        t = now.astimezone(UTC).replace(second=0, microsecond=0)
        stop = t - LOOKBACK
        while t >= stop:
            if self.matches(t):
                return t
            t -= timedelta(minutes=1)
        return None


def latest_slot(exprs: list[str], now: datetime) -> tuple[datetime, str] | None:
    """The latest slot at or before `now` over all the expressions."""
    found = [(t, e) for e in exprs if (t := Cron(e).latest(now)) is not None]
    return max(found) if found else None


def hm(delta: timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    return f'{minutes // 60}h {minutes % 60:02d}m'


def report(workflow_text: str, now: datetime, event: str | None) -> tuple[str, bool]:
    """The summary line, and whether it is a warning."""
    exprs = crons(workflow_text)
    if not exprs:
        return 'Start delay: this workflow has no cron line to measure against.', False
    slot = latest_slot(exprs, now)
    if slot is None:
        return f'Start delay: no slot in the last {LOOKBACK.days} days for {exprs}.', True
    at, expr = slot
    delay = now - at
    by = f', started by {event}' if event else ''
    line = (f"Start delay: {hm(delay)} after the {at:%a %H:%M} UTC slot (cron '{expr}'){by}.")
    return line, delay >= timedelta(hours=WARN_HOURS)


def main(argv: list[str] | None = None, now: datetime | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print('usage: python -m src.core.start_delay .github/workflows/<file>.yml')
        return 2
    line, warn = report(Path(args[0]).read_text(encoding='utf-8'), now or datetime.now(UTC),
                        os.environ.get('GITHUB_EVENT_NAME'))
    print(line)
    if warn:
        print(f'::warning title=Late start::{line} Warned at {WARN_HOURS} hours.')
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as fh:
            fh.write(line + (f' **Late: {WARN_HOURS} hours or more.**' if warn else '') + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
