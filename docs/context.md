# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-10-06, early morning ET (#299 to #303 and #306 merged: the NHL's lock rule, colours, history and backtest, daily run, and its workflows; the NHL is live)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked
figure. `src/` is packaged: run modules with `python -m src.<package>.<module>`.
The dashboard template is parts under `src/dashboard/`, joined by
`src/pipeline/template_parts.py`. Read it with `read_template()`, never one
part as the page (traps). The NFL is still `src/pipeline/` until Stage 52
merges. **The NHL is live**: `.github/workflows/nhl-daily.yml` (14:00 and 21:00 UTC) saves and
grades its picks, and `.github/workflows/nhl-canary.yml` runs at 06:40 UTC, with "NHL: ..."
alerts through `src/core/alerts.py`. No page shows the NHL yet (Stage 57).

**Next action: the read-only checks**: the NHL daily run's first scheduled
runs (14:00 and 21:00 UTC 2026-10-06; picks in `predictions/nhl/2026/`),
Tuesday's Weekly update (`DRIFT CHECK: OK`, the "Model A, log loss"
section, its runs-table row), and **Thursday 2026-10-08, the first LOCK on
the new code**. Nothing that touches the weekly run, the weekend refresh or
the deploy merges until that lock has been seen to run.

**Mark delegated decisions to Claude on 2026-10-05 ("until I say so").**
Each one is logged with its reason in `memory/` and the Audit Response Log.

**Scheduled runs start from cron-job.org** (Stage 42; `docs/decisions/`),
GitHub's cron the fallback: canary 06:00, slice 06:30, refreshes Fri 05:17,
Sun 21:47, Mon 01:47 (no repo cron yet) and Mon 05:37 UTC. The NHL's jobs
are on GitHub's cron only until Mark adds cron-job.org jobs for them.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Nine post-lock branches | Committed locally, one worktree each, not pushed | The 10-08 lock, then one PR at a time in the order below |
| Stage 52 (NFL to `src/sports/nfl/`) | Built and proven on `s52-nfl-module`; migrate_nfl.py (session archive) now drops the NFL's alerts copy, the core's being there | Step 2's PRs, then the window after a Thursday lock |
| NHL standings odds (Stage 57 item 3) | `s58s-nhl-standings`, pushed, suite and scope run | Its PR, next |
| NBA (Stage 61) | Probe, data doc, registration draft, schedule and history modules built in the cloud copy; ESPN history being cached locally | Mark's call on a live NBA price: ESPN refuses runners |
| cron-job.org | Six NFL jobs on, Weekly update job off; no NHL jobs | Stage 42's slot guard; Mark adds the NHL's two |
| Issues #287, #297, #304, #305 | Raised by infrastructure, not code | Mark closes them |
| NHL board and home page (Stages 53, 57, 59) | Mark chose the designs 2026-10-05 | Stage 52, then Stage 53's per-sport pages |
| Private vulnerability reporting | Off (SECURITY.md covers both) | Mark's choice, Settings, Security |

## Queued, in order (after the 10-08 lock is seen to run)

The branches and their worktrees are listed in the session archive's handoff file.
1. Stage 42's slot guard (`s42-slot-guard`), then Mark switches on the Weekly update's cron-job.org job.
2. Stage 36 item 7 (`s36-7-folders`).
3. Stage 37 item 3 (`s37-3-final-status`), then the backfill of weeks 1 to 4's final snapshots.
4. Stage 37 item 4 (`s37-4-line-moves`), item 6 (`s37-6-neutral-site`).
5. Stage 41 item 5 (`s41-5-canary-sources`), item 7 (`s41-7-provenance`).
6. The Monday 01:47 fallback cron line (`s42-monday-fallback`).
7. The cancelled-game state (`s39-cancelled-state`).
8. Stage 52, then Mark re-points cron-job.org's jobs and the QB routine (stage52_repoint.md in the session archive).
Then Stages 53, 57 and 59 for the NHL's pages, Stage 45 items 1 and 2, Stage 21 once week 5 is graded.

One branch at a time. Rebase each on `main` before opening, then run the
suite and the mutation scope at the exact head (scope_run.py), and list the
case files. Keep counts out of commit messages. Branches that change
`tests/test_action_pins.py`'s counts (now 20) or a shared case file need
their numbers or anchors refreshed on rebase.

## Known and deliberately not fixed

- **Scheduled runs start hours late** on GitHub's cron; cron-job.org starts them on time.
- **Booth's audit can run past its 20-minute limit** on a big PR (#302, twice); a re-run finished in under 5.
- **Booth's prose can count an UNVERIFIABLE its block does not**: the run goes red over a SAFE TO MERGE comment (#286, #296, #303).
- **The drift check re-tests a growing sample every week**, so it will sometimes flag by chance. R4 registered it as written.
- **A failed Thursday run leaves Thursday night's game unpicked** unless dispatched by hand that day.
- **Mutation runs quote a count Booth cannot always rerun**: a large scope is UNVERIFIABLE by design; the files are listed.
- **Preview cards have no TV channel or team-news line**; **the share image says "The Pick'em Model"** (Mark, #242).
- **`check_scoped_test_counts` skips a count for a module that does not exist**; **only the wrap-up gate and session-start recompute CLAUDE.md's `Suite:` line.**
- **A human approval leaves no artifact in the repo.** `memory/` records it.
- **Season Accuracy's trend end-labels** stack where Model A and Model B end on the same value.
- **60 of 496 team pairs sit under the CIEDE2000 floor on the Week Board's split bar, accepted 2026-09-21.**
- **The reproducibility audit flips between GitHub runners**; local Windows reproduces exactly.
- **`ubuntu-latest` moves to Ubuntu 26 from 2026-10-19.** Nothing pins the image; watch the first runs after it.
