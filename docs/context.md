# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-11 (Stage 8c phase 2 on a branch)

---

## Right now

**Suite:** re-run before quoting it. The root `conftest.py` now builds the
dashboard first, so seven tests that used to *skip* when `index.html` was
absent actually run.

**Stage:** 8, 8b and 8c complete. Stage 9 started — the Week Board renders the
design approved in Stage 8.

**Next action:** get `stage-8c-untrack-build-output` reviewed and merged, then
the pipeline item below. Phase 2 untracked `index.html` and `dist/`, deleted
the churn pruner and the `Auto-regenerate dashboard` workflow, and left
`.github/workflows/deploy-pages.yml` as the only builder. That ends the
conflict tax: a branch
touching the template no longer collides with whatever CI regenerated on main.

**Most losable thing:** `stage-11-model-colours` is pushed with **no PR**. It
carries the Model B colour fix (ochre in charts, blue
in prose; 6.6 dE00 from Model A under red-green CVD in light mode, i.e. the
same colour). Rebase onto `main` and open a PR, or it will be forgotten.

**Pages serves a CI-built artifact now, not the committed file.** Proven: a
manual deploy stamped 18:33 while the committed file said 18:26.

## Open work, and what each is waiting on

Branch names in full — `src/session_start.py` cross-checks them against git.

| What | State | Waiting on |
|---|---|---|
| `stage-8c-untrack-build-output` | Open PR | Booth, then merge |
| `stage-11-model-colours` | Pushed, no PR | Rebase and open one |
| Seven merged branches | Still on the remote | Mark, in the web UI |
| The repo's About panel | Empty | Mark. Wording in CLAUDE.md |
| `Auto-regenerate dashboard` #56 | Failed 2026-09-09; workflow now deleted | Nothing — moot |

## Queued, in order

1. **Date/time/channel in the pipeline — blocks three asked-for things.** A week
   has only `season`, `week`, `games`; no game carries a date, kickoff or
   channel. Fable's mock invented all three. Blocks: chronological first sort
   on the Week Board, start time + channel on the card, and the stepper's date
   range. Owner asked for each. Pipeline first; the surface work is small after.
2. **Card visual bug (owner-reported, undiagnosed).** With a breakdown open its
   grid row grows to 585px while its neighbours stay 354px, so `align-items:
   start` leaves dead space; and the notable track-record box sits between the
   Vegas line and the why sentences. Diagnose with a clean VIEWPORT screenshot —
   a full-element capture of `#game-grid` is unreliable, the fixed bottom nav
   bleeds into it.
3. **Stage 11.** `matchupColors` still ranks colours by RGB Euclidean distance,
   which models no colour vision. And `check_test_count` does not strip
   quotations, so a body quoting a historical count false-positives (Booth, #57).
4. **Stage 9, remaining.** Unify the TWO `.game-card` render paths — why the `@`
   survived on My Picks. Then `teamColor()`'s `#8A93A8` fallback (wrong in
   light), Net Rating diverging pair, one button component, focus/keyboard.
5. **Stage 10.** Duplicate "Model Output" sidebar label (renders twice), shared
   page-header, table system, mobile pass, empty/error/loading states, closing
   `dashboard-design-audit` against the 15/40 baseline.
6. **First graded week.** `.github/workflows/weekly-update.yml` fires Tue
   2026-09-15, 11:00 UTC. Never yet run against a week that had games.

## Known and deliberately not fixed

- **`check_scoped_test_counts` ignores a count attributed to a module that does
  not exist.** Deliberate, not a hole: a body may describe a file a later phase
  adds. Noted here because it also means a count naming a DELETED module passes
  silently, which is why the #54 fixture had to be re-anchored rather than
  re-pointed when its module went away.
- **The recurring defect** — a real number from a command whose scope is not the
  sentence's scope — now partly mechanised in CI. It checks
  PR DESCRIPTIONS only; commit messages and source comments are unchecked, and
  that is where two of four instances lived. Full entry in CLAUDE.md.
- **A green check means Booth posted, not approved.** Misread twice today.
