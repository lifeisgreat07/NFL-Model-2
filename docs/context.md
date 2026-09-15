# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-15 (second session; #74 merged, no open PRs)

---

## Right now

**Suite:** 1184 passing, 1 skipped on `main` at `a60bcb9`. Re-run before quoting
it. Corpus: 33 case files, 180 cases — from `python tests/mutation/runner.py`
with no `--id`, whose scope is every case.

**#75 is open** (branch claude/ecstatic-clarke-npab1e), from the Claude Code
Routine: a week-3 line snapshot whose 16 spreads are all null, none posted 9
days out. Next Tuesday's run recreates it with real lines, so closing loses
nothing; its QB flag needs no merge. Should the routine push branches at all?

**Stage:** 8, 8b and 8c complete. Stage 9's component pass is DONE; what
remains is colour, and those are accessibility defects. There is no Stage 11.

**The first graded week landed and worked.** Week 1 graded (Model A 11/16,
Model B 11/16, market 12/16), Week 2 locked in, SOS populated and its
empty-state note retired itself.

**The weekly run now publishes on its own.** #74 added "Weekly update" to
`.github/workflows/deploy-pages.yml`'s `workflow_run` list; its push uses the
default `GITHUB_TOKEN`, which cannot trigger a workflow, so the `paths:`
trigger never fired. Tue 2026-09-22 11:00 UTC is the bridge's first live
test — check a Pages deploy follows it untouched.

**Next action: the two Week Board sort-control defects, as one PR.** Reproduce
the wrap first — it is the one with no measurement behind it yet.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| The repo's About panel | Empty | Mark. Repo settings; wording in CLAUDE.md |
| Confirming #73 on a real phone | Not done | Only a device proves the zoom is gone |
| Week 2 grading | Tue 2026-09-22 | Watch that the page rebuilds itself |
| #75, the routine's snapshot | Open | Mark: close it, or merge for completeness |
| ATL's week 2 starter | Unresolved | Not ours to fix — predictions are write-once |

## Queued, in order

1. **Two defects on the Week Board sort control — same control, same row, one
   PR.** (a) The listbox opens off-screen at the right edge: `.lbx-list` is
   `left:0` with nowrap options, so a control near the right edge overflows
   while open and the document scrolls sideways. Needs an edge flip. (b) From
   Mark, 2026-09-15: the sort button sizes to its own label, so any option
   longer than "Sort: First Game to Last" wraps the filter row onto a second
   line beside Print / PDF on mobile. **Neither is reproduced here**, and (b)'s
   stated cause is a hypothesis from the symptom. Reproduce both at a 430px
   mobile-emulated viewport before writing any fix.
2. **Stage 9's colour items.** `teamColor()`'s `#8A93A8` fallback, wrong in
   light mode, and the same literal in `.week-select`'s chevron data-URI — two
   sites, one change. `tests/test_listbox.py` asserts the inline-SVG
   `currentColor` pattern to copy.
3. **Colour, as accessibility.** `--accent` vs `--series-a`: 8.1 dE00 in
   light, 6.6 under red-green CVD, floor is 15, and #60 proved they share a
   screen. `matchupColors` ranks by RGB distance: 60 of 496 pairs below the
   floor, worst ARI/PHI at 0.18. One validator run, both themes.
4. **Four preflight and README guard gaps.** `check_test_count` does not strip
   quotations; the commit-message check matches suite-shaped counts only; the
   README says "N cases" where its guard counts FILES (#74 bumped the number,
   left the wording — needs the guard's regex changed). A figure from a
   mutation `--id` glob or a before/after table is the same unchecked shape.
5. **Stage 10.** Duplicate "Model Output" sidebar label, shared page-header,
   table system, mobile pass, empty/error/loading states, and closing
   `dashboard-design-audit` against 15/40. Add: the glossary's definition
   column is right-aligned because every cell carries `.num`.
6. **Stage 6 — broadcast channel.** Unsourced, not deferred: `load_schedules()`
   returns 46 columns and none is a network.
7. **Stage 7's text-only items** are unblocked; visual ones wait for 10.

## Known and deliberately not fixed

- **A Booth header can disagree with its verdict block**, logged by `cross_check()`. Should it fail?
- **`check_scoped_test_counts` skips a count for a module that does not exist** — deliberate, but a DELETED module passes silently.
- **Only the wrap-up gate and the session-start print recompute CLAUDE.md's
  `Suite:` line.** Both manual, accepted.
