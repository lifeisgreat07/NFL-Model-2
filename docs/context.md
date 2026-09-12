# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-12 (#60 and #62 merged; #63 open)

---

## Right now

**Suite:** 894 passing, 1 skipped on `main`. Re-run before quoting it.

**Stage:** 8, 8b and 8c complete. Stage 9 is done apart from the items below.
Stage 11's model-colour work is merged; its remaining items are queued below.

**Next action:** PR #63, and it needs a commit before it can merge. `main` has
22 mutation-case files and a README saying 22; #63 adds a 23rd but edits that
line from 21 to 22 — the same edit `main` already has, so git AUTO-MERGES it
silently and `test_readme_accuracy` then goes red on `main`. A conflict would
have stopped and asked; this will not. Bump it to 23, fix the two lines in the
body quoting 22, then merge.

**The grading freeze stands for everything else until Tue 11:00 UTC.** It was
overridden once, for #62, deliberately and on evidence — `src/weekly_update.py`
is step 1 of that job and a crash there aborts grading, so the added lines were
run over all 272 real schedule rows first. #62 is merged, so week 2's file will
carry kickoff times. Nothing else touches that path before the run.

## Open work, and what each is waiting on

Branch names in full — `src/session_start.py` cross-checks them against git.

| What | State | Waiting on |
|---|---|---|
| `preflight-commit-message-counts` | PR #63, 1 commit, suite green, body pre-flighted clean | Booth's audit, then the README-to-23 commit — see above |
| Ten merged branches | Still on the remote | Nobody — `git push origin --delete <name>` works from here, as #60's branch proved. Say the word |
| The repo's About panel | Empty | Mark. Wording in CLAUDE.md |

## Queued, in order

1. **Date/time on the SURFACE — the pipeline half merged as #62.** Records
   carry `gameday`/`gametime_et`/`weekday`; the Week Board ignores them.
   Chronological sort, start time on the card, stepper range. Two things
   first: nothing renders until the Tuesday run saves week 2, and week 1 is
   permanently dateless unless backfilled — decide that, it decides whether
   the sort has anything to sort. ET becomes EST in November, so no naive
   local-zone conversion. Channel has no source; a new feed, Stage 6.
2. **Suite counts and `src/scout_preflight.py` — PR #63, open.** Rejects a
   count in a commit message (the one artifact no later edit can repair),
   stops a red suite being reported as a stale figure, and pins the encoding
   on the subprocess that made the suite red only when nested.
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
