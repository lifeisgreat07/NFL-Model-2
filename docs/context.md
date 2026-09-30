# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-30, afternoon ET (third audit, 83/100: Stage 35; #249 and #250 merged)

---

## Right now

**Suite:** 4925 passing, none skipped, on `main` at `e9d8406` (after #248).
Not re-run on `main` since #249 and #250; the wrap-up recomputes it.

**Next action: check Thursday's lock run** (2026-10-01, cron 11:00 UTC; runs
start up to 6.5 hours late, so "not run yet" before ~17:30 UTC is normal).
Confirm it locked week 4 before the 00:15 UTC Friday kickoff, deleted
`predictions/preview/2026_week4.json` in the same commit, and pushed. It is
the first lock on the overnight code (`src/paths.py`, the split
`weekly_update.main`, logging, type hints): its log should read as week 3's
did, and its summary should say "Preview for 2026 week 4 removed" (#249). Not
started by 20:00 UTC: start "Weekly update" by hand. A scheduled check
(`trig_01HuuuPeAXBor9w6hPcxqVLP`) runs this at Thursday 17:00 UTC.

Stage 35 (`docs/stage-history.md`): 1 and 1b done (#249, #250); 2 open as
#251; 3(c) on `s35-tooling-remnants`; 3(a) `s35-drift-baseline` and 3(b)
`s35-pipeline-remnants` wait for the lock. Then, after the lock, in order:
1. **Stage 35 items 3(a) and 3(b).**
2. **Stage 32 item 14, package `src/`** (Mark: after the lock), proven by the
   reproducibility audit and a byte-identical page.
3. **Ruff `I` and `UP`** (item 18's tail): one dry run, then one PR.
4. **Stage 33 item 23** (line snapshots for every locked, ungraded week).
5. **Stage 33 items 21, 22, 24**: registrations shown to Mark before code.
6. **Stage 33 item 26** when the next page-sized feature starts; then Stage
   34 item 32 (real testers, the fourth audit).

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Thursday lock run | Due Thu 2026-10-01 11:00 UTC | Check as above |
| QB overrides | Must be merged by 11:00 UTC Thursday | Mark, Wednesday evening |
| QB override routine prompt | Still names the old lock time | Mark edits it at claude.ai/code/routines (agents cannot) |
| claude-code-action pin | On v1.0.236 | A hand bump when a release matters |
| Season Accuracy's forecast score | Merged (#160), not on the page yet | 50 graded games: after week 4 at the earliest |
| TV exceptions for holiday and Saturday games | Weeks 12, 15, 16 | Sourced entries in `data/tv/exceptions.json` before those weeks |
| Audit Response Log | Updated 2026-09-30 | Fable, for the next audit |
| Drift issue | Never fired on a real event | A real event |

## Queued, in order

1. The five after-lock items above.
2. **Stages 20 to 22**: 20 needs five real testers; 21 waits for week 5; 22 comes from 20.
3. **Stage 28** and the closing-line backtest: after the regular season.

Merge one branch at a time: every branch that adds a mutation case file
moves the README count, so two open at once always conflict. Run the suite
and the mutation scope at the exact head being opened, after the last
rebase, and describe the scope as run whole with both counts, listing the
case files (Booth cannot reproduce a count whose selection it cannot see).

## Known and deliberately not fixed

- **Scheduled runs start hours late** (3.5 to 6.5h since 2026-09-24). Absorbed by the 11:00 Thursday lock and 8h slack, not fixed; GitHub's queue is not ours.
- **Preview cards have no TV channel or team-news line**: those steps read locked weeks only (#204).
- **The link preview and share image say "The Pick'em Model"**: Mark's decision, recorded in `test_product_name`; the re-audit's redraw was declined (#242).
- **The drift check is on accuracy**, which cannot carry a result at this sample size. Stage 33 item 24 is the fix, as a registration.
- **A failed Thursday run leaves Thursday night's game unpicked** unless someone dispatches the workflow by hand that day. Since #105 the failure opens an issue.
- **Mutation runs quote a count Booth cannot always rerun**: a large scope is UNVERIFIABLE in the audit by design; list the files so the selection is at least checkable.
- **A Booth header can disagree with its verdict block**, logged by `cross_check()`. It has cost nothing yet.
- **Season Accuracy's trend end-labels** stack where Model A and Model B end on the same value. Not yet looked at.
- **`check_scoped_test_counts` skips a count for a module that does not exist** — a DELETED module passes silently.
- **Only the wrap-up gate and session-start recompute CLAUDE.md's `Suite:` line.** Both manual, accepted.
- **Preflight checks commits and suite counts, not every number in prose.** Read the body against `git log` before opening.
- **A human approval leaves no artifact in the repo.** `memory/` is what records it.
- **Browser checks does not click.** Interaction-only states are covered by static tests; since #245 the tie, skipped-week and stale-preview states are built and checked.
- **60 of 496 team pairs sit under the CIEDE2000 floor on the Week Board's split bar, accepted 2026-09-21.**
- **The Booth report check cannot tell WHY a run posted nothing.** Since #101 a failed audit at least opens an issue.
