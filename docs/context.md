# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-24, end of session (Stage 4 complete, #100 to #107 merged)

---

## Right now

**Suite:** 2275 passing, none skipped — `python -m pytest -q` on `main` at
`aef3a2b`, HEAD level with origin.

**Next action: check that the first nightly canary passed** (06:00 UTC
2026-09-25, "Nightly canary" in the Actions tab). If it failed, the issue
"Nightly canary failing" says why. Then Stage 6, when Mark picks it up.

**Done today:** Stage 4, all nine items, one PR at a time, each merged after
Booth said SAFE TO MERGE with no discrepancies: #100 data-quality checks,
#101 Booth alerts, #102 nightly canary and schema snapshot, #103 build-output
smoke check, #104 drift to an issue, #105 weekly summary and failure alert,
#106 reproducibility audit and leak-free tests, #107 play-by-play cache for
the canary. Stage 7 finished earlier (#96 to #99).

**The weekly Claude routine** is "Weekly QB override research": QB news
only, sourced override file, via a PR, Mon and Wed 22:00 UTC. It never
grades or rebuilds. On a normal week, merge its PR before Thursday's 16:00
UTC lock. Its first run is Mon 2026-09-28.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| First nightly canary | Due 06:00 UTC 2026-09-25 | Check it passed, and that its cache step saved `.pbp-cache` |
| First weekly summary | Due Tue 2026-09-29 11:00 UTC | Open the run's page and check the summary reads right |
| First run of the new QB routine | Due Mon 2026-09-28 | Check it opened a PR, or said in one line that none was needed |
| Booth alert, drift issue, failure alerts | Live, never fired | Each needs a real event; when one opens an issue, check it reads right |
| Which claim Booth's fixture claim 1 was | Inferred as the "Two commits." line | Reading that run's report artifact, if it is ever worth it |
| Leak table splits two ways on Linux | Recorded in the QB case study | Nothing, unless it is ever worth finding the cause |

## Queued, in order

1. **Stage 6**, each item with a hypothesis stated before any data is pulled.

Merge one branch at a time: every branch that adds a mutation case file
moves the README count, so two open at once always conflict.

## Known and deliberately not fixed

- **The drift check is on accuracy**, which cannot carry a result at this sample size. Its issue says so and points at log loss and Brier. Rewriting the check itself was not in Stage 4.
- **A failed Thursday run leaves Thursday night's game unpicked** unless someone dispatches the workflow by hand that day. Since #105 the failure opens an issue, so it at least reaches Mark in time.
- **A Booth header can disagree with its verdict block**, logged by `cross_check()`. Should it fail? It has cost nothing yet.
- **`check_scoped_test_counts` skips a count for a module that does not exist** — a DELETED module passes silently.
- **Only the wrap-up gate and session-start recompute CLAUDE.md's `Suite:` line.** Both manual, accepted.
- **Preflight checks commits and suite counts, not every number in prose.** Read the body against `git log` before opening.
- **Nothing on the page reaches the listbox edge flip**; kept and checked over synthetic geometries.
- **A human approval leaves no artifact in the repo.** `memory/` is what records it.
- **The co-occurrence trace, and the no-JS findings, are re-derivable only where a browser exists.** No CI job here has one; the premise is guarded in the suite and the finding is not.
- **60 of 496 team pairs sit under the CIEDE2000 floor on the Week Board's split bar, accepted 2026-09-21.** `src/verify_matchup_cvd.py` still reports it.
- **The Booth report check cannot tell WHY a run posted nothing.** Since #101 a failed audit at least opens an issue.
