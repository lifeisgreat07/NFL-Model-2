# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-20 (#78 open; the six untraced colour pairs are traced)

---

## Right now

**Suite:** `main` is at `49b697e`; run `python -m pytest -q` and read the whole
summary line before quoting it. On #78's branch at `80f7d93`, HEAD level with
origin, it is 1273 passing, 1 skipped — that branch adds tests, so the two
numbers differ on purpose. Corpus at `80f7d93`: 200 cases, all CAUGHT, from
`python tests/mutation/runner.py` with no `--id`, whose scope is every case.

**One PR open, #78**, "Trace the six untraced ACCEPTED_CLOSE colour pairs",
waiting on Booth. It adds a Playwright verifier under src/ (unbackticked
because it is not on `main` yet and the path guard is right to say so),
rewrites all six "Not traced" entries from what the rendered page shows, and
guards the premise under the two "cannot meet" verdicts.

**Stage:** 8, 8b and 8c complete. Stage 9's component pass is done; colour is
what remains, and tracing turned two queued items into a question.

**Next action: decide whether `--accent-strong`/`--series-a` and
`--accent`/`--series-d` are still defects.** Mark's call, not a measurement,
and it blocks the rest of the colour work. Both were queued on distance alone.
Neither pair can ever be on screen together: `--accent-strong` has one
consumer, `.srs-bar-fill`, on Power Ratings and Team Deep-Dive; `--series-d`
has one, the picks entry of `SERIES`, on Season Accuracy. What is left is a
claim the design makes about itself — colour has exactly four jobs — with two
of them wearing near-identical blues on different screens. If that is a defect,
`--accent` cannot be re-stepped in light mode (searched, zero candidates), so
the fix has to come from the other side of the pair.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| PR #78 | Open | Booth's audit |
| The two KNOWN DEFECT gradings | Traced, ungraded | Mark. See above |
| The repo's About panel | Empty | Mark. Repo settings; wording in CLAUDE.md |
| Confirming #73 on a real phone | Not done | Only a device proves the zoom is gone |
| Week 2 grading | Tue 2026-09-22 | Watch that the page rebuilds itself |
| ATL's week 2 starter | Unresolved | Not ours — predictions are write-once |

## Queued, in order

1. **`teamColor()`'s `#8A93A8` fallback**, wrong in light mode, and the same
   literal in `.week-select`'s chevron data-URI — two sites, one change.
   `tests/test_listbox.py` has the inline-SVG `currentColor` pattern to copy.
   The next real defect with no decision in front of it.
2. **`matchupColors`.** `python src/verify_matchup_cvd.py` (CIEDE2000): 60 of
   496 team pairs under 15, 9 under 5, worst ARI/PHI 0.18, and 20 within 1 of
   the floor so the count moves between honest runs. Stage 8 says team identity
   is a logo, so retiring these bars may delete the problem rather than tune
   it. Mark wanted that decided by looking.
3. **`log_line_snapshot` writes nulls instead of skipping.**
   `src/weekly_update.py` appends a row when the spread is NaN — #75's
   all-null file, and it recurs on any run made days ahead of a week.
4. **`.game-card` overflows the viewport below 352px.** `.game-grid` is
   `repeat(auto-fit, minmax(340px, 1fr))`: 340px card, 296px content box at
   320. Stage 10's mobile pass.
5. **Four preflight and README guard gaps.** `check_test_count` does not strip
   quotations; the commit-message check matches suite-shaped counts only; the
   README says "N cases" where its guard counts FILES — bumped a third time by
   #78, wording untouched all three times.
6. **Stage 10**, then **Stage 6's broadcast channel**; Stage 7's text-only
   items are unblocked, visual ones wait for 10.

## Known and deliberately not fixed

- **A Booth header can disagree with its verdict block**, logged by `cross_check()`. Should it fail?
- **`check_scoped_test_counts` skips a count for a module that does not exist** — a DELETED module passes silently.
- **Only the wrap-up gate and session-start recompute CLAUDE.md's `Suite:` line.** Both manual, accepted.
- **Nothing on the page reaches the listbox edge flip.** The sort labels got
  short enough that the decision is `as-is` from 320 to 520 on both listboxes;
  the rule is kept and checked over synthetic geometries.
- **The co-occurrence trace is re-derivable only where a browser exists.** No
  CI job here has one. The premise under the two "cannot meet" verdicts IS
  guarded in the suite; the findings themselves are not, and that is accepted.
