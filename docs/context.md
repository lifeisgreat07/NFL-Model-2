# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-11 (long session; #58, #59, #61 merged, #60 open)

---

## Right now

**Suite:** 841 passing, 1 skipped on `main`. Re-run before quoting it.

**Stage:** 8, 8b and 8c complete. Stage 9 is done apart from the items below.

**Next action:** merge `stage-11-model-colours` (PR #60) once its final Booth
audit is read. Everything in it is pushed and green; only the merge is left.

**Then:** the pipeline item. It blocks three separate things the owner asked
for and nothing else can start them.

**Do not touch the grading path before Tue 2026-09-15, 11:00 UTC.** That run
is the first that will ever grade a week with real games in it.

## Open work, and what each is waiting on

Branch names in full — `src/session_start.py` cross-checks them against git.

| What | State | Waiting on |
|---|---|---|
| `stage-11-model-colours` | PR #60, 4 commits, suite green | Final audit, then merge |
| Ten merged branches | Still on the remote | Mark, in the web UI |
| The repo's About panel | Empty | Mark. Wording in CLAUDE.md |

## Queued, in order

1. **Date/time/channel in the pipeline — blocks three asked-for things.** A week
   has only `season`, `week`, `games`; no game carries a date, kickoff or
   channel. Fable's mock invented all three. Blocks: chronological first sort
   on the Week Board, start time + channel on the card, and the stepper's date
   range. Owner asked for each. Pipeline first; the surface work is small after.
2. **Reject a suite count in a commit message.** `src/scout_preflight.py` checks
   the PR body and nothing checks commit messages, which is where three of the
   four discrepancies across #60's two audits lived. A count there cannot be
   corrected without rewriting its SHA, so the rule is "do not write one" and
   the check should enforce it. Small, and it closes the defect class the
   session ended on.
3. **Re-step `--accent` against `--series-a`.** They are 8.1 dE00 apart in light
   and 6.6 under red-green CVD, below the floor of 15, and Booth proved on #60
   that they DO share a screen — the onboarding banner's Model A dot and the
   Week Board's pick ticks, on every first visit. Shipping rests on shape and
   role separating them. Re-step the pair so it clears 15 and the argument
   stops being needed.
4. **Stage 11, remaining.** `matchupColors` still ranks colour by RGB Euclidean
   distance, which models no colour vision: 60 of 496 team pairs below the
   dE00 15 floor, worst ARI/PHI at 0.18. And `check_test_count` does not strip
   quotations, so a body quoting a historical count false-positives.
5. **Stage 9, remaining.** Unify the TWO `.game-card` render paths — why the `@`
   survived on My Picks. Then `teamColor()`'s `#8A93A8` fallback (wrong in
   light), Net Rating diverging pair, one button component, focus/keyboard.
6. **Stage 10.** Duplicate "Model Output" sidebar label (renders twice), shared
   page-header, table system, mobile pass, empty/error/loading states, closing
   `dashboard-design-audit` against the 15/40 baseline.
7. **First graded week.** `.github/workflows/weekly-update.yml` fires Tue
   2026-09-15, 11:00 UTC. Never yet run against a week that had games.

## Known and deliberately not fixed

- **A number that was right when written, falsified by the base moving.** Five
  instances in two days. Everything guarded failed loudly within minutes;
  the commit-message trailers, which nothing can guard, rotted silently and
  cost an audit. Full entry in CLAUDE.md; the check is item 2 above.
- **`check_scoped_test_counts` ignores a count for a module that does not
  exist.** Deliberate — a body may describe a file a later phase adds — but it
  also means a count naming a DELETED module passes silently.
- **A green check means Booth posted, not approved.** The verdict is the
  comment text. Misread three times now.
