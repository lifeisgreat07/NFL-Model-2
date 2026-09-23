# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-23 (#88 open, Booth SAFE TO MERGE)

---

## Right now

**Suite:** 1604 passing, 1 skipped — `python -m pytest -q` on `main`, HEAD
level with origin. #88's branch runs 1646 passed, 1 skipped at `f432d19`,
and its full corpus run was 268 cases, all CAUGHT; Booth re-ran both and
matched. Nothing else may read the tree while the corpus runs — see
CLAUDE.md's traps.

**PR #88 is open: picks lock on Thursday, not Tuesday.** Mark decided this on
2026-09-22. The weekly workflow runs Tuesday 11:00 UTC (grading, ratings,
line archive) and Thursday 16:00 UTC. `decide_lock` in `src/weekly_update.py`
locks the week when its first game comes before the next scheduled run plus
four hours, so an ordinary week locks Thursday, and weeks 1 and 12 of 2026
(both open on a Wednesday) lock Tuesday. A game already kicked off never
gets a pick. Booth: 9 of 9 claims confirmed, SAFE TO MERGE. It independently
re-ran the lock rule against the real 2026 schedule.

**Next action: Mark merges #88 before Tuesday 29 Sep, 11:00 UTC.** Merged
before then, week 4 locks on Thursday 1 Oct. Merged later, week 4 still
locks on Tuesday under the old workflow. The merge moves `main` to the
branch's suite figure, so the CLAUDE.md `Suite:` line needs updating in the
same session.

**Once #88 is in, QB overrides are due by Thursday 16:00 UTC** (noon ET until
1 Nov, 11 AM after), in `data/qb_overrides/`.

**Live model is v2.5.** Each pick is rated with the expected starter: a
sourced override first, then the schedule's listed starter, then last
game's QB.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| #88, Thursday lock | Audited, SAFE TO MERGE | Mark to merge, before Tue 29 Sep 11:00 UTC |
| The repo's About panel | Empty | Mark. Repo settings; wording in CLAUDE.md |
| Confirming #73 on a phone | Not done | Only a device proves the zoom is gone |

## Queued, in order

1. **Stage 10**, after #88 merges (one branch at a time): the mobile pass
   (`.game-card` overflows below 352px, a 340px card against a 296px content
   box at 320) and the button component, moved here from Stage 9. The focus
   sweep is already done.
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
