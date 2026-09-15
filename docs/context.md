# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-15 (#71 and #72 merged; #73 audited SAFE TO MERGE)

---

## Right now

**Suite:** 1156 passing, 1 skipped on `main` at `41b1d5b`. Re-run before
quoting it. Mutation corpus on `main`: 31 case files, 173 cases (`python` sum
over each file's `cases` list, not a recalled figure). #73 takes those to 32
and 176.

**Stage:** 8, 8b and 8c complete. Stage 9's component pass is DONE --
`#sort-select` in #69, `#teamdive-select` in #71, both driven by the one
shared `enhanceSelect()`. What remains of Stage 9 is colour, and those items
are accessibility defects rather than polish. There is no Stage 11.

**#73 is the only thing in flight.** A phone bug: `.visually-hidden` sets
`width:1px` while `.week-select` sets `min-width:160px`, and min-width wins,
so every hidden select stayed a 160px box that clipping hid but did not
remove from the page's scrollable overflow. At 430px the Week Board's
document measured 533 wide and a phone shrink-fit the whole page.

**Next action once #73 lands: Stage 9's colour items.** `teamColor()`'s
`#8A93A8` fallback, wrong in light mode, and the same literal in
`.week-select`'s chevron -- two sites, one change.

**The first graded week runs Tue 2026-09-15 11:00 UTC**, the first ever to
grade a week with real games in it. Nothing touches `src/weekly_update.py` or
the grading path before it. Watch the run and check the output. Until it
lands every team has `sos: null`, so the SOS note on Power Ratings renders --
that is correct, and it stops rendering on its own.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| The repo's About panel | Empty | Mark. Repo settings; wording in CLAUDE.md |
| PR #73, `fix/visually-hidden-min-width` | SAFE TO MERGE (16/16 confirmed) | Mark merging it |
| First graded week | Scheduled | Tue 2026-09-15 11:00 UTC |
| Confirming #73 on a real phone | Not done | Emulation cannot shrink-to-fit; only the device proves the zoom is gone |

`fix/visually-hidden-min-width` is the only branch besides `main`.

## Queued, in order

1. **Stage 9's colour items.** `teamColor()`'s `#8A93A8` fallback and the same
   literal in `.week-select`'s chevron, a second site nothing had recorded.
2. **The listbox opens off-screen at the right edge.** `.lbx-list` is `left:0`
   with `white-space:nowrap` options, so a control near the right edge
   overflows: 435 against a 430 viewport while open, back to 430 when it
   closes. Needs an edge flip. Disclosed in #73 and left out of it on purpose.
3. **Colour, as accessibility.** `--accent` vs `--series-a` are 8.1 dE00 apart
   in light and 6.6 under red-green CVD, against a floor of 15, and Booth
   proved on #60 that they DO share a screen. `matchupColors` still ranks by
   RGB Euclidean distance, which models no colour vision: 60 of 496 team pairs
   below the floor, worst ARI/PHI at 0.18. The Net Rating diverging pair needs
   the dataviz validator in both themes. One investigation, one validator.
4. **Stage 10.** Duplicate "Model Output" sidebar label, shared page-header,
   table system, mobile pass, empty/error/loading states, and closing
   `dashboard-design-audit` against the 15/40 baseline. Add one: the glossary's
   definition column is right-aligned because every cell carries `.num`, which
   only became obvious once a long definition moved in.
5. **Stage 6 — broadcast channel.** NOT deferred, unsourced: `load_schedules()`
   returns 46 columns and none is a network. Needs a new feed with its own
   staleness story, and a flexed game changes network days before kickoff.
6. **Four preflight and README guard gaps.** `check_test_count` does not strip
   quotations; the commit-message check matches suite-shaped counts only; the
   README says "N cases" where its guard counts FILES. New: a mutation count
   quoted from an `--id` glob is the same class of unchecked figure, and
   preflight already knows how to check a count against a command.
7. **Stage 7's text-only items** are unblocked; the visual ones wait for 10.

## Known and deliberately not fixed

- **A Booth header can disagree with its own verdict block.** `cross_check()`
  already catches and logs it. Open: should it fail?
- **`check_scoped_test_counts` ignores a count for a module that does not
  exist.** Deliberate — a body may describe a file a later phase adds — but a
  count naming a DELETED module passes silently.
