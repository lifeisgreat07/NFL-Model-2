# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-28, late night (#178 to #190 merged)

---

## Right now

**Suite:** 4056 passing, none skipped — `python -B -m pytest -q -p no:cacheprovider`
on `main` at `03ca571` (after #190), HEAD level with origin.

**Next action:** Stage 26 item 6 (disclosure buttons, s26a) is the open PR;
merge it on Booth SAFE TO MERGE, then open the next prepared branch, each
rebased with the next README case-file count: s26b (item 7, `scope` on table
headers), s26c (item 8, chart labels; the calibration chart does not draw
yet, too few games), s26d (item 9, chip state), s26e (item 10, reliability
points one Tab stop), s26f (item 11, page bytes: 741,803 to 435,749, budget
800,000), s27b (27.2, nightly mutation slice), s27c (27.3, ruff), and s27a
(27.1, action pins) last: it edits Booth's workflow, so it needs Mark's
review. Worktrees under the session archive. Tuesday's weekly summary is
11:00 UTC; Thursday's lock run 16:00 UTC.

**Done tonight:** Stage 23 finished (#178, the collector keeps only Booth's
two accounts: 220 audits logged). Stage 24 finished (#180 timeouts, #181
never save an empty week). Stage 25 finished (#182 to #190). The QB
routine's first run opened #179 (TB: Jalon Daniels), audited and merged.

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
   day; items and order in CLAUDE.md). Stages 23, 24 and 25 done. Stage 26
   items 6 to 11 and Stage 27 items 1 to 3 prepared on branches; Stage 26
   items 1 to 5 and Stage 27 item 4 (Dependabot, Mark's call) not started.
   One PR open at a time.
2. **Stages 20 to 22**: 20 needs five real testers and comes after Stage 26;
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
