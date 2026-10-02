# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-10-02, afternoon ET (#258 to #262 merged; Stage 33 R1 to R4 answered)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked
figure. `src/` is packaged: run modules with `python -m src.<package>.<module>`.

**Next action: Stage 33 item 25**, one PR. Tests tie the `model_version` in
the calibration, bootstrap and reproducibility files to `MODEL_VERSION`, with
an explicit "backtest unchanged since 2.4" allowance, and tie the README and
Methodology backtest tables to `data/calibration.json`.

**Before it, check the unattended runs** (read-only):
1. Monday 22:00 UTC: the QB routine's first run on the `src.pipeline` imports.
2. Tuesday 11:00 UTC: the first Weekly update on `MODEL_SPECS` and on the
   log-loss drift check (#261). Its summary should read `DRIFT CHECK: OK`,
   and its drift report should have a "Model A, log loss" section.
3. Whether the Booth prompt PR (the restored CLAUDE.md is expected) has
   Mark's review. Booth skips a PR that edits its own workflow.

**Stage 33 has answered all four questions.** R1, R2 and R3 are INCONCLUSIVE
and the budget of three is spent; R4 is live. A fifth model question needs a
new registration.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Booth prompt line: the restored CLAUDE.md is expected | PR open, branch `s33-booth-restore` | Mark's review |
| QB override routine | Prompt edited by Mark 2026-10-02 to `src.pipeline` | Its first run, Monday 22:00 UTC |
| Log-loss drift check (R4) | Merged #261; first real run OK on 48 games | Tuesday's Weekly update |
| claude-code-action pin | On v1.0.236 | A hand bump when a release matters |
| Season Accuracy's forecast score | Merged (#160), not on the page yet | 50 graded games: after week 4 at the earliest |
| TV exceptions for holiday and Saturday games | Weeks 12, 15, 16 | Sourced entries in `data/tv/exceptions.json` before those weeks |
| Audit Response Log | Updated 2026-10-02 afternoon | Fable, for the next audit |

## Queued, in order

1. **Stage 33 items 25, 20 and 26** (26 last, by the audit's own order).
2. **Stages 20 to 22**: 20 needs five real testers; 21 waits for week 5; 22 comes from 20.
3. **Stage 28** and the closing-line backtest: after the regular season.

Merge one branch at a time: every branch that adds a mutation case file
moves the README count, so two open at once always conflict. Run the suite
and the mutation scope at the exact head being opened, after the last
rebase, and describe the scope as run whole with both counts, listing the
case files (Booth cannot reproduce a count whose selection it cannot see).
Keep counts out of commit messages: scout-preflight fails on one even when
the body discloses it.

## Known and deliberately not fixed

- **Scheduled runs start hours late** (3.5 to 6.5h since 2026-09-24). Absorbed by the 11:00 Thursday lock and 8h slack, not fixed; GitHub's queue is not ours.
- **Preview cards have no TV channel or team-news line**: those steps read locked weeks only (#204).
- **The link preview and share image say "The Pick'em Model"**: Mark's decision, recorded in `test_product_name`; the re-audit's redraw was declined (#242).
- **The drift check re-tests a growing sample every week**, so it will sometimes flag by chance. The issue says so. R4 registered the rule as written; changing it needs a new registration.
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
- **Booth's runner shows CLAUDE.md modified on every PR that edits it**: claude-code-action restores it from `main` before Booth starts, by design (traps). Stashing it is right; the open Booth prompt PR tells Booth so.
- **The reproducibility audit flips between GitHub runners** (same commit, same packages). Machine-dependent; traps. Local Windows reproduces exactly. Since #262 each record names its CPU, so the next flip can be tied to hardware.
- **The Booth report check cannot tell WHY a run posted nothing.** Since #101 a failed audit at least opens an issue.
