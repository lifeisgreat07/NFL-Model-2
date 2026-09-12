# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-12 (#60, #62, #63 merged; no open PRs)

---

## Right now

**Suite:** 918 passing, 1 skipped on `main`. Re-run before quoting it.

**Stage:** 8, 8b and 8c complete. Stage 9 is done apart from the items below.
Stage 11's model-colour work is merged; its remaining items are queued below.

**Next action:** a decision, not a keystroke — whether to backfill week 1's
date and kickoff. It is the only saved week, it has none, and predictions are
write-once, so it stays blank in the stepper beside every dated week unless
somebody amends it under a stated exception. It also decides whether the
Week Board's chronological sort has anything to sort for week 1. Then the
surface work, queue item 1.

**The grading freeze stands for everything else until Tue 11:00 UTC.** It was
overridden once, for #62, deliberately and on evidence — `src/weekly_update.py`
is step 1 of that job and a crash there aborts grading, so the added lines were
run over all 272 real schedule rows first. #62 is merged, so week 2's file will
carry kickoff times. Nothing else touches that path before the run.

## Open work, and what each is waiting on

Branch names in full — `src/session_start.py` cross-checks them against git.

| What | State | Waiting on |
|---|---|---|
| Eleven merged branches | Still on the remote | Nobody — `git push origin --delete <name>` works from here. Say the word |
| The repo's About panel | Empty | Mark. Wording in CLAUDE.md |

## Queued, in order

1. **Date/time on the SURFACE — the pipeline half merged as #62.** Records
   carry `gameday`/`gametime_et`/`weekday`; the Week Board ignores them.
   Chronological sort, start time on the card, stepper range. Nothing renders
   until the Tuesday run saves week 2, and week 1 stays dateless (item 2), so
   the dateless case is the FIRST case, not an edge one. ET becomes EST in
   November, so no naive local-zone conversion. Channel has no source.
2. **Week 1's missing date — DECIDED 2026-09-12: no backfill.** The week is
   played, so a date on it is cosmetic and not worth an exception to
   write-once. Consequence: the Week Board must render a dateless week
   properly and the sort must place it sanely. Do not re-open this.
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

- **A Booth header can disagree with its own verdict block.** #60's audit 4 does;
  `cross_check()` already catches and logs it. Open: should it fail an audit?
- **A number that was right when written, falsified by the base moving.** Five
  instances in two days. Everything guarded failed loudly within minutes;
  the commit-message trailers, which nothing can guard, rotted silently and
  cost an audit. Full entry in CLAUDE.md; the check is item 2 above.
- **`check_scoped_test_counts` ignores a count for a module that does not
  exist.** Deliberate — a body may describe a file a later phase adds — but it
  also means a count naming a DELETED module passes silently.
- **A green check means Booth posted, not approved.** The verdict is the
  comment text. Misread three times now.
