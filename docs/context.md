# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-23 (#88 merged, Stage 10 started)

---

## Right now

**Suite:** 1646 passing, 1 skipped — `python -m pytest -q` on `main` at
`b01342b`, HEAD level with origin. Nothing else may read the tree while the
mutation corpus runs — see CLAUDE.md's traps.

**#88 is merged: picks lock on Thursday.** The weekly workflow runs Tuesday
11:00 UTC (grading, ratings, line archive) and Thursday 16:00 UTC.
`decide_lock` in `src/weekly_update.py` locks the week when its first game
comes before the next scheduled run plus four hours, so an ordinary week
locks Thursday, and weeks 1 and 12 of 2026 lock Tuesday. Week 4 is the first
to lock on Thursday, 1 Oct.

**QB overrides are due by Thursday 16:00 UTC** (noon ET until 1 Nov, 11 AM
after), in `data/qb_overrides/`.

**Live model is v2.5.** Each pick is rated with the expected starter: a
sourced override first, then the schedule's listed starter, then last
game's QB.

**Stage 10 is under way, one PR at a time (Mark, 2026-09-23).** Each PR is
cut from `main` only after the previous one merges. The order: mobile pass,
components (button, page header, nav labels, onboarding banner), table
system, page states, the standout moments, then the design-audit re-run.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Stage 10 | Mobile pass first | Nothing: in progress |
| The repo's About panel | Empty | Mark. Repo settings; wording in CLAUDE.md |
| Confirming #73 on a phone | Not done | Only a device proves the zoom is gone |

## Queued, in order

1. **Stage 10**, in the order above.
2. **Stage 7**: text-only items are unblocked; visual ones wait for 10.
3. **Stage 4**.
4. **Stage 6's broadcast channel**.

Merge one branch at a time: every branch that adds a mutation case file
moves the README count, so two open at once always conflict.

## Known and deliberately not fixed

- **A failed Thursday run leaves Thursday night's game unpicked** unless someone dispatches the workflow by hand that day. The lock now comes about 8 hours before that kickoff, not about 61. A run after kickoff predicts only the games still to come, and a week entirely kicked off with nothing locked fails the run.
- **A Booth header can disagree with its verdict block**, logged by `cross_check()`, ten of the last eleven reports before #88. Should it fail? It has cost nothing yet only because the discrepancy count was zero either way.
- **`check_scoped_test_counts` skips a count for a module that does not exist** — a DELETED module passes silently.
- **Only the wrap-up gate and session-start recompute CLAUDE.md's `Suite:` line.** Both manual, accepted.
- **Preflight checks commits and suite counts, not every number in prose.** #86 merged with "a merge" for two, and #87's draft said "nine" above a list of seven. Read the body against `git log` before opening. #88's Booth report did it too: "all 8 named test functions" above a list of seven.
- **Nothing on the page reaches the listbox edge flip**; kept and checked over synthetic geometries.
- **A human approval leaves no artifact in the repo.** Booth marked the #80 acceptance UNVERIFIABLE for that reason and was right to; `memory/2026-09-21.md` is what it points at.
- **The co-occurrence trace, and the no-JS findings, are re-derivable only where a browser exists.** No CI job here has one. In both the premise is guarded in the suite and the finding itself is not; accepted.
- **60 of 496 team pairs sit under the CIEDE2000 floor on the Week Board's split bar, and that is accepted.** Decided 2026-09-21 after looking at the alternatives. `src/verify_matchup_cvd.py` still reports it; nothing guards the figure from growing, which is the one loose end if the palette is ever edited.
- **The Booth report check cannot tell WHY a run posted nothing.** It only knows that nothing was posted. The cause is in the action's log, which needs a signed-in browser.
