# 0005. Scheduled runs are started on time by cron-job.org

## Decision

cron-job.org sends a `workflow_dispatch` request at each scheduled time:
the nightly canary (06:00 UTC), the nightly mutation slice (06:30), and the
weekend refreshes (Friday 05:17, Sunday 21:47, Monday 01:47 and 05:37).
GitHub's own `schedule:` cron stays in each workflow as the fallback. The
Weekly update's job exists and stays off until the slot guard (Stage 42)
makes a second run of the same slot harmless.

It holds one fine-grained GitHub token: this repository only, Actions read
and write, expiring after a year. It can start a workflow; it cannot push.

Mark's pick on 2026-10-04: a web page, with nothing to deploy or maintain.

## Why

- GitHub's `schedule:` trigger is best-effort. Runs here started on time
  until 2026-09-22 and 3.5 to 6.5 hours late after, while
  `workflow_dispatch` runs started within seconds throughout. The delay is
  GitHub's queue, so the fix replaces the trigger, not the runner.
- On 2026-10-05 the requested runs started within a minute of their times.
  GitHub's late copies of the same slots arrived 2h24m to 8h39m after them.

## What it costs

- Every slot now runs twice: on time, and again when GitHub's cron fires.
  For a read-only job that costs nothing. For a job that commits, the late
  copy commits too (the weekend refresh's do, harmlessly). For the Weekly
  update it is not harmless: a late copy of a dispatched Thursday lock
  would see the week locked, move to the next one and save a preview
  mid-week. Hence the slot guard before its job is switched on.
  **The guard exists since Stage 42 item 3**: the Weekly update's first
  job, `slot-guard`, works out the run's slot and reads the last served
  slot from `data/nfl/run_slots/weekly-update.json` on origin/main; a slot
  already served is skipped, and the runs queue in one concurrency group.
  A guard that fails lets the week run (fail open) and raises its own
  alert. `tests/test_slot_guard.py` holds it.
- A credential outside GitHub, with an expiry to renew.
- A missed request is seen only through cron-job.org's failure e-mail and
  the delay line in the run that did start.

## What would reopen it

GitHub's scheduler running on time again for long enough to trust, or the
token or service becoming unavailable.

Sources: `docs/stage-history.md`, Stage 42; `memory/2026-10-04.md`.
