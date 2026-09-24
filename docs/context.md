# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-24 (#96 and #97 merged, #98 open, Stage 7.6 done)

---

## Right now

**Suite:** 1877 passing, none skipped — `python -m pytest -q` on `main` at
`f7b4fff`, HEAD level with origin.

**#98 is open: the rest of Stage 7.** Stage 2 corrections case study,
Booth regression suite write-up, the lessons-learned page,
the architecture diagram, and the README rewrite with images. Waiting on
Booth, then Mark. **Merging #98 finishes Stage 7.**

**Next action once #98 merges: start Stage 4**, beginning with the two
loose ends below that are Stage 4 in nature (the regression workflow's
recorded head, and the stale weekly routine prompt).

**Stage 7.6 is done.** The repo's About panel carries Mark's description
and seven topics, set 2026-09-24 in a signed-in browser.

**#95 held.** Every Booth run on #96, #97 and #98 so far posted a report
(one on #96 was cancelled by design when a newer run started).

**The Booth regression suite has run once** (`f7b4fff`, 2026-09-24): Booth
caught the planted defect. On `main` the suite now has no standing skip.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| The regression head fix and fixture body | Open PR | Booth, then Mark |
| Confirming #73 on a phone | Not done | Only a device proves the zoom is gone |
| The weekly routine's prompt is stale | New prompt written (QB news only, via PR, Mon and Wed 22:00 UTC) | Mark pastes it in: the routine was created outside an agent session, so an agent cannot edit it |
| Leak table splits two ways on Linux | Recorded in the QB case study | Nothing, unless it is ever worth finding the cause |

## Queued, in order

1. **Stage 4**: automation and monitoring.
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
