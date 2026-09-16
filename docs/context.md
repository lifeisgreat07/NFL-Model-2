# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-16 (#76 merged, #77 audited SAFE TO MERGE, not merged)

---

## Right now

**Suite:** 1229 passing, 1 skipped — `python -m pytest -q` on `main` at
`89dabf1`, HEAD level with origin. Re-run before quoting it. Corpus: 35 case
files, 191 cases, all CAUGHT — from `python tests/mutation/runner.py` with no
`--id`, whose scope is every case.

**#77 is open, audited SAFE TO MERGE, and is the only branch.** It widens the
colour verifier to every meaning-carrying token pair and fixes nothing. Booth:
7 CONFIRMED, 1 DISCREPANCY (prose miscount, corrected here), 1 UNVERIFIABLE.
Its own suite is 1255 passing, 1 skipped at `69eea27`; corpus 196, all CAUGHT.

**Stage:** 8, 8b and 8c complete. Stage 9's component pass is done; colour is
what remains, and those are accessibility defects. There is no Stage 11 —
`src/dashboard_template.html`'s model-colour comment says the re-step is
"Stage 11 work in docs/context.md", and that pointer has never been true.

**Next action: trace the six pairs in `ACCEPTED_CLOSE` that say "not traced".**
Whether each pair is ever on screen together decides how many of them are real
defects and how many are pairs that can never meet. It is DOM work, not colour
maths, and it has to happen before anyone picks a replacement colour — Booth
caught a false co-occurrence claim about a neighbouring pair on #60.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| #77, the colour sweep | Audited, clean | Mark to merge; body has a five-for-six to fix |
| The repo's About panel | Empty | Mark. Repo settings; wording in CLAUDE.md |
| Confirming #73 on a real phone | Not done | Only a device proves the zoom is gone |
| Week 2 grading | Tue 2026-09-22 | Watch that the page rebuilds itself |
| Which colour floor governs | Answered | OKLab: CVD_TARGET 8, NORMAL_FLOOR 15, both in test_dashboard_charts.py |
| ATL's week 2 starter | Unresolved | Not ours — predictions are write-once |

## Queued, in order

1. **Trace the six "not traced" pairs** in `ACCEPTED_CLOSE` — count with
   `grep -c "'Not traced" tests/test_dashboard_charts.py`; #77's body said five
   and Booth caught it. Each becomes a defect or a "they can never meet".
2. **Separate the two known collisions:** `--accent` vs `--series-d` in light
   (OKLab CVD 1.3) and `--accent-strong` vs `--series-a` in dark (2.8 CVD, 2.9
   NORMAL). Quote OKLab, never CIEDE2000 — the rulers disagree about ranking,
   see CLAUDE.md. `--good` vs `--warn` is NOT one of these: it collapses under
   CVD and both graded surfaces carry the word.
3. **`teamColor()`'s `#8A93A8` fallback**, wrong in light mode, and the same
   literal in `.week-select`'s chevron data-URI — two sites, one change.
   `tests/test_listbox.py` has the inline-SVG `currentColor` pattern to copy.
4. **`matchupColors`.** `python src/verify_matchup_cvd.py` (CIEDE2000): 60 of
   496 team pairs under 15, 9 under 5, worst ARI/PHI 0.18 — and 20 sit within
   1 of the floor, so the count moves by one or two between honest runs. Stage
   8 says team identity is a logo, never a colour, so retiring these bars may
   delete the problem rather than tune it. Mark wanted that decided by looking.
5. **`log_line_snapshot` writes nulls instead of skipping.**
   `src/weekly_update.py` appends a row when the spread is NaN. That produced
   #75's all-null file and will again on any run made days ahead of a week.
6. **`.game-card` overflows the viewport below 352px.** `.game-grid` is
   `repeat(auto-fit, minmax(340px, 1fr))`, so the card is 340px against a 296px
   content box at 320. Stage 10's mobile pass.
7. **Four preflight and README guard gaps.** `check_test_count` does not strip
   quotations; the commit-message check matches suite-shaped counts only; the
   README says "N cases" where its guard counts FILES — bumped twice now,
   wording untouched both times.
8. **Stage 10**, then **Stage 6's broadcast channel**; Stage 7's text-only
   items are unblocked, visual ones wait for 10.

## Known and deliberately not fixed

- **A Booth header can disagree with its verdict block**, logged by `cross_check()`. Should it fail?
- **`check_scoped_test_counts` skips a count for a module that does not exist** — a DELETED module passes silently.
- **Only the wrap-up gate and the session-start print recompute CLAUDE.md's `Suite:` line.** Both manual, accepted.
- **Nothing on the page reaches the listbox edge flip.** The sort labels got
  short enough that the decision is `as-is` at every width from 320 to 520, on
  both listboxes. The rule is kept and checked over synthetic geometries; see
  the comment above `lbxFlipDecision` in `src/dashboard_template.html`.
