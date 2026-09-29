# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-29, early (#178 to #201 merged; session ended at Mark's request)

---

## Right now

**Suite:** 4278 passing, none skipped, on `main` at `d7ac3b1` (after #201).

**Next action: open the Stage 27 item 2 PR** from branch
`stage27-nightly-mutation-slice` (worktree `s27b` in the session archive,
head `d4822bb`). It is rebased onto main (README at 146 case files), pushed,
and done: full suite 4308 passed, mutation scope 3 files, 27 cases run whole,
14 case by case, all 27 caught. Its description is ready in the session archive's
pr-bodies folder (s27-2, the final version); run the preflight on it,
open the PR, and merge on Booth SAFE TO MERGE. If main has moved, rebase and
re-run first. Then, one PR at a time, each rebased with the next README
case-file count (147 next): s27c (27.3, ruff; later branches must then pass
`ruff check .`), srun (the mutation runner reads UTF-8; it touches
`tests/mutation/runner.py` like s27b, so expect a small conflict), and s27a (27.1, action
pins) last: it edits Booth's workflow, so it needs "Human review required:"
and Mark's OK, and the pin counts in its new test move by one checkout and
one setup-python once the nightly workflow is on main. Rebase can surface
tests merged since a branch was cut: run the full suite before the mutation
run. Mark's plan: finish Stage 27 next session; Stage 29 after that.

**Today:** Tuesday's weekly summary is 11:00 UTC; Thursday's lock run is
16:00 UTC on 2026-10-01.

**Done last night:** Stages 23 to 26 finished (#178 to #201). Stage 27
item 4: Mark said skip Dependabot. The QB routine's first run opened #179
(TB: Jalon Daniels), audited and merged.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| First weekly summary | Due Tue 2026-09-29 11:00 UTC | Open the run's page and check the summary reads right |
| Thursday lock run | Due Thu 2026-10-01 16:00 UTC | Check it started, locked before kickoff, and its push survived; week 4 is the first card with quarterback names and TV channels |
| Season Accuracy's forecast score | Merged (#160), not on the page yet | 50 graded games: after week 4 at the earliest |
| TV exceptions for holiday and Saturday games | Weeks 12, 15, 16 | Sourced entries in `data/tv/exceptions.json` before those weeks |
| Model Lab mappings | My calls, in #141 | Mark may overrule any (listed in `experiments/legacy/README.md`) |
| Drift issue | Never fired on a real event | A real event |
| #147's catch-up step under a race | Ran once with nothing to catch up | A refresh or weekly run during which main moves |

## Queued, in order

1. **Stages 23 to 29, from the 2026-09-28 audit** (approved by Mark the same
   day; items and order in CLAUDE.md). Stages 23 to 26 done. Stage 27
   items 1 to 3 on branches (item 2 ready to open); item 4 (Dependabot)
   skipped by Mark. Stage 28 waits for the regular season to end; Stage 29
   after Stage 27 (Mark, 2026-09-29).
   One PR open at a time.
2. **Stages 20 to 22**: 20 needs five real testers (Stage 26, its prerequisite, is done);
   21 waits for week 5; 22 comes from 20.
3. **Line movement and the closing-line backtest**: not before the 2026 regular season ends, beside Stage 28.

Merge one branch at a time: every branch that adds a mutation case file
moves the README count, so two open at once always conflict. Describe a
mutation scope as run whole, with both the whole-file and the case-by-case
counts (CLAUDE.md trap, #165).

## Known and deliberately not fixed

- **The drift check is on accuracy**, which cannot carry a result at this sample size. Its issue says so and points at log loss and Brier.
- **A failed Thursday run leaves Thursday night's game unpicked** unless someone dispatches the workflow by hand that day. Since #105 the failure opens an issue.
- **A Booth header can disagree with its verdict block**, logged by `cross_check()`. It has cost nothing yet.
- **Season Accuracy's trend end-labels**: where Model A and Model B end on the same value the labels stack beside one marker (seen in the README screenshot). Not yet looked at.
- **`tests/browser/check_page.py` flaked in Booth's environment** on 2 of 7 runs (#156 audit), unrelated to the change.
- **`check_scoped_test_counts` skips a count for a module that does not exist** — a DELETED module passes silently.
- **Only the wrap-up gate and session-start recompute CLAUDE.md's `Suite:` line.** Both manual, accepted.
- **Preflight checks commits and suite counts, not every number in prose.** Read the body against `git log` before opening.
- **A human approval leaves no artifact in the repo.** `memory/` is what records it.
- **Browser checks does not click.** Interaction-only states are covered by static tests.
- **60 of 496 team pairs sit under the CIEDE2000 floor on the Week Board's split bar, accepted 2026-09-21.**
- **The Booth report check cannot tell WHY a run posted nothing.** Since #101 a failed audit at least opens an issue.
