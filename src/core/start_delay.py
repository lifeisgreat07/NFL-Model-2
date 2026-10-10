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

A run GitHub's cron started always serves a slot. A dispatched run (by
cron-job.org at a slot, or by hand) serves one only if it started within
`OFF_SLOT_HOURS` of it; later than that it was started by hand for its own
reason, and the line says so instead of calling it a day late, with no
warning.

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
#: The daily sports save a game's pick at the last run before it starts,
#: with an hour of slack (`SLACK` in src/sports/<sport>/lock.py), so a run
#: more than an hour late can miss a game the run before left to it. They
#: are warned at that hour, not at the NFL's seven (Stage 68 item 3).
WARN_HOURS_FOR = {'nhl-daily.yml': 1, 'nba-daily.yml': 1}
#: A dispatched run this long after the last slot is not serving it.
OFF_SLOT_HOURS = 12
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


def served_delay(exprs: list[str], started: datetime, event: str | None) -> timedelta | None:
    """How late a run started for the slot it served, or None when it served
    none: no slot found, or a dispatched run more than OFF_SLOT_HOURS after
    the last one."""
    slot = latest_slot(exprs, started)
    if slot is None:
        return None
    delay = started - slot[0]
    if event != 'schedule' and delay > timedelta(hours=OFF_SLOT_HOURS):
        return None
    return delay


def hm(delta: timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    return f'{minutes // 60}h {minutes % 60:02d}m'


def report(workflow_text: str, now: datetime, event: str | None,
           schedule: str | None = None, warn_hours: int = WARN_HOURS) -> tuple[str, bool]:
    """The summary line, and whether it is a warning.

    `schedule` is the cron line that fired a scheduled run
    (`github.event.schedule`). Given, the run is measured against that
    line's own latest slot: a 14:00 run GitHub starts at 21:20 is seven
    hours late, not twenty minutes after the 21:00 slot."""
    exprs = crons(workflow_text)
    if not exprs:
        return 'Start delay: this workflow has no cron line to measure against.', False
    if event == 'schedule' and schedule in exprs:
        exprs = [schedule]
    slot = latest_slot(exprs, now)
    if slot is None:
        return f'Start delay: no slot in the last {LOOKBACK.days} days for {exprs}.', True
    at, expr = slot
    delay = now - at
    by = f', started by {event}' if event else ''
    if served_delay(exprs, now, event) is None:
        return (f"Start delay: none; started by {event or 'hand'} {hm(delay)} after the last slot "
                f"({at:%a %H:%M} UTC), so it serves no slot."), False
    line = (f"Start delay: {hm(delay)} after the {at:%a %H:%M} UTC slot (cron '{expr}'){by}.")
    return line, delay >= timedelta(hours=warn_hours)


def main(argv: list[str] | None = None, now: datetime | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print('usage: python -m src.core.start_delay .github/workflows/<file>.yml')
        return 2
    warn_hours = WARN_HOURS_FOR.get(Path(args[0]).name, WARN_HOURS)
    line, warn = report(Path(args[0]).read_text(encoding='utf-8'), now or datetime.now(UTC),
                        os.environ.get('GITHUB_EVENT_NAME'), os.environ.get('CRON_SCHEDULE') or None,
                        warn_hours)
    print(line)
    if warn:
        print(f'::warning title=Late start::{line} Warned at {warn_hours} hours.')
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as fh:
            fh.write(line + (f' **Late: {warn_hours} hours or more.**' if warn else '') + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
