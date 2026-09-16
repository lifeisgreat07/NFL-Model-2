# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-16 (#76 merged; colour work is next)

---

## Right now

**Suite:** 1229 passing, 1 skipped — `python -m pytest -q` on `main` at
`89dabf1`, HEAD level with origin. Re-run before quoting it. Corpus: 35 case
files, 191 cases, all CAUGHT — from `python tests/mutation/runner.py` with no
`--id`, whose scope is every case.

**No open PRs.** #76 merged (sort control: edge flip, frozen button width,
shorter labels; Booth 9 CONFIRMED / 0 discrepancies / 4 UNVERIFIABLE, all four
being pixel figures its sandbox had no browser for). Two of those four were
afterwards confirmed on markys through the built-in browser at 430 and 390:
`--lbx-fit` 218px, all six options 218, no list past the viewport. #75 closed.

**Stage:** 8, 8b and 8c complete. Stage 9's component pass is done; colour is
what remains, and those are accessibility defects. There is no Stage 11 —
`src/dashboard_template.html`'s model-colour comment says the re-step is
"Stage 11 work in docs/context.md", and that pointer has never been true.

**Next action: widen `src/verify_model_colours.py` from its two-pair table to
every meaning-carrying token pair, both themes, normal and CVD.** It is the
guard that would have caught the finding below, and it tells us the real shape
of the palette problem before anyone picks a colour.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| The repo's About panel | Empty | Mark. Repo settings; wording in CLAUDE.md |
| Confirming #73 on a real phone | Not done | Only a device proves the zoom is gone |
| Week 2 grading | Tue 2026-09-22 | Watch that the page rebuilds itself |
| Which colour floor governs | Undecided | Mark. 8 is what shipped, 15 is what the design record quotes |
| ATL's week 2 starter | Unresolved | Not ours — predictions are write-once |

## Queued, in order

1. **Widen the colour verifier to the whole class.** Two-pair table today. See
   the four colour findings in CLAUDE.md for what it missed and why.
2. **`--accent` vs `--series-d`, light mode, 1.58 dE00 under CVD.** The worst
   pair on the page and unrecorded until 2026-09-16. Before proposing a fix,
   trace whether the two actually co-occur — Booth caught a false co-occurrence
   claim about the neighbouring pair on #60.
3. **`teamColor()`'s `#8A93A8` fallback**, wrong in light mode, and the same
   literal in `.week-select`'s chevron data-URI — two sites, one change.
   `tests/test_listbox.py` has the inline-SVG `currentColor` pattern to copy.
4. **`matchupColors`.** Verified with `python src/verify_matchup_cvd.py`: 60 of
   496 distinct team pairs under dE00 15, 9 under 5, worst ARI/PHI 0.18. Note
   20 pairs sit within 1 dE00 of the floor, so the count is unstable by one or
   two between honest runs. Stage 8's rule says team identity is a logo, never
   a colour — retiring these bars may delete the problem rather than tune it,
   and Mark wanted that decided by looking.
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
