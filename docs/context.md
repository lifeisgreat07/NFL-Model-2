# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-28, morning session (Stage 19 complete; Stage 6 registration open as #163)

---

## Right now

**Suite:** 3623 passing, none skipped — `python -m pytest -q` on `main` at
`de218ad` (#162 merged), HEAD level with origin.

**Next action: merge #163 on Booth's SAFE TO MERGE, then run R1** (the
referee screen), as its own PR. That PR must also teach `recompute()` in
`tests/test_stage6_registry.py` R1's correlation rule: today it derives a
screen's label from N1's error-difference fields.

**Done this morning:** #160 "How sure, and how right" on Season Accuracy,
#161 Power Ratings' rank change and biggest moves, #162 offense and defense
on Team Deep-Dive — Stage 19 complete. #163 registers R1, R2, A2 and P1.
Details: `memory/2026-09-28.md`.

**#148 is explained:** the overnight session merged it itself. Desktop
Commander's own call history on markys (in the user profile, not the repo)
shows it polling Booth at 02:53 and 02:58 UTC, reading the report, and
running `merge_pr.ps1 -Pr 148` at 02:59:34. The session then lost that
stretch across its pause and recorded the merge as a stranger's. Mark
confirmed it was not him.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| #163 Stage 6 referee registration | Open; suite 3623, 9 scoped mutations CAUGHT | Booth, then merge |
| R1, the referee screen | Registered in #163, not run | #163 merged; the run is its own PR |
| Season Accuracy's forecast score | Merged (#160) but not on the page yet | 50 graded games: after week 4 at the earliest |
| README screenshots | Mark asked, 2026-09-28 | Stage 19 is done; Stage 6's R1 next, then replace them |
| First run of the QB routine | Due Mon 2026-09-28 22:00 UTC | Check it opened a PR, or said in one line that none was needed |
| First weekly summary | Due Tue 2026-09-29 11:00 UTC | Open the run's page and check the summary reads right |
| Thursday lock run | Due Thu 2026-10-01 16:00 UTC | Check it started, locked before kickoff, and its push survived; week 4 is the first card with quarterback names and channels |
| TV exceptions for holiday and Saturday games | Weeks 12, 15, 16 | Sourced entries in `data/tv/exceptions.json` before those weeks |
| Model Lab mappings | My calls, in #141 | Mark may overrule any (listed in `experiments/legacy/README.md`) |
| Booth alert, drift issue, failure alerts | Two have fired, read right and are closed (#144, #145) | The drift issue still needs a real event |
| #147's catch-up step under a race | Ran on Monday's refresh (11:56 UTC, `1aa74e8`), but main had not moved, so it caught up on nothing | A refresh or weekly run during which main moves |

## Queued, in order

1. **Stage 6, referees**: merge #163, then run R1 as its own PR. R2 and A2 only if R1 passes; the stated expectation is that it fails.
2. **README screenshots** (Mark, 2026-09-28): replace them once 1 has landed. Binary files cross the bridge base64-encoded with an MD5 check.
3. **Stages 20 to 22**: 20 needs five real testers; 21 waits for week 5; 22 comes from 20.

Merge one branch at a time: every branch that adds a mutation case file
moves the README count, so two open at once always conflict. Don't merge
while a scheduled run is in flight if it can be avoided; the catch-up step
narrows the race, it does not close it.

## Known and deliberately not fixed

- **The drift check is on accuracy**, which cannot carry a result at this sample size. Its issue says so and points at log loss and Brier. Rewriting the check itself was not in Stage 4.
- **A failed Thursday run leaves Thursday night's game unpicked** unless someone dispatches the workflow by hand that day. Since #105 the failure opens an issue, so it at least reaches Mark in time.
- **A Booth header can disagree with its verdict block**, logged by `cross_check()` (seen again on #153). Should it fail? It has cost nothing yet.
- **The generator writes `index.html` without `encoding=`**, so a non-cp1252 character in generated text crashes the Windows build. Worked around with `&minus;` in #154.
- **`tests/browser/check_page.py` flaked in Booth's environment** on 2 of 7 runs (#156 audit), with findings unrelated to the change and not reproducible.
- **`check_scoped_test_counts` skips a count for a module that does not exist** — a DELETED module passes silently.
- **Only the wrap-up gate and session-start recompute CLAUDE.md's `Suite:` line.** Both manual, accepted.
- **Preflight checks commits and suite counts, not every number in prose.** Read the body against `git log` before opening.
- **Nothing on the page reaches the listbox edge flip**; kept and checked over synthetic geometries.
- **A human approval leaves no artifact in the repo.** `memory/` is what records it.
- **The co-occurrence trace, and the no-JS findings, are re-derivable only where a browser exists.** Browser checks (#120) now has one, but runs only `tests/browser/check_page.py`; these two are still guarded as premises in the suite, not re-derived.
- **Browser checks does not click.** States reached only by interaction (a switched-off series, an opened team dive, shared-picks mode) are covered by static tests, not by the browser run. #122 found the off-series contrast failure by reading, not by the checker.
- **60 of 496 team pairs sit under the CIEDE2000 floor on the Week Board's split bar, accepted 2026-09-21.** `src/verify_matchup_cvd.py` still reports it.
- **The Booth report check cannot tell WHY a run posted nothing.** Since #101 a failed audit at least opens an issue.
