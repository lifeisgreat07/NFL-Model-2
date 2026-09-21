# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-20 (#78 merged; queue item 1 turned out not to be a defect)

---

## Right now

**Suite:** 1273 passing, 1 skipped — `python -m pytest -q` on `main` at
`f36d68b`, HEAD level with origin, which is the order that makes the figure
reproducible. Corpus: 200 cases, all CAUGHT, from
`python tests/mutation/runner.py` with no `--id`, whose scope is every case.

**No open PRs and no branches but `main`.** #78 merged: the six
`ACCEPTED_CLOSE` entries reading "Not traced" are traced against the rendered
page by `src/verify_token_cooccurrence.py`. Booth: 14 CONFIRMED, 0
discrepancies, 1 UNVERIFIABLE, SAFE TO MERGE — and its prose header disagreed
with its own verdict block, the ninth report to do so.

**Stage:** 8, 8b and 8c complete. Stage 9's component pass is done; colour is
what remains, and two of the three things queued under it are now questions.

**Next action: decide whether `--accent-strong`/`--series-a` and
`--accent`/`--series-d` are still defects.** Mark's call, not a measurement,
and the rest of Stage 9's colour work waits on it. Both were queued on
distance alone, and neither pair can ever be on screen together — each token
has one consumer, on pages the other never reaches. What is left is the
design's claim about itself, colour having exactly four jobs, with two of them
wearing near-identical blues on different screens. If that is a defect,
`--accent` cannot be re-stepped in light mode (searched, zero candidates), so
the fix has to come from the other side of the pair.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| The two KNOWN DEFECT gradings | Traced, ungraded | Mark. See above |
| Queue item 1's premise | Refuted, unrecorded | Mark. See below |
| The repo's About panel | Empty | Mark. Repo settings; wording in CLAUDE.md |
| Confirming #73 on a phone | Not done | Only a device proves the zoom is gone |
| Week 2 grading | Tue 2026-09-22 | Watch that the page rebuilds itself |
| ATL's week 2 starter | Unresolved | Not ours — predictions are write-once |

## Queued, in order

1. **The `#8A93A8` item is NOT a defect, and nothing records that yet.**
   Refuted 2026-09-20 twice over — the chevron never paints, and the no-JS
   reader it was kept for cannot reach the control. Evidence and method in
   `memory/2026-09-20.md`. Proposed: correct the reasons in CLAUDE.md, the two
   `tests/mutation/cases/listbox.json` `why` fields and `tests/test_listbox.py`'s docstring; leave
   the guards alone; add a `<noscript>` note.
2. **`teamColor()`'s fallback may be deleted by item 3.** Reached only for an
   abbreviation outside the 32 in `TEAM_COLOR`, and its only caller is
   `matchupColors`, whose only consumer is the Week Board card's split bar.
3. **`matchupColors`.** `python src/verify_matchup_cvd.py` (CIEDE2000): 60 of
   496 team pairs under 15, 9 under 5, worst ARI/PHI 0.18. Stage 8 says team
   identity is a logo, so retiring these bars may delete the problem rather
   than tune it. Mark wanted that decided by looking.
4. **`log_line_snapshot` writes nulls instead of skipping.**
   `src/weekly_update.py` appends a row when the spread is NaN — #75's
   all-null file, recurring on any run made days ahead of a week. The first
   item here with a real trigger and no decision in front of it.
5. **`.game-card` overflows the viewport below 352px**, 340px card against a
   296px content box at 320. Stage 10's mobile pass.
6. **Four preflight and README guard gaps**, one confirmed by Booth on #78.
7. **Stage 10**, then **Stage 6's broadcast channel**; Stage 7's text-only
   items are unblocked, visual ones wait for 10.

## Known and deliberately not fixed

- **A Booth header can disagree with its verdict block**, logged by
  `cross_check()`, nine reports deep. Should it fail? It cost nothing on #78
  only because 0 discrepancies is 0 either way.
- **`check_scoped_test_counts` skips a count for a module that does not exist** — a DELETED module passes silently.
- **Only the wrap-up gate and session-start recompute CLAUDE.md's `Suite:` line.** Both manual, accepted.
- **Nothing on the page reaches the listbox edge flip**; kept and checked over synthetic geometries.
- **The co-occurrence trace is re-derivable only where a browser exists.** No
  CI job here has one and Booth confirmed it could not run it either. The
  premise under the two "cannot meet" verdicts IS guarded in the suite; the
  findings themselves are not, and that is accepted.
