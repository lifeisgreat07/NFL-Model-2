# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-10-05, evening ET (#292 and #294 merged: Stages 50 and 51; nine post-lock branches prepared)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked
figure. `src/` is packaged: run modules with `python -m src.<package>.<module>`.
The dashboard template is parts under `src/dashboard/`, joined by
`src/pipeline/template_parts.py`. Read it with `read_template()`, never one
part as the page (traps). `src/core/` and `src/sports/nhl/` exist since #292
and #294; the NFL is still `src/pipeline/` until Stage 52 merges.

**Next action: the read-only checks**: Tuesday 2026-10-06's Weekly update
(`DRIFT CHECK: OK` in its run summary, a "Model A, log loss" section, Pages
from `src/dashboard/`, its row in the runs table), the nightly shuffled
suite's first run (07:15 UTC, GitHub cron only), and **Thursday 2026-10-08,
the first LOCK on the new code**. Nothing that touches the weekly run, the
weekend refresh or the deploy merges until that lock has been seen to run.

**Mark delegated decisions to Claude on 2026-10-05 ("until I say so").**
Each one is logged with its reason in `memory/` and the Audit Response Log.

**Scheduled runs start from cron-job.org** (Stage 42; `docs/decisions/`),
GitHub's cron the fallback: canary 06:00, slice 06:30, refreshes Fri 05:17,
Sun 21:47, Mon 01:47 (no repo cron yet) and Mon 05:37 UTC. The QB routine
ran Monday 22:13 UTC on `src.pipeline` and opened no PR (week 5).

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Nine post-lock branches | Committed on the local Windows machine, one worktree each, not pushed; each has its mutation cases, all caught | The 10-08 lock, then one PR at a time in the order below |
| Stage 52 (NFL to `src/sports/nfl/`) | Built and proven on `s52-nfl-module` | Step 2's PRs, then the window after a Thursday lock; re-run the script on that day's `main` |
| cron-job.org dispatch | Six jobs on, Weekly update job off | Stage 42's slot guard merged; then Mark switches it on |
| Issue #287, and the Booth-failed issue for #292 | Both raised by infrastructure, not code (#292's audit was cancelled by GitHub's outage) | Mark closes them |
| Private vulnerability reporting | Off (SECURITY.md covers both) | Mark's choice, Settings, Security |
| Season Accuracy's forecast score | Merged (#160), not on the page yet | 50 graded games |
| TV exceptions for holiday and Saturday games | Weeks 12, 15, 16 | Sourced entries before those weeks |

## Queued, in order (after the 10-08 lock is seen to run)

The branches and their worktrees are listed in the session archive's handoff file.
1. Stage 42's slot guard (`s42-slot-guard`), then Mark switches on the Weekly update's cron-job.org job.
2. Stage 36 item 7 (`s36-7-folders`).
3. Stage 37 item 3 (`s37-3-final-status`), then the backfill of weeks 1 to 4's final snapshots.
4. Stage 37 item 4 (`s37-4-line-moves`), item 6 (`s37-6-neutral-site`).
5. Stage 41 item 5 (`s41-5-canary-sources`), item 7 (`s41-7-provenance`).
6. The Monday 01:47 fallback cron line (`s42-monday-fallback`).
7. The cancelled-game state (`s39-cancelled-state`).
8. Stage 52, then Mark re-points cron-job.org's jobs and the QB routine (step-by-step text to be written with the PR).
Then Stage 45 items 1 and 2; Stage 21 once week 5 is graded; Stages 53 to 61.

One branch at a time. Rebase each on `main` before opening, then run the
suite and the mutation scope at the exact head being opened (scope_run.py),
and list the case files. Keep counts out of commit messages. Branches that
change `tests/test_action_pins.py`'s counts or the same mutation case file
will need their numbers or anchors refreshed on rebase.

## Known and deliberately not fixed

- **Scheduled runs start hours late** on GitHub's cron; cron-job.org starts them on time.
- **Preview cards have no TV channel or team-news line**: those steps read locked weeks only (#204).
- **The link preview and share image say "The Pick'em Model"**: Mark's decision (#242).
- **The drift check re-tests a growing sample every week**, so it will sometimes flag by chance. R4 registered it as written.
- **A failed Thursday run leaves Thursday night's game unpicked** unless dispatched by hand that day. The failure opens an issue.
- **Mutation runs quote a count Booth cannot always rerun**: a large scope is UNVERIFIABLE by design; the files are listed.
- **Booth's prose can count an UNVERIFIABLE its block does not**: the run goes red over a SAFE TO MERGE comment (#286), and booth-alert's issue (#287) does not name that cause.
- **Season Accuracy's trend end-labels** stack where Model A and Model B end on the same value.
- **`check_scoped_test_counts` skips a count for a module that does not exist.**
- **Only the wrap-up gate and session-start recompute CLAUDE.md's `Suite:` line.**
- **A human approval leaves no artifact in the repo.** `memory/` records it.
- **60 of 496 team pairs sit under the CIEDE2000 floor on the Week Board's split bar, accepted 2026-09-21.**
- **The reproducibility audit flips between GitHub runners**; local Windows reproduces exactly.
- **`ubuntu-latest` moves to Ubuntu 26 from 2026-10-19** (GitHub's notice on every run). Nothing pins the image; watch the first runs after it.
