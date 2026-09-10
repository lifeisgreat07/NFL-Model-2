# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-10 (long session, PRs #51-#57 merged)

---

## Right now

**Suite:** 765 passing, 1 skipped on `main`. Re-run before quoting it.

**Stage:** 8 and 8b complete. 8c phase 1 merged and proven; phase 2 is next.
Stage 9 started — the Week Board renders the design approved in Stage 8.

**Next action:** Stage 8c phase 2 — stop versioning the generated dashboard.
Not tidiness: `index.html` is generated AND committed, so it conflicted five
times in one day across three branches, and every remaining template stage
pays that tax until it stops being tracked.

**Most losable thing:** `stage-11-model-colours` is pushed with **no PR** — the
only unmerged branch. It carries the Model B colour fix (ochre in charts, blue
in prose; 6.6 dE00 from Model A under red-green CVD in light mode, i.e. the
same colour). Rebase onto `main` and open a PR, or it will be forgotten.

**Pages serves a CI-built artifact now, not the committed file.** Proven: a
manual deploy stamped 18:33 while the committed file said 18:26.

## Open work, and what each is waiting on

Branch names in full — `src/session_start.py` cross-checks them against git.

| What | State | Waiting on |
|---|---|---|
| `stage-11-model-colours` | Pushed, no PR | Rebase and open one |
| Stage 8c phase 2 | Not started, scoped | Nothing |
| Seven merged branches | Still on the remote | Mark, in the web UI |
| The repo's About panel | Empty | Mark. Wording in CLAUDE.md |
| `Auto-regenerate dashboard` #56 | Failed 2026-09-09 | Someone to read its log |

## Queued, in order

1. **Stage 8c phase 2.** Untrack `index.html` and `dist/`; add a ROOT pytest
   conftest building the dashboard once per session — load-bearing, or eight
   guarded tests silently become *skips*; six test failures (four are
   template-vs-artifact drift tests to delete, not patch); two policy tests
   fail once workflows stop committing; delete `src/prune_build_churn.py`,
   then dead; three workflows and README's repo-layout block.
2. **Date/time/channel in the pipeline — blocks three asked-for things.** A week
   has only `season`, `week`, `games`; no game carries a date, kickoff or
   channel. Fable's mock invented all three. Blocks: chronological first sort
   on the Week Board, start time + channel on the card, and the stepper's date
   range. Owner asked for each. Pipeline first; the surface work is small after.
3. **Card visual bug (owner-reported, undiagnosed).** With a breakdown open its
   grid row grows to 585px while its neighbours stay 354px, so `align-items:
   start` leaves dead space; and the notable track-record box sits between the
   Vegas line and the why sentences. Diagnose with a clean VIEWPORT screenshot —
   a full-element capture of `#game-grid` is unreliable, the fixed bottom nav
   bleeds into it.
4. **Stage 11.** `matchupColors` still ranks colours by RGB Euclidean distance,
   which models no colour vision. And `check_test_count` does not strip
   quotations, so a body quoting a historical count false-positives (Booth, #57).
5. **Stage 9, remaining.** Unify the TWO `.game-card` render paths — why the `@`
   survived on My Picks. Then `teamColor()`'s `#8A93A8` fallback (wrong in
   light), Net Rating diverging pair, one button component, focus/keyboard.
6. **Stage 10.** Duplicate "Model Output" sidebar label (renders twice), shared
   page-header, table system, mobile pass, empty/error/loading states, closing
   `dashboard-design-audit` against the 15/40 baseline.
7. **First graded week.** `.github/workflows/weekly-update.yml` fires Tue
   2026-09-15, 11:00 UTC. Never yet run against a week that had games.

## Known and deliberately not fixed

- **`index.html` generated AND committed.** Resolve conflicts by taking the
  branch's copy and rebuilding — never edit markers in a generated file.
- **Run #56 failed, unread.** Hypothesis (unverified): two rebuilds racing.
- **The recurring defect** — a real number from a command whose scope is not the
  sentence's scope — now partly mechanised in CI. It checks
  PR DESCRIPTIONS only; commit messages and source comments are unchecked, and
  that is where two of four instances lived. Full entry in CLAUDE.md.
- **A green check means Booth posted, not approved.** Misread twice today.
