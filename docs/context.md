# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-12 (#64, #65, #66, #67 merged; no open PRs; no open branches)

---

## Right now

**Suite:** 1045 passing, 1 skipped on `main`. Re-run before quoting it.
Mutation corpus: 29 case files, 151 cases (at `6d5147d`; `python` sum over
each file's `cases` list, not a recalled figure).

**Stage:** 8, 8b and 8c complete. Stage 9 is done apart from one component
pass. Stage 11's model-colour work is merged; its remaining items are below
and are accessibility defects, not polish.

**Next action:** Stage 9's component pass — replace the two native `<select>`
controls with a real listbox. This is one job, not two: a listbox IS the
"one button component with variants and states" plus the focus/keyboard pass,
so building them separately writes that behaviour twice.
`-webkit-appearance: none` is not an alternative; it restyles the closed
control and does nothing to the picker iOS opens on tap.

**The grading path is frozen until Tue 2026-09-15, 11:00 UTC.** That run is
the first ever to grade a week with real games in it. Nothing touches
`src/weekly_update.py` or the grading path before it. Surface work is
unaffected and is what the gap is for.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| The repo's About panel | Empty | Mark. Needs repo settings. Wording in CLAUDE.md |
| First graded week | Scheduled | Tue 2026-09-15 11:00 UTC. Watch the run, check the output |

No open PRs. No branches but `main` — sixteen were deleted on 2026-09-12,
each checked with `git merge-base --is-ancestor` before any deletion.

## Queued, in order

1. **Stage 9's component pass.** The two native selects → a real listbox, with
   variants, states, focus and keyboard. Then `teamColor()`'s `#8A93A8`
   fallback, which is wrong in light mode.
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
5. **`check_test_count` does not strip quotations**, so a body quoting a
   historical count false-positives.
6. **Stage 7's text-only items** are unblocked; the visual ones wait for 10.

## Known and deliberately not fixed

- **A Booth header can disagree with its own verdict block.** #60's audit 4
  does; `cross_check()` already catches and logs it. Open: should it fail?
- **A number right when written, falsified by the base moving.** The fix is
  now known and proved: name the commit the figure was measured at, and it
  stays true when the base moves. Full entry in CLAUDE.md.
- **`check_scoped_test_counts` ignores a count for a module that does not
  exist.** Deliberate — a body may describe a file a later phase adds — but a
  count naming a DELETED module passes silently.
- **A green check means Booth posted, not approved.** The verdict is the
  comment text. Misread three times now.
- **Booth's environment varies between runs.** One audit drove headless
  Chromium; the next had no browser at all. UNVERIFIABLE on a render claim
  says which runner it hit, not whether the claim is sound.
