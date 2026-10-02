# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-10-02, early morning ET (#255, #256, #257 merged; Stage 33 registered)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked
figure. `src/` is packaged: run modules with `python -m src.<package>.<module>`.

**Next action: Stage 33 item 21's groundwork**, one PR: `MODEL_SPECS` and
`walk_forward(spec)` shared by the live pipeline and the backtest, with
`C=1.0, penalty='l2'` written out, proven by a byte-identical page and the
reproducibility audit run on the local Windows machine (GitHub runners flip,
see traps). The registry (`experiments/stage33/registry.json`, `8ddbcec`)
requires it before any of R1 to R4 runs. Then, in order:
1. **A Stage 33 registry test** like `tests/test_stage5_registry.py`
   (registered before answered; labels recomputed; budget 3), before R1 has
   a result.
2. **R1, R2, R3** (98.33% intervals; R3 non-inferiority +0.002), each a
   Model Lab row; then **R4**, the drift check on log loss against 0.6518.
3. **Booth prompt line**: the CLAUDE.md restore on PRs is expected (edits
   the Booth workflow, so Mark reviews). **Audit provenance**: record the
   runner's CPU.
4. **Check after the weekend**: Friday's weekend refresh appended week 4
   lines (#257); Monday 22:00 UTC the QB routine runs on the new imports;
   Tuesday's Weekly update under `python -m`.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Stage 33 R1 to R4 | Registered (`8ddbcec`), not run | Item 21's groundwork PR, then a registry test |
| QB override routine prompt | Edited by Mark 2026-10-02 to `from src.pipeline...`; read back | Its first run, Monday 22:00 UTC |
| claude-code-action pin | On v1.0.236 | A hand bump when a release matters |
| Season Accuracy's forecast score | Merged (#160), not on the page yet | 50 graded games: after week 4 at the earliest |
| TV exceptions for holiday and Saturday games | Weeks 12, 15, 16 | Sourced entries in `data/tv/exceptions.json` before those weeks |
| Audit Response Log | Updated 2026-10-02 | Fable, for the next audit |
| Drift issue | Never fired on a real event | A real event |

## Queued, in order

1. The Stage 33 items above.
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
