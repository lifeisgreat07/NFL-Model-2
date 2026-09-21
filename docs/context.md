# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-21 (#79 merged; queue item 1 closed)

---

## Right now

**Suite:** 1286 passing, 1 skipped — `python -m pytest -q` on `main` at
`db79fc7`, HEAD level with origin, which is the order that makes the figure
reproducible. Corpus: 203 cases, all CAUGHT, from
`python tests/mutation/runner.py` with no `--id`, whose scope is every case.

**No open PRs and no branches but `main`.** #79 merged: the no-script note,
its guard and three mutation cases. Booth's verdict block read 7 CONFIRMED,
0 discrepancies, 1 UNVERIFIABLE — no browser in that runner — and SAFE TO
MERGE. Two defects were in the report itself, neither affecting the verdict
and both now in CLAUDE.md's traps: the prose header disagreed with its own
block, the tenth report to do so, and it quoted "204 passed" for an anchor
test that reports 203.

**Queue item 1 is closed.** The `#8A93A8` chevron is dead, not wrong in light
mode; the reader the two markup-visible selects were kept for cannot reach
either page. Method in `memory/2026-09-21.md`.

**Stage:** 8, 8b and 8c complete. Stage 9's component pass is done; colour is
what remains.

**Next action: decide whether `--accent-strong`/`--series-a` and
`--accent`/`--series-d` are still defects.** Mark's call, not a measurement,
and the rest of Stage 9's colour work waits on it. Both were queued on
distance alone, and neither pair can be on screen together — each token has
one consumer, on pages the other never reaches. What is left is the design's
claim about itself: colour has four jobs, two of them wearing near-identical
blues on different screens. If that is a defect, `--accent` cannot be
re-stepped in light mode (searched, zero candidates), so the fix comes from
the other side of the pair. It expires: the Season Accuracy legend paints all
four series swatches once a second week grades, so `--accent`/`--series-d`
stops being a pair that cannot meet on Tue 2026-09-22.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| The two KNOWN DEFECT gradings | Traced, ungraded | Mark. See above |
| The repo's About panel | Empty | Mark. Repo settings; wording in CLAUDE.md |
| Confirming #73 on a phone | Not done | Only a device proves the zoom is gone |
| Week 2 grading | Tue 2026-09-22 | Watch that the page rebuilds itself |
| ATL's week 2 starter | Unresolved | Not ours — predictions are write-once |

## Queued, in order

1. **`teamColor()`'s fallback may be deleted by item 2.** Reached only for an
   abbreviation outside the 32 in `TEAM_COLOR`; its only caller is
   `matchupColors`, whose only consumer is the Week Board card's split bar.
   It is now the only live site of the `#8A93A8` literal.
2. **`matchupColors`.** `python src/verify_matchup_cvd.py` (CIEDE2000): 60 of
   496 team pairs under 15, 9 under 5, worst ARI/PHI 0.18. Stage 8 says team
   identity is a logo, so retiring these bars may delete the problem rather
   than tune it. Mark wanted that decided by looking.
3. **`log_line_snapshot` writes nulls instead of skipping.**
   `src/weekly_update.py` appends a row when the spread is NaN — #75's
   all-null file, recurring on any run made days ahead of a week. The first
   item here with a real trigger and no decision in front of it.
4. **`.game-card` overflows the viewport below 352px**, 340px card against a
   296px content box at 320. Stage 10's mobile pass.
5. **Six preflight and README guard gaps**, one confirmed by Booth on #78 and
   two found on 2026-09-21 in `check_visual_claims_have_artifacts`. All are
   written up in CLAUDE.md's traps.
6. **Stage 10**, then **Stage 6's broadcast channel**; Stage 7's text-only
   items are unblocked, visual ones wait for 10.

## Known and deliberately not fixed

- **A Booth header can disagree with its verdict block**, logged by `cross_check()`, ten reports deep. Should it fail? It has cost nothing yet only because both times the discrepancy count was zero either way.
- **`check_scoped_test_counts` skips a count for a module that does not exist** — a DELETED module passes silently.
- **Only the wrap-up gate and session-start recompute CLAUDE.md's `Suite:` line.** Both manual, accepted.
- **The README says "cases" where its guard counts FILES.** Bumping the number is forced by any new case file; fixing the wording moves the guard's own regex.
- **Nothing on the page reaches the listbox edge flip**; kept and checked over synthetic geometries.
- **The co-occurrence trace, and the no-JS findings, are re-derivable only where a browser exists.** No CI job here has one. In both the premise is guarded in the suite and the finding itself is not; accepted.
