# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-28, overnight session (Stage 17: #148 and #149 merged)

---

## Right now

**Suite:** 3289 passing, none skipped — `python -m pytest -q` on `main` at
`657871a` (#149 merged) plus the 2026-09-28 docs, HEAD level with origin.

**Next action: check the Monday 05:37 UTC weekend refresh** (table below),
then Stage 17's next item, the `[` / `]` week keys.

**Done this session:** Stage 17's channel pill, quarterbacks and team-news
line (#148) and the "Model A's reasoning" label (#149), each merged on a clean
Booth audit. Details and traps: `memory/2026-09-28.md`.

**Unexplained:** #148 was merged on markys at 02:59 UTC by something other
than this session, four minutes after Booth's SAFE TO MERGE, while the session
was paused. The result matches the audited commit exactly. Asked Mark
whether it was him; no answer yet.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Weekend refresh with the catch-up step | Due Mon 2026-09-28 05:37 UTC (has started up to 2h12m late) | Check it committed week 3's status, TV and news, and the page rebuilt; then close #145 and #144 |
| First run of the QB routine | Due Mon 2026-09-28 22:00 UTC | Check it opened a PR, or said in one line that none was needed |
| First weekly summary | Due Tue 2026-09-29 11:00 UTC | Open the run's page and check the summary reads right (it now also reads TV and team news) |
| Thursday lock run | Due Thu 2026-10-01 16:00 UTC | Check it started, locked before kickoff, and its push survived; week 4 is the first card with quarterback names |
| `.card-status` colour | `color:var(--text-1)`, a token never defined (#134), so the line inherits | Its own small PR |
| TV exceptions for holiday and Saturday games | Weeks 12, 15, 16 | Sourced entries in `data/tv/exceptions.json` before those weeks |
| Model Lab mappings | My calls, in #141 | Mark may overrule any (listed in `experiments/legacy/README.md`) |
| Booth alert, drift issue, failure alerts | Two have fired and read right (#144, #145) | The drift issue still needs a real event |

## Queued, in order

1. **Stage 17** remaining, one PR each: `[` / `]` week keys; no HIGH/LOW words; drop the unused `.model-row` / `.tele-team` CSS.
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
