# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-27, evening session (Stage 16 complete; Stages 17 and 18 under way; #138 to #147 merged)

---

## Right now

**Suite:** 3220 passing, none skipped — `python -m pytest -q` on `main` at
`c4532da` (#146 merged) plus the evening docs, HEAD level with origin.

**Next action: Stage 17's next item**, the TV pill, announced QB names and
the one-line team news on the card (#146, the card body, merged on a clean
fourth audit). Check the Monday 05:37 UTC weekend refresh first (table below).

**Done today:** Stage 15 (#132 to #137), Stage 16 (#138 to #140), Stage 18's
first three items (#141 to #143), and #147, a fix found by the first live
weekend refresh: its push lost a race with a merge, so both committing
workflows now rebase onto main just before committing. Mark chose the card
design ("B refined") from rendered side-by-sides. Details, decisions and traps:
`memory/2026-09-27.md` and CLAUDE.md Stages 16 to 18.

**Stage 4's live runs:** the Nightly canary passed 2026-09-25, -26 and -27,
each starting 4.5 to 5 hours after its 06:00 UTC cron. The first weekend
refresh started 2h12m late and failed on the race above (issue #145, open).
Issue #144 is the Booth alert from #143's first audit, since superseded by a
clean re-audit; both can be closed by hand.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Weekend refresh with the catch-up step | Next run Mon 2026-09-28 05:37 UTC | Check it committed week 3's status, TV and news, and the page rebuilt; then close #145 |
| First run of the QB routine | Due Mon 2026-09-28 22:00 UTC | Check it opened a PR, or said in one line that none was needed |
| First weekly summary | Due Tue 2026-09-29 11:00 UTC | Open the run's page and check the summary reads right (it now also reads TV and team news) |
| Thursday lock run | Due Thu 2026-10-01 16:00 UTC | Check it started, locked before kickoff, and its push survived (the catch-up step's first test under load) |
| TV exceptions for holiday and Saturday games | Weeks 12, 15, 16 | Sourced entries in `data/tv/exceptions.json` before those weeks |
| Model Lab mappings | My calls, in #141 | Mark may overrule any (listed in `experiments/legacy/README.md`) |
| Booth alert, drift issue, failure alerts | Two have now fired and read right (#144, #145) | The drift issue still needs a real event |

## Queued, in order

1. **Stage 17** remaining items, one PR each (CLAUDE.md Stage 17).
2. **Stage 18** remaining: result-first layout with an interval glyph, cards on a phone, the reliability diagram below with "How to read this".
3. **Stages 19 to 22**, and the rest of Stage 6 (referee crews, personnel) after Stage 18.

Merge one branch at a time: every branch that adds a mutation case file
moves the README count, so two open at once always conflict. Don't merge
while a scheduled run is in flight if it can be avoided; the catch-up step
narrows the race, it does not close it.

## Known and deliberately not fixed

- **The drift check is on accuracy**, which cannot carry a result at this sample size. Its issue says so and points at log loss and Brier. Rewriting the check itself was not in Stage 4.
- **A failed Thursday run leaves Thursday night's game unpicked** unless someone dispatches the workflow by hand that day. Since #105 the failure opens an issue, so it at least reaches Mark in time.
- **A Booth header can disagree with its verdict block**, logged by `cross_check()`. Should it fail? It has cost nothing yet.
- **`check_scoped_test_counts` skips a count for a module that does not exist** — a DELETED module passes silently.
- **Only the wrap-up gate and session-start recompute CLAUDE.md's `Suite:` line.** Both manual, accepted.
- **Preflight checks commits and suite counts, not every number in prose.** Read the body against `git log` before opening.
- **Nothing on the page reaches the listbox edge flip**; kept and checked over synthetic geometries.
- **A human approval leaves no artifact in the repo.** `memory/` is what records it.
- **The co-occurrence trace, and the no-JS findings, are re-derivable only where a browser exists.** Browser checks (#120) now has one, but runs only `tests/browser/check_page.py`; these two are still guarded as premises in the suite, not re-derived.
- **Browser checks does not click.** States reached only by interaction (a switched-off series, an opened team dive, shared-picks mode) are covered by static tests, not by the browser run. #122 found the off-series contrast failure by reading, not by the checker.
- **60 of 496 team pairs sit under the CIEDE2000 floor on the Week Board's split bar, accepted 2026-09-21.** `src/verify_matchup_cvd.py` still reports it.
- **The Booth report check cannot tell WHY a run posted nothing.** Since #101 a failed audit at least opens an issue.
