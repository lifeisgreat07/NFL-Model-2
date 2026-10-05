# 0003. A week's picks are saved once, before its first kickoff

## Decision

The Weekly update runs Tuesday and Thursday at 11:00 UTC. Each run asks
`decide_lock` (`src/pipeline/weekly_update.py`) whether the week's first
game still to come kicks off before the next scheduled run plus
`LOCK_SLACK` (eight hours). If it does, this run locks the week: the picks
are saved to `predictions/` and never rewritten. Usually that is Thursday;
a week with an earlier game (Thanksgiving, a Wednesday game) locks on
Tuesday. A game that has already kicked off is never predicted. A run that
holds the week saves a labelled preview to `predictions/preview/` instead,
and only locked picks are ever graded.

## Why

- A pick saved after kickoff is not a prediction. The Methodology page
  says every pick is locked before kickoff, and the record only means
  something if that is true of every graded game.
- Saving once and never rewriting makes the record auditable: the commit
  that locked a week is the evidence.
- The slack exists because GitHub's scheduled runs started 3.5 to 6.5
  hours late from 2026-09-24. Eight hours covers the worst delay seen and
  still lets an ordinary Thursday night game wait for Thursday's run.

## What it costs

- A Thursday lock leaves about 13 hours to a Thursday night kickoff. A
  failed Thursday run leaves that game unpicked unless someone starts the
  workflow by hand that day; a failure opens an issue.
- Picks cannot react to news after the lock. The QB override routine
  (Monday and Wednesday) exists to get the starting quarterback right
  before it.
- Only one writer of saved picks is allowed. The QB routine must never be
  given the weekly scripts back: two writers is two ways to break a lock.

## What would reopen it

Scheduled runs that start on time for long enough to trust (Stage 42 item
5 revisits `LOCK_SLACK` after four on-time weeks), or a schedule change by
the league.

Sources: `decide_lock` and the comments above `LOCK_SLACK`; CLAUDE.md,
"What runs unattended, and who owns what"; #204 (the Tuesday preview).
