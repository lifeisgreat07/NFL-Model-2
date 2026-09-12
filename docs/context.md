# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-12 (#60 merged after a fifth commit and a fourth audit)

---

## Right now

**Suite:** 876 passing, 1 skipped on `main`. Re-run before quoting it.

**Stage:** 8, 8b and 8c complete. Stage 9 is done apart from the items below.
Stage 11's model-colour work is merged; its remaining items are queued below.

**Next action:** the pipeline item, premise corrected — see the queue. It edits
`src/weekly_update.py`, which the Tuesday run invokes, so build and open it now
and merge AFTER that run. The commit-message count guard can land meanwhile.

**Do not touch the grading path before Tue 2026-09-15, 11:00 UTC.** That run
is the first that will ever grade a week with real games in it.

## Open work, and what each is waiting on

Branch names in full — `src/session_start.py` cross-checks them against git.

| What | State | Waiting on |
|---|---|---|
| Ten merged branches | Still on the remote | Nobody — `git push origin --delete <name>` works from here, as #60's branch proved. Say the word |
| The repo's About panel | Empty | Mark. Wording in CLAUDE.md |

## Queued, in order

1. **Date/time in the pipeline. PREMISE CORRECTED 2026-09-12: channel has no
   source.** This said no game carries a date, kickoff or channel. Half right.
   `load_schedules` gives 46 columns, `gameday`/`gametime`/`weekday` among them
   with no nulls, and `src/data_loader.py` does not subset — so they reach
   `src/weekly_update.py` and are simply not written into the record. Pass them
   through there and through `build_games_js` in `src/generate_dashboard.py`
   with `.get()`. **No broadcast column exists** (`espn`, `ftn`, `pff`, `pfr`
   are cross-reference IDs), so channel needs a new feed, is Stage 6 in nature,
   and must not gate the rest. `gametime` is EASTERN — the six Sunday 09:30
   games are London and Munich — so store `gametime_et`, and note week 10+
   crosses the US clock change.
2. **Reject a suite count in a commit message.** `src/scout_preflight.py` checks
   the PR body and nothing checks commit messages, which is where three of the
   four discrepancies across #60's two audits lived. A count there cannot be
   corrected without rewriting its SHA, so the rule is "do not write one" and
   the check should enforce it. Small, and it closes the defect class the
   session ended on. Same file, same pass: `run_test_suite` reads only the
   passed count, so a red suite reports as a stale figure (trap in CLAUDE.md).
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
