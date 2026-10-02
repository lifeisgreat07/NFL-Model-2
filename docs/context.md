# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-10-01, evening ET (week 4 locked; #253 and #254 merged; #255 open)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked
figure. Week 4 locked on Thursday's scheduled run (`c80cb28`), cleanly.

**Next action: #255 (Stage 32 item 14, package `src/`)** is open and waits
on Mark twice: its body says "Human review required" (it edits
the Booth workflow), and his QB routine's three `sys.path.insert(0,'src')`
commands must become `from src.pipeline...` before it merges (agents cannot
edit the routine; it next runs Monday 22:00 UTC). On his word: merge with
`merge_pr.ps1`. If `main` moves first, rebuild the branch from the session
archive's pkg scripts (build_branch) and rerun suite and whole corpus.
Then, in order:
1. **Ruff `I` and `UP`**: built and green as `s32-ruff-i-up` (worktree
   nfl-wt/ruff), stacked on #255. Rebase after #255, then suite and scope.
   UP031 stays off (regexes with braces), target py311.
2. **Stage 33 item 23** needs Mark's decision first: weekly runs never see
   a locked, ungraded week except at its own lock, so closing lines can only
   come from the weekend refresh, which the 2026-09-24 decision keeps away
   from `data/line_history/`. Recommendation: let it append there for
   locked, ungraded weeks only (picks stay single-writer).
3. **Stage 33 items 21, 22, 24**: drafts with Mark (R3's switching rule,
   R4's baseline); committed as a Stage 33 registry under experiments/
   before anything runs.
4. **Stage 33 item 26** when the next page-sized feature starts; then Stage
   34 item 32 (real testers, the fourth audit).

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| #255 packages | Open at `ebbc172`, description current. Booth: NEEDS HUMAN REVIEW, 6 confirmed, 2 expected UNVERIFIABLE (the whole corpus; the routine), no discrepancy | Mark: his routine edit, then his say-so to merge (it edits the Booth workflow) |
| QB override routine prompt | `sys.path` imports; names the old lock time | Mark edits it at claude.ai/code/routines |
| claude-code-action pin | On v1.0.236 | A hand bump when a release matters |
| Season Accuracy's forecast score | Merged (#160), not on the page yet | 50 graded games: after week 4 at the earliest |
| TV exceptions for holiday and Saturday games | Weeks 12, 15, 16 | Sourced entries in `data/tv/exceptions.json` before those weeks |
| Audit Response Log | Updated 2026-10-01 | Fable, for the next audit |
| Drift issue | Never fired on a real event | A real event |

## Queued, in order

1. The after-lock items above.
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
- **The drift check is on accuracy** (baseline now read from `data/calibration.json`, #254), which cannot carry a result at this sample size. Stage 33 item 24 is the fix, as a registration.
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
- **Booth's runner shows CLAUDE.md modified on every PR that edits it**: claude-code-action restores it from `main` before Booth starts, by design (traps). Stashing it is right.
- **The reproducibility audit flips between GitHub runners** (same commit, same packages: one REPRODUCED, one Model A log loss 0.64995 against 0.64981). Machine-dependent; traps. Local Windows reproduces exactly.
- **The Booth report check cannot tell WHY a run posted nothing.** Since #101 a failed audit at least opens an issue.
