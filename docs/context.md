# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-10-06, 18:45 UTC (Stages 53 and 59 moved ahead of Stage 52 so the NHL's and NBA's pages go live sooner, rebuilt on today's layout; Stage 45 items 1 and 2 built on top; all local, nothing pushed)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked
figure. `src/` is packaged: run modules with `python -m src.<package>.<module>`.
The dashboard template is parts under `src/dashboard/`, joined by
`src/pipeline/template_parts.py`. Read it with `read_template()`, never one
part as the page (traps). The NFL is still `src/pipeline/` until Stage 52
merges. **The NHL is live**: `.github/workflows/nhl-daily.yml` (14:00 and 21:00 UTC) saves and
grades its picks and writes its page inputs; `.github/workflows/nhl-canary.yml` runs at 06:40 UTC.
**The NHL's pages are built but not deployed**: `python -m src.sports.nhl.site` writes one page
from the NHL's own files (#310); wiring it into the deploy waits for the lock. The NBA's pages
(`python -m src.sports.nba.site`, #321) show the backtest and no live picks, and wait the same way.

**Next action: the read-only checks**: Tuesday's Weekly update (GitHub's cron copy only;
not started at 13:01 UTC: `DRIFT CHECK: OK`, the "Model A, log loss" section, its runs-table
row), the first nightly shuffled suite and the NHL canary (GitHub's cron only), the NHL's
14:00 and 21:00 UTC runs (the first picks carrying injury lists), and
**Thursday 2026-10-08, the first LOCK on the new code**. Nothing that touches the
weekly run, the weekend refresh or the deploy merges until that lock has been seen to run.

**Mark delegated decisions to Claude on 2026-10-05 ("until I say so").**
Each one is logged with its reason in `memory/` and the Audit Response Log.

**Scheduled runs start from cron-job.org** (Stage 42; `docs/decisions/`),
GitHub's cron the fallback: canary 06:00, slice 06:30, refreshes Fri 05:17,
Sun 21:47, Mon 01:47 (no repo cron yet) and Mon 05:37 UTC. The NHL's jobs
are on GitHub's cron only until Mark adds cron-job.org jobs for them.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Nine post-lock branches | Committed locally, one worktree each, not pushed. All rebased on `main` on 10-06 without conflict, ruff clean, full suite green; `s42-slot-guard` also has a README fix (`83776bc`), its mutation scope run and its PR body written in the session archive | The 10-08 lock, then one PR at a time in the order below |
| Stage 52 (NFL to `src/sports/nfl/`) | migrate_nfl.py (session archive, now v11) rehearsed and COMMITTED on `main` at 110f2c9 (branch `s52-rehearsal`, local only): suite green. v8 leaves Booth fixtures alone, v9 writes a single-module `tests/test_alerts.py`, v10 leaves the history test's throwaway repository alone, v11 moves the home page's NFL folders; #324 made the registration checks follow the move. v11 run on the Stage 59 branch gives the version already tested on the rehearsal | Step 2's PRs, then the window after a Thursday lock |
| Stages 53, 59, 45 (items 1, 2) | **Moved ahead of Stage 52** (Claude, under the delegation, 2026-10-06: Mark wants the NHL's and NBA's pages live soon), rebuilt on today's layout as a stack: `s53-site-pre52` (one sport at a time: nfl/, nhl/, nba/), `s59-home-pre52` (home page, sport pills for Mark to confirm), `s45-1-pins`, `s45-2-csp`. Suites green, browser checker clean; PR bodies in the session archive. The NHL's page builds once its daily run has written the season's schedule | The 10-08 lock and the slot guard's merge; then one PR each |
| NBA (Stage 61) | Registered (#312), history and backtest merged (#313, #314, #318, #319): H1 and H2 ACCEPT, H3 REJECT (Model B is worse than the market), availability helps (M1). Backtest-only pages merged (#321), option A of the rendered "NBA Board Options", Claude's recommendation | **Decided** (Mark, 2026-10-06): option A stands, no live NBA picks this season; deploying with Stage 53 |
| Stage 60 item 2 | The whole mutation corpus at `36fc82d`: every case caught (2026-10-06); a first run was killed by my own cleanup (Audit Response Log) | The leak fixture is merged (#322, `tests/booth_fixtures/cross-sport-leak/`); its baseline test skips until the Booth regression run, dispatched after the lock (Mark approved it) |
| cron-job.org | Six NFL jobs on, Weekly update job off; no NHL jobs | Stage 42's slot guard; Mark adds the NHL's two on the evening of 10-06 |
| Private vulnerability reporting | Off (SECURITY.md covers both) | Mark's choice, Settings, Security |

## Queued, in order (after the 10-08 lock is seen to run)

The branches and their worktrees are listed in the session archive's handoff file.
1. Stage 42's slot guard (`s42-slot-guard`), then Mark switches on the Weekly update's cron-job.org job.
2. Stage 53 (`s53-site-pre52`): the NHL's and NBA's pages go live.
3. Stage 59 (`s59-home-pre52`): the home page and the sport pills.
4. Stage 36 item 7 (`s36-7-folders`).
5. Stage 37 item 3 (`s37-3-final-status`, plus `2af662a` re-anchoring two cases), then the backfill of weeks 1 to 4's final snapshots.
6. Stage 37 items 4 and 6 (`s37-4-line-moves`, `s37-6-neutral-site`), Stage 41 items 5 and 7 (`s41-5-canary-sources`, `s41-7-provenance`).
7. The Monday 01:47 fallback cron line (`s42-monday-fallback`), the cancelled-game state (`s39-cancelled-state`).
8. Stage 45 items 1 and 2 (`s45-1-pins`, `s45-2-csp`).
9. Stage 52 with migrate_nfl v11, then Mark re-points cron-job.org's jobs and the QB routine (stage52_repoint.md in the session archive).
Then Stage 21 (`s21-insights`, option A, Mark's pick) once week 5 is graded. Never start the mutation runner under pythonw (memory/2026-10-06.md).

One branch at a time. Rebase each on `main` before opening, then run the
suite and the mutation scope at the exact head (scope_run.py, in the session
archive's `one-off-scripts`), and list the case files. Keep counts out of commit
messages. Branches that change `tests/test_action_pins.py`'s counts (now 21) or a
shared case file need their numbers or anchors refreshed on rebase.

## Known and deliberately not fixed

- **Scheduled runs start hours late** on GitHub's cron; cron-job.org starts them on time.
- **Booth's audit can run past its 20-minute limit** on a big PR (#302 twice, #319); a re-run or a body edit giving it a bounded check finished well inside it.
- **Booth's prose can count an UNVERIFIABLE its block does not**: the run goes red over a SAFE TO MERGE comment (#286, #296, #303, #307).
- **The drift check re-tests a growing sample every week**, so it will sometimes flag by chance. R4 registered it as written.
- **A failed Thursday run leaves Thursday night's game unpicked** unless dispatched by hand that day.
- **Mutation runs quote a count Booth cannot always rerun**: a large scope is UNVERIFIABLE by design; the files are listed.
- **Preview cards have no TV channel or team-news line**; **the share image says "The Pick'em Model"** (Mark, #242).
- **`check_scoped_test_counts` skips a count for a module that does not exist**; **only the wrap-up gate and session-start recompute CLAUDE.md's `Suite:` line.**
- **A human approval leaves no artifact in the repo.** `memory/` records it.
- **Season Accuracy's trend end-labels** stack where Model A and Model B end on the same value.
- **60 of 496 team pairs sit under the CIEDE2000 floor on the Week Board's split bar, accepted 2026-09-21.**
- **The reproducibility audit flips between GitHub runners**; local Windows reproduces exactly.
- **`ubuntu-latest` moves to Ubuntu 26 from 2026-10-19.** Nothing pins the image; watch the first runs after it.
