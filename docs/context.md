# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-21 (#79 and #80 merged; the colour gradings are decided)

---

## Right now

**Suite:** 1305 passing, 1 skipped — `python -m pytest -q` on `main` at
`e1152f8`, HEAD level with origin, which is the order that makes the figure
reproducible. Corpus: 208 cases, all CAUGHT, from
`python tests/mutation/runner.py` with no `--id`, whose scope is every case.

**#80 merged**: both disputed colour pairs graded ACCEPTED, each pinned by the
fact it rests on. Booth: 13 CONFIRMED, 0 discrepancies, 1 UNVERIFIABLE, SAFE
TO MERGE — and its header agreed with its own verdict block for the first
time in eleven reports.

**One PR open, #81**, audited and ready. Stage 9's colour work is unblocked
and its two biggest questions are now settled; what remains is the Net Rating
diverging pair and the confidence / flagged / "model was wrong" language.

**The split-bar question is decided: the bars stay as shipped.** Mark's call
2026-09-21, after four alternatives were rendered side by side on real games
in both themes and under CVD simulation. The measured cost is accepted
knowingly and written up in CLAUDE.md; `teamColor()`, `TEAM_COLOR`,
`CONTRAST_THRESHOLD` and the `#8A93A8` literal all stay. Do not re-open it.

**Next action: merge #81 before the Tuesday run.** Booth: 7 CONFIRMED, 0
discrepancies, 0 unverifiable, SAFE TO MERGE. The scheduled workflow writes
`data/line_history/` straight to `main`, so an unmerged fix is a week of dead
rows if week 4's lines are not posted when it runs.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Booth can pass silently | Found 2026-09-21, unfixed | A step asserting a comment exists for the head SHA. Booth cannot audit its own workflow file, so it ships on a test and an argument, as #30 did |
| The repo's About panel | Empty | Mark. Repo settings; wording in CLAUDE.md |
| Confirming #73 on a phone | Not done | Only a device proves the zoom is gone |
| Week 2 grading | Tue 2026-09-22 | Watch that the page rebuilds itself |
| ATL's week 2 starter | Unresolved | Not ours — predictions are write-once |

## Queued, in order

1. **Booth can report Success and post nothing.** The fix is a step asserting
   a comment exists for the head SHA. Ships on a test and an argument, the
   way #30 did, because Booth structurally cannot audit its own workflow file.
2. **Stage 9's remaining colour work**: the Net Rating bar's diverging pair
   through the dataviz validator in both themes, and deciding what confidence,
   a flagged game and "the model was wrong" each look like.
3. **`.game-card` overflows the viewport below 352px**, 340px card against a
   296px content box at 320. Stage 10's mobile pass.
4. **Six preflight and README guard gaps**, one confirmed by Booth on #78 and
   two found on 2026-09-21 in `check_visual_claims_have_artifacts`. All are
   written up in CLAUDE.md's traps.
5. **Stage 10**, then **Stage 6's broadcast channel**; Stage 7's text-only
   items are unblocked, visual ones wait for 10.

*Retired 2026-09-21, not done: `matchupColors` and `teamColor()`'s fallback.
Decided and kept — see "Right now" above and CLAUDE.md.*

## Known and deliberately not fixed

- **A Booth header can disagree with its verdict block**, logged by `cross_check()`, ten of the last eleven reports. Should it fail? It has cost nothing yet only because the discrepancy count was zero either way.
- **`check_scoped_test_counts` skips a count for a module that does not exist** — a DELETED module passes silently.
- **Only the wrap-up gate and session-start recompute CLAUDE.md's `Suite:` line.** Both manual, accepted.
- **The README says "cases" where its guard counts FILES.** Bumping the number is forced by any new case file; fixing the wording moves the guard's own regex.
- **Nothing on the page reaches the listbox edge flip**; kept and checked over synthetic geometries.
- **A human approval leaves no artifact in the repo.** Booth marked the #80 acceptance UNVERIFIABLE for that reason and was right to; `memory/2026-09-21.md` is what it points at.
- **The co-occurrence trace, and the no-JS findings, are re-derivable only where a browser exists.** No CI job here has one. In both the premise is guarded in the suite and the finding itself is not; accepted.
- **60 of 496 team pairs sit under the CIEDE2000 floor on the Week Board's split bar, and that is accepted.** Decided 2026-09-21 after looking at the alternatives. `src/verify_matchup_cvd.py` still reports it; nothing guards the figure from growing, which is the one loose end if the palette is ever edited.
