
# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-22 (#84 to #87 merged; nothing open)

---

## Right now

**Suite:** 1604 passing, 1 skipped — `python -m pytest -q` on `main` at
`2ab17ee`, HEAD level with origin. The latest full corpus run was #87's head
before it merged: 260 cases, all CAUGHT, at `bf21c29`; Booth re-ran it and
matched. Nothing else may read the tree
while the corpus runs — see CLAUDE.md's traps.

**No PR is open.** Stage 9 merged as #87: red and green mean only a scored
pick right or wrong, the Net Rating bar is a neutral fill, and
`--accent-strong` is retired. `tests/test_graded_colour_scope.py` holds it.

**Live model is v2.5.** Each pick is rated with the expected starter: a
sourced override in `data/qb_overrides/` first, then the schedule's listed
starter, then last game's QB. Chosen on methodology grounds; Stage 5's H1 was
INCONCLUSIVE, so the 2026 forward test is what scores it.

**Next action: Mark decides when the weekly run locks picks.** It locks on
Tuesday at 11:00 UTC, before most injury news, so an override only helps if
it lands before then.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Pick lock time | Decision | Mark: keep Tuesday 11:00 UTC, or lock later in the week |
| The repo's About panel | Empty | Mark. Repo settings; wording in CLAUDE.md |
| Confirming #73 on a phone | Not done | Only a device proves the zoom is gone |

## Queued, in order

1. **Stage 10**: the mobile pass (`.game-card` overflows below 352px, a
   340px card against a 296px content box at 320) and the button component,
   moved here from Stage 9. The focus sweep is already done.
2. **Stage 7**: text-only items are unblocked; visual ones wait for 10.
3. **Stage 4**.
4. **Stage 6's broadcast channel**.

Merge one branch at a time: every branch that adds a mutation case file
moves the README count, so two open at once always conflict.

## Known and deliberately not fixed

- **A Booth header can disagree with its verdict block**, logged by `cross_check()`, ten of the last eleven reports. Should it fail? It has cost nothing yet only because the discrepancy count was zero either way.
- **`check_scoped_test_counts` skips a count for a module that does not exist** — a DELETED module passes silently.
- **Only the wrap-up gate and session-start recompute CLAUDE.md's `Suite:` line.** Both manual, accepted.
- **Preflight checks commits and suite counts, not every number in prose.** #86 merged with "a merge" for two, and #87's draft said "nine" above a list of seven. Read the body against `git log` before opening.
- **Nothing on the page reaches the listbox edge flip**; kept and checked over synthetic geometries.
- **A human approval leaves no artifact in the repo.** Booth marked the #80 acceptance UNVERIFIABLE for that reason and was right to; `memory/2026-09-21.md` is what it points at.
- **The co-occurrence trace, and the no-JS findings, are re-derivable only where a browser exists.** No CI job here has one. In both the premise is guarded in the suite and the finding itself is not; accepted.
- **60 of 496 team pairs sit under the CIEDE2000 floor on the Week Board's split bar, and that is accepted.** Decided 2026-09-21 after looking at the alternatives. `src/verify_matchup_cvd.py` still reports it; nothing guards the figure from growing, which is the one loose end if the palette is ever edited.
- **The Booth report check cannot tell WHY a run posted nothing.** It only knows that nothing was posted. The cause is in the action's log, which needs a signed-in browser.
