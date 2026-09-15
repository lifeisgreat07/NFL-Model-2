# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-15 (second session; #74 open, nothing merged)

---

## Right now

**Suite:** 1173 passing, 1 skipped on `main` at `3f8a29f`; 1184 on the #74
branch at `f7be6a4`. Re-run before quoting either. Corpus: 33 case files and
180 cases on that branch, 32 and 177 on `main` — from
`python tests/mutation/runner.py` with no `--id`, whose scope is every case.

**Stage:** 8, 8b and 8c complete. Stage 9's component pass is DONE; what
remains of Stage 9 is colour, and those are accessibility defects rather than
polish. There is no Stage 11.

**The first graded week landed and worked.** `3f8a29f` at 11:05 UTC graded
Week 1 (Model A 11/16, Model B 11/16, market 12/16) and locked in Week 2. SOS
populated and its empty-state note retired itself, as predicted.

**The page did not rebuild, and #74 fixes it.** The weekly workflow commits
with the default `GITHUB_TOKEN`, which cannot trigger another workflow, and
`.github/workflows/deploy-pages.yml`'s `workflow_run` list named only the
collector. Mark dispatched a build by hand. The guard for this exact defect
existed, scoped to one workflow and one file.

**Next action: get #74 merged, and it is time-boxed.** The next weekly run is
Tue 2026-09-22 11:00 UTC. If #74 is not on `main` by then, that run fails to
publish the same way. Nothing else is worth starting first.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| #74 weekly run rebuilds the page | Open, green locally | Mark's review. Merge before Tue 2026-09-22 11:00 UTC |
| The repo's About panel | Empty | Mark. Repo settings; wording in CLAUDE.md |
| Confirming #73 on a real phone | Not done | Only a device proves the zoom is gone |

## Queued, in order

1. **Two defects on the Week Board sort control — same control, same row, one
   PR.** (a) The listbox opens off-screen at the right edge: `.lbx-list` is
   `left:0` with nowrap options, so a control near the right edge overflows
   while open and the document scrolls sideways. Needs an edge flip. (b) NEW,
   from Mark: the sort button sizes to its own label, so any option longer
   than "Sort: First Game to Last" wraps the filter row onto a second line
   beside Print / PDF on mobile. Needs a stable width. Reproduce (b) first.
2. **Stage 9's colour items.** `teamColor()`'s `#8A93A8` fallback, wrong in
   light mode, and the same literal in `.week-select`'s chevron data-URI — two
   sites, one change. `tests/test_listbox.py` asserts the inline-SVG
   `currentColor` pattern to copy.
3. **Colour, as accessibility.** `--accent` vs `--series-a` are 8.1 dE00 apart
   in light, 6.6 under red-green CVD, against a floor of 15, and #60 proved
   they share a screen. `matchupColors` ranks by RGB Euclidean distance: 60 of
   496 pairs below the floor, worst ARI/PHI at 0.18. One validator run, both
   themes.
4. **Four preflight and README guard gaps.** `check_test_count` does not strip
   quotations; the commit-message check matches suite-shaped counts only; the
   README says "N cases" where its guard counts FILES (#74 bumped the number
   and left the wording, which needs the guard's regex changed). A figure from
   a mutation `--id` glob or a before/after table is the same unchecked shape.
5. **Stage 10.** Duplicate "Model Output" sidebar label, shared page-header,
   table system, mobile pass, empty/error/loading states, and closing
   `dashboard-design-audit` against 15/40. Add: the glossary's definition
   column is right-aligned because every cell carries `.num`.
6. **Stage 6 — broadcast channel.** Unsourced, not deferred: `load_schedules()`
   returns 46 columns and none is a network.
7. **Stage 7's text-only items** are unblocked; visual ones wait for 10.

## Known and deliberately not fixed

- **CLAUDE.md's `Suite:` line goes 1173 -> 1184 when #74 merges.** Not on the
  branch: its PR body enumerates two commits and a third would falsify it.
  `src/session_start.py` prints the line against a real run, so the drift
  announces itself next session.
- **A Booth header can disagree with its own verdict block.** `cross_check()`
  catches and logs it. Open: should it fail?
- **`check_scoped_test_counts` ignores a count for a module that does not
  exist.** Deliberate, but a count naming a DELETED module passes silently.
