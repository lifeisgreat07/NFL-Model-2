# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-24 (#98 merged, #99 open, Stage 1 retired, Stage 4 parked)

---

## Right now

**Suite:** 1962 passing, none skipped — `python -m pytest -q` on
`regression-head-and-stage1` (#99) at `335bf0a`, HEAD level with origin.

**Next action: get #99 merged.** It retires Stage 1 and fixes the two
problems the first Booth regression run found (the baseline's head, and the
fixture's "Two commits." description). Waiting on Booth, then Mark.

**Stage 7 is complete** (#96, #97, #98). **Stage 1 is retired** (in #99):
its live item, line accumulation and the closing-line backtest, moved to
Stage 6 with the end of the 2026 regular season as the trigger.

**Stage 4 is parked** by Mark, mid-build. The draft is the local, unpushed
branch `stage4-draft` on `markys`; CLAUDE.md's Stage 4 section says what is
in it and the decisions already made.

**The weekly Claude routine is replaced.** Mark saved it on 2026-09-24 as
"Weekly QB override research": QB news only, sourced override file, via a
PR, Mon and Wed 22:00 UTC. It never grades or rebuilds; the Weekly update
workflow owns that. On a normal week, merge its PR before Thursday's
16:00 UTC lock.

**#95 held.** Every Booth run on #96 to #98 posted a report.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| #99, Stage 1 retirement and the regression fixes | Open | Booth, then Mark |
| Confirming #73 on a phone | Not done | Only a device proves the zoom is gone |
| Which claim Booth's fixture claim 1 was | Inferred as the "Two commits." line | Reading that run's report artifact, if it is ever worth it |
| Leak table splits two ways on Linux | Recorded in the QB case study | Nothing, unless it is ever worth finding the cause |

## Queued, in order

1. **Stage 4**, resumed from `stage4-draft` when Mark says so.
2. **Stage 6**, each item with a hypothesis stated before any data is pulled.

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
