# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-16 (sort-control PR open; #75 closed)

---

## Right now

**Suite:** 1229 passing, 1 skipped — `python -m pytest -q` at `604862f` on the
sort-control branch, HEAD pushed. Re-run before quoting it. Corpus: 35 case
files, 191 cases, all CAUGHT — from `python tests/mutation/runner.py` with no
`--id`, whose scope is every case.

**The sort-control branch is the only open one.** #75 was closed rather than
merged: its whole payload was 16 rows of null spreads, the only all-null file
in `data/line_history/`, and the scheduled weekly workflow already writes that
archive to `main`.

**Stage:** 8, 8b and 8c complete. Stage 9's component pass is done; colour is
what remains, and those are accessibility defects. There is no Stage 11.

**The weekly run publishes on its own and has not yet been proven to.** #74 put
"Weekly update" in `.github/workflows/deploy-pages.yml`'s `workflow_run` list.
Tue 2026-09-22 11:00 UTC is the first live test — check a Pages deploy follows
it untouched.

**Next action: `src/weekly_update.py`'s `log_line_snapshot` writes a row when
the spread is NaN instead of skipping the game.** That produced #75's all-null
file and will again on any run made days ahead of a week. One line, plus a
guard and a mutation case.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| The sort-control PR | Branch pushed | Mark to open it; then Booth |
| The repo's About panel | Empty | Mark. Repo settings; wording in CLAUDE.md |
| Confirming #73 on a real phone | Not done | Only a device proves the zoom is gone |
| Week 2 grading | Tue 2026-09-22 | Watch that the page rebuilds itself |
| ATL's week 2 starter | Unresolved | Not ours — predictions are write-once |

## Queued, in order

1. **`log_line_snapshot` writes nulls instead of skipping.** Found assessing
   #75. `data/line_history/2026_week2_lines.json` holds 64 rows and no nulls;
   #75's file held 16 rows and 16 nulls. Absent inputs get dropped where the
   data is built.
2. **Stage 9's colour items.** `teamColor()`'s `#8A93A8` fallback, wrong in
   light mode, and the same literal in `.week-select`'s chevron data-URI — two
   sites, one change. `tests/test_listbox.py` has the `currentColor` pattern.
3. **Colour, as accessibility.** `--accent` vs `--series-a`: 8.1 dE00 in light,
   6.6 under red-green CVD, floor is 15, and #60 proved they share a screen.
   `matchupColors` ranks by RGB distance: 60 of 496 pairs below the floor.
4. **`.game-card` overflows the viewport below 352px.** Measured at 320 and 340
   with the listbox closed: `.game-grid` is `repeat(auto-fit, minmax(340px,
   1fr))`, so the card is 340px against a 296px content box. Unrelated to the
   sort control — found while confirming it was. Stage 10's mobile pass.
5. **Four preflight and README guard gaps.** `check_test_count` does not strip
   quotations; the commit-message check matches suite-shaped counts only; the
   README says "N cases" where its guard counts FILES — bumped again this PR,
   wording again untouched, second time.
6. **Stage 10.** Duplicate "Model Output" sidebar label, shared page-header,
   table system, mobile pass, empty/error/loading states, and closing
   `dashboard-design-audit` against 15/40. The glossary's definition column is
   right-aligned because every cell carries `.num`.
7. **Stage 6 — broadcast channel.** `load_schedules()` returns 46 columns and
   none is a network. Stage 7's text-only items are unblocked; visual ones
   wait for 10.

## Known and deliberately not fixed

- **A Booth header can disagree with its verdict block**, logged by `cross_check()`. Should it fail?
- **`check_scoped_test_counts` skips a count for a module that does not exist** — a DELETED module passes silently.
- **Only the wrap-up gate and the session-start print recompute CLAUDE.md's `Suite:` line.** Both manual, accepted.
- **Nothing on the page reaches the listbox edge flip.** The sort labels got
  short enough that the decision is `as-is` at every width from 320 to 520, on
  both listboxes. The rule is kept and checked over synthetic geometries; see
  the comment above `lbxFlipDecision` in `src/dashboard_template.html`.
