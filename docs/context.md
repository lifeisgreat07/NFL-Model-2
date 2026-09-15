# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-15 (#69 merged; README bumped to 31 in `976d0a3`)

---

## Right now

**Suite:** 1123 passing, 1 skipped on `main`. Re-run before quoting it.
Mutation corpus: 31 case files, 165 cases (at `976d0a3`; `python` sum over
each file's `cases` list, not a recalled figure).

**Stage:** 8, 8b and 8c complete. Stage 9's model-colour work (#60) is
merged; what remains of Stage 9 is the component pass and the colour items
below, which are accessibility defects, not polish. There is no Stage 11.

**#69 is merged and `main` is green.** The README bump did not ride with the
merge, so `tests/test_readme_accuracy.py` was red for one commit; fixed in
`976d0a3`. The "cases"/FILES wording gap in that sentence is still queued.

**Stage 9's component pass is done and in review: PR #71.** `#teamdive-select`
is the second `enhanceSelect()` consumer and the first use of `refresh()`.

**Next action: Stage 9's colour items.** `teamColor()`'s `#8A93A8` fallback,
wrong in light mode, and the same literal in `.week-select`'s chevron -- two
sites, one change. Then `--accent` vs `--series-a` and `matchupColors`.

**The grading path is frozen until Tue 2026-09-15, 11:00 UTC.** That run is
the first ever to grade a week with real games in it. Nothing touches
`src/weekly_update.py` or the grading path before it. Surface work is
unaffected and is what the gap is for.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| The repo's About panel | Empty | Mark. Needs repo settings. Wording in CLAUDE.md |
| PR #71, `feat/teamdive-listbox` | Open, preflight green | Booth, then Mark's review |
| First graded week | Scheduled | Tue 2026-09-15 11:00 UTC. Watch the run, check the output |

#68, #69 and #70 are merged and their branches are deleted, local and remote.
`feat/teamdive-listbox` is the only other branch.

## Queued, in order

1. **Stage 9's colour items.** The component pass is done -- `#sort-select` in
   #69, `#teamdive-select` in #71. What remains is `teamColor()`'s `#8A93A8`
   fallback, wrong in light mode, and the same literal in `.week-select`'s
   chevron, a second site nothing had recorded.
2. **Colour, as accessibility.** `--accent` vs `--series-a` are 8.1 dE00 apart
   in light and 6.6 under red-green CVD, against a floor of 15, and Booth
   proved on #60 that they DO share a screen. `matchupColors` still ranks by
   RGB Euclidean distance, which models no colour vision: 60 of 496 team pairs
   below the floor, worst ARI/PHI at 0.18. The Net Rating diverging pair needs
   the dataviz validator in both themes. One investigation, one validator —
   these were split across two stages and should not be.
3. **Stage 10.** Duplicate "Model Output" sidebar label (renders twice),
   shared page-header, table system, mobile pass, empty/error/loading states,
   closing `dashboard-design-audit` against the 15/40 baseline.
4. **Stage 6 — broadcast channel.** NOT deferred, unsourced: `load_schedules()`
   returns 46 columns and none is a network. Needs a new feed with its own
   staleness story, and a flexed game changes network days before kickoff, so
   it needs a refresh policy rather than a one-time fetch.
5. **Two preflight gaps.** `check_test_count` does not strip quotations, so
   a body quoting a historical count false-positives. And the
   commit-message check matches suite-shaped counts only, so any other
   count reaches a message that cannot be corrected without rewriting its
   SHA -- "147 individual cases" did, on #68.
6. **README says "N cases" where its guard counts FILES** (157 across 30).
   Sentence and regex must change together; rewording alone makes the
   check report the line as missing. Ends a collision that has now cost
   three PRs a follow-up commit.
7. **Stage 7's text-only items** are unblocked; the visual ones wait for 10.

## Known and deliberately not fixed

- **A Booth header can disagree with its own verdict block.** #60's audit 4
  does; `cross_check()` already catches and logs it. Open: should it fail?
- **`check_scoped_test_counts` ignores a count for a module that does not
  exist.** Deliberate — a body may describe a file a later phase adds — but a
  count naming a DELETED module passes silently.

Three durable entries moved out of here into CLAUDE.md's traps, where the
length cap says they belong.
