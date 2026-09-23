# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-22 (#82 and #83 merged; Stage 5 answered in #84)

---

## Right now

**Suite:** 1383 passing, 1 skipped — `python -m pytest -q` on `main` at
`4e0f1fd`, HEAD level with origin. Corpus on `main`: 224 cases, all CAUGHT,
from `python tests/mutation/runner.py` on the #83 branch before it merged.
Nothing else may read the tree while that runs — see CLAUDE.md's traps.

**Open: PR #84 (Stage 5).** Its Booth run went RED because Booth posted
nothing. That is #83's new step catching a real silent audit on its first live
run: Booth ran 5m08s, the action exited 0, and there was no comment. A re-run
is needed. The logs need a signed-in browser, so the cause is still unknown.

**Stage 5 accepted nothing.** Ten questions were registered before any was
answered. None cleared the 99.5% bar the ten-slot budget sets, and four slots
are spent. The one signal (H1) is about the live pipeline: it rates last
game's quarterback, while the published backtest effectively rates the
announced starter. Switching is INCONCLUSIVE at 99.5%, so it waits on Mark.

**Pushed, no PR yet: branch `announced-qb-capture`.** It records the
announced and model starters in every pick, and notes when they differ.
Nothing the model computes changes. Open it after #84 merges: both branches
bump the README case count, so opening now guarantees a conflict.

**Next action: get #84 re-audited.** Mark re-runs the Booth job on #84 and,
while signed in, reads why the first run posted nothing.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| PR #84, Stage 5 | Open, Booth red (posted nothing) | A re-run, and the log read |
| announced-qb-capture | Pushed, no PR | #84 merging first (README count) |
| Live model on announced starter | Decision | Mark: switch on methodology grounds, like weekly refit, or wait for the 2026 forward test |
| The repo's About panel | Empty | Mark. Repo settings; wording in CLAUDE.md |
| Confirming #73 on a phone | Not done | Only a device proves the zoom is gone |

## Queued, in order

1. **Stage 9's remaining colour work**: the Net Rating bar's diverging pair
   through the dataviz validator in both themes, and deciding what confidence,
   a flagged game and "the model was wrong" each look like.
2. **`.game-card` overflows the viewport below 352px**, 340px card against a
   296px content box at 320. Stage 10's mobile pass.
3. **Six preflight and README guard gaps**, one confirmed by Booth on #78 and
   two found on 2026-09-21 in `check_visual_claims_have_artifacts`. All are
   written up in CLAUDE.md's traps.
4. **Stage 10**, then **Stage 6's broadcast channel**; Stage 7's text-only
   items are unblocked, visual ones wait for 10.

## Known and deliberately not fixed

- **A Booth header can disagree with its verdict block**, logged by `cross_check()`, ten of the last eleven reports. Should it fail? It has cost nothing yet only because the discrepancy count was zero either way.
- **`check_scoped_test_counts` skips a count for a module that does not exist** — a DELETED module passes silently.
- **Only the wrap-up gate and session-start recompute CLAUDE.md's `Suite:` line.** Both manual, accepted.
- **The README says "cases" where its guard counts FILES.** Bumping the number is forced by any new case file; fixing the wording moves the guard's own regex.
- **Nothing on the page reaches the listbox edge flip**; kept and checked over synthetic geometries.
- **A human approval leaves no artifact in the repo.** Booth marked the #80 acceptance UNVERIFIABLE for that reason and was right to; `memory/2026-09-21.md` is what it points at.
- **The co-occurrence trace, and the no-JS findings, are re-derivable only where a browser exists.** No CI job here has one. In both the premise is guarded in the suite and the finding itself is not; accepted.
- **60 of 496 team pairs sit under the CIEDE2000 floor on the Week Board's split bar, and that is accepted.** Decided 2026-09-21 after looking at the alternatives. `src/verify_matchup_cvd.py` still reports it; nothing guards the figure from growing, which is the one loose end if the palette is ever edited.
- **The Booth report check cannot tell WHY a run posted nothing.** It only knows that nothing was posted. The cause is in the action's log, which needs a signed-in browser.
