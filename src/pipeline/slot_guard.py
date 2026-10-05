"""A scheduled slot is served once (Stage 42 item 3).

cron-job.org starts the Weekly update on time with `workflow_dispatch`, and
GitHub's own `schedule:` cron stays as the fallback. So every slot can run
twice: on time, and again when GitHub's late copy arrives, 2h24m to 8h39m
later on 2026-10-05. For a read-only job that costs nothing. For the Weekly
update it is not harmless: a late copy of a dispatched Thursday lock would
see the week locked, move to the next one and save a preview mid-week
(decision record 0005).

So a run first works out which slot it belongs to (the latest of
`SCHEDULED_RUNS_UTC` at or before now) and reads which slot was last
served from `data/run_slots/<workflow>.json` **on origin/main**, not in
its own checkout, which may predate the first run's commit. The same slot
again is skipped: nothing runs, nothing is committed. A run that serves its
slot marks it in the same commit as its data, and only when every step
before succeeded, so a failed run leaves the slot open and a run by hand
can retry it. A run by hand on a served slot needs `force`.

Run with:
    python -m src.pipeline.slot_guard check --workflow weekly-update [--force]
    python -m src.pipeline.slot_guard mark --workflow weekly-update --slot <iso>
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.pipeline.paths import DATA_DIR, ROOT

SLOT_DIR = DATA_DIR / 'run_slots'
#: (weekday Monday=0, hour, minute) UTC, per workflow. The Weekly update's
#: are weekly_update.SCHEDULED_RUNS_UTC, which tests/test_pick_lock_time.py
#: holds equal to the workflow's cron lines; tests/test_slot_guard.py holds
#: this table equal to that constant.
WORKFLOW_SLOTS: dict[str, tuple[tuple[int, int, int], ...]] = {
    'weekly-update': ((1, 11, 0), (3, 11, 0)),
}


def current_slot(now: datetime, runs: Sequence[tuple[int, int, int]]) -> datetime:
    """The latest scheduled time at or before `now` (UTC)."""
    now = now.astimezone(UTC)
    best = None
    for weekday, hour, minute in runs:
        day = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=(now.weekday() - weekday) % 7)
        t = day.replace(hour=hour, minute=minute)
        if t > now:
            t -= timedelta(days=7)
        if best is None or t > best:
            best = t
    if best is None:
        raise ValueError('no scheduled runs')
    return best


def slot_key(slot: datetime) -> str:
    return slot.astimezone(UTC).strftime('%Y-%m-%dT%H:%MZ')


def _git_show(path: str) -> str | None:
    """The file's text on origin/main, fetched fresh, or None if absent."""
    subprocess.run(['git', 'fetch', '--quiet', '--depth=1', 'origin', 'main'], cwd=ROOT, check=True)
    r = subprocess.run(['git', 'show', f'origin/main:{path}'], cwd=ROOT, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def served_slot(workflow: str, show: Callable[[str], str | None] = _git_show) -> str | None:
    text = show(f'data/run_slots/{workflow}.json')
    if text is None:
        return None
    return str(json.loads(text)['slot'])


def decide(slot: datetime, served: str | None, force: bool) -> tuple[bool, str]:
    """(run, why). The same slot twice is skipped unless forced."""
    key = slot_key(slot)
    if force:
        return True, f'slot {key}: forced'
    if served == key:
        return False, f'slot {key} was already served; this run changes nothing'
    return True, f'slot {key}: not yet served (last served: {served or "none"})'


def mark(workflow: str, slot: str, run_id: str | None, folder: Path = SLOT_DIR) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'{workflow}.json'
    path.write_text(json.dumps({'slot': slot, 'run_id': run_id}, indent=1) + '\n', encoding='utf-8')
    return path


def _output(name: str, value: str) -> None:
    out = os.environ.get('GITHUB_OUTPUT')
    if out:
        with open(out, 'a', encoding='utf-8') as f:
            f.write(f'{name}={value}\n')


def main(argv: list[str] | None = None, now: datetime | None = None,
         show: Callable[[str], str | None] = _git_show) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=('check', 'mark'))
    ap.add_argument('--workflow', required=True, choices=sorted(WORKFLOW_SLOTS))
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--slot')
    args = ap.parse_args(argv)
    if args.action == 'mark':
        if not args.slot:
            ap.error('mark needs --slot')
        print(f'marked {args.slot} in {mark(args.workflow, args.slot, os.environ.get("GITHUB_RUN_ID"))}')
        return 0
    slot = current_slot(now or datetime.now(UTC), WORKFLOW_SLOTS[args.workflow])
    run, why = decide(slot, served_slot(args.workflow, show), args.force)
    print(why)
    _output('run', 'true' if run else 'false')
    _output('slot', slot_key(slot))
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary and not run:
        with open(summary, 'a', encoding='utf-8') as f:
            f.write(f'**Skipped:** {why}.\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
