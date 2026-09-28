# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-28, overnight session (Stages 17 and 18 complete; Stage 19 #157 to #159)

---

## Right now

**Suite:** 3495 passing, none skipped — `python -m pytest -q` on `main` at
`e95d312` (#159 merged), HEAD level with origin.

**Next action: read Mark's answers** to the three Stage 19 questions and the
Stage 6 draft registration (table below), then build what they unblock.

**Done this session:** #148 to #159 — Stage 17 complete, Stage 18 complete,
and Stage 19's default team, games-list headings and accuracy-trend labels.
Details and traps: `memory/2026-09-28.md`.

**Unexplained:** #148 was merged on markys at 02:59 UTC by something other
than this session, while it was paused. The result matches the audited
commit exactly. Asked Mark whether it was him; no answer yet.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Stage 19 log-loss row | Written and tested, not opened | Mark: plain wording, or an exception to the plain-language guard for "log loss" |
| Stage 19 Power Ratings movers + rank change | Not started | Mark: does the arrow follow rank or rating? |
| Stage 19 Team Deep-Dive offence/defence | Not started | Mark: phone layout, and a "lower is better" note for defence |
| Stage 6 referee crews and personnel | Registration drafted (R1 screen, R2, A2; personnel DEFERRED), sent to Mark, not committed: registry entries are append-only | Mark's approval, then commit the entries before any data is loaded |
| First run of the QB routine | Due Mon 2026-09-28 22:00 UTC | Check it opened a PR, or said in one line that none was needed |
| First weekly summary | Due Tue 2026-09-29 11:00 UTC | Open the run's page and check the summary reads right |
| Thursday lock run | Due Thu 2026-10-01 16:00 UTC | Check it started, locked before kickoff, and its push survived; week 4 is the first card with quarterback names and channels |
| TV exceptions for holiday and Saturday games | Weeks 12, 15, 16 | Sourced entries in `data/tv/exceptions.json` before those weeks |
| Model Lab mappings | My calls, in #141 | Mark may overrule any (listed in `experiments/legacy/README.md`) |
| Booth alert, drift issue, failure alerts | Two have fired, read right and are closed (#144, #145) | The drift issue still needs a real event |
| #147's catch-up step under a race | Ran on Monday's refresh (11:56 UTC, `1aa74e8`), but main had not moved, so it caught up on nothing | A refresh or weekly run during which main moves |

## Queued, in order

1. **Stage 19** remaining, once Mark answers: the log-loss row, Power Ratings movers and rank change, Team Deep-Dive offence/defence.
2. **The rest of Stage 6** (referee crews, personnel): commit the registration once Mark approves the draft, then run R1.
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
