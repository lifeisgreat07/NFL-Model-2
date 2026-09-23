# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-23 (Stage 10: #89 and #90 merged, #91 open)

---

## Right now

**Suite:** 1705 passing, 1 skipped — `python -m pytest -q` on `main` at
`61ebdfd`, HEAD level with origin. Each open branch quotes its own figure at
its own SHA.

**Stage 10 is landing one PR at a time (Mark, 2026-09-23).** Merged: #89
mobile pass, #90 components. Open: **#91 table system**, waiting on Booth
and then Mark. Built and waiting their turn, each on a local branch stacked
on the one before, so each is rebased onto `main` when its turn comes:

1. `stage10-states` (worktree `E:\nfl-cache\wt-states`): page states.
2. `stage10-moments` (`E:\nfl-cache\wt-moments`): the Season Accuracy
   scoreboard, Mark's pick of three rendered candidates.
3. `stage10-scale` (`E:\nfl-cache\wt-scale`): type and spacing onto the
   Stage 8 scales. Mark approved the before/after renders.

Then Stage 10 closes with the audit score in CLAUDE.md (re-run on the
stacked build: about 28/40, from 15) and the correction below.

**CLAUDE.md is wrong in one place until the scale PR lands:** its Stage 8
section says the token block satisfies the audit's foundations list. The
tokens existed but the page barely used them. The scale PR fixes both the
page and that sentence.

**The weekly job locks picks on Thursday** (#88). QB overrides are due by
Thursday 16:00 UTC, in `data/qb_overrides/`. Live model is v2.5.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| #91, table system | Open | Booth, then Mark to merge |
| states, moments, scale | Built locally | #91 merging, one at a time |
| The repo's About panel | Empty | Mark. Repo settings; wording in CLAUDE.md |
| Confirming #73 on a phone | Not done | Only a device proves the zoom is gone |

## Queued, in order

1. **Stage 10**, the three PRs above.
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
