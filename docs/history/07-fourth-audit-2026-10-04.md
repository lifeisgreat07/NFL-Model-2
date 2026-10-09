# The 2026-10-04 fourth audit

Part of the stage history; the index is `docs/stage-history.md`. Moved verbatim from
that file on 2026-10-06 (Stage 49 item 24).

## Stages 36 to 41: the 2026-10-04 fourth audit (planned 2026-10-04)

The fourth independent audit scored the repository 86/100 on 2026-10-04 at
`6af07c7` (after #249 to #265), up from 83, 78 and 71, with no regressions.
It proposed Stages 36 to 39 and 25 forward items. Every item was checked
against the code before it became one of the items below; the verdicts and
reasons are in the Audit Response Log. Mark approved this plan 2026-10-04.

**Corrections to the audit, so they are not re-litigated:**
- The week-4 lock (2026-10-01, `c80cb28`) ran on the code from before
  #255 and #258. The first scheduled run on the packages, `MODEL_SPECS`,
  the log-loss drift check and the template parts is Tuesday 2026-10-06;
  the first LOCK on them is Thursday 2026-10-08.
- (Withdrawn the same day.) The review first said seven registry entries
  were missing from Model Lab. Six of them (Stage 5 H11; Stage 6 N2, N3,
  A1, R2, A2) are off the page by Stage 18's decision, held by
  `test_every_result_file_is_an_entry_once_and_nothing_unasked_is`: never
  run, so no decision to show. Only Stage 33's R4 is a gap, because only
  Stage 33's registry promises a row for every question. The audit was
  right.
- The MNF closing line is not lost: nflverse keeps it after the game. What
  is lost is the MNF final score on the page.
- Neutral sites are a regular-season question, not a Super Bowl one: eight
  2026 games, and nothing in `src/` reads the schedule's `location`.
- Playoff pick'em points need nothing: `confidence_points` is `n - i` for
  any n, and bye weeks already vary n from week 5 (Mark agreed).
- Worst scheduled-start delay so far is 6h35m (canary); the weekend
  refresh's worst is 6h19m, not 5h51m.

**Decided:** the audience switcher is not built; the current state stays
(Mark, 2026-10-04). Two rendered options may be shown later, under Stage 22.
Releases per `MODEL_VERSION` are in (Mark, reversing "later").

Rules, on top of CLAUDE.md's PR loop: one item, one PR; anything touching
the weekly run or the weekend refresh merges only after the 2026-10-08 lock
is seen to run; every guard gets a mutation case run by `--id`; every
mutation claim names its case files.

### Stage 36 - Loose ends

1. The `sys.path.insert(0, ROOT)` lines made dead by `pyproject.toml`'s
   `pythonpath`, then ruff `RUF100` once (262 of the 265 unused `noqa` are
   E402 behind those lines; keep `weekend_refresh.py`'s real F401). Three
   stale comments (`generate_dashboard.py` sys.path, `requirements-dev.txt`
   "pyflakes only", `nfl-run-backtest.yml` naming `calibration.json` as the
   drift baseline) and `conftest.py`'s unused `GENERATOR`.
2. Stage 33's R4 gets its Model Lab row (a monitoring rule: ADOPTED, shown
   as ACCEPT), with a test that a registry promising a row for every
   question gets one.
3. The type-check test fails under `CI` instead of skipping.
4. A test that each `nfl-run-backtest.yml` option resolves to a real module.
5. The lateness margin in `tests/test_weekend_refresh.py` reads
   `LOCK_SLACK`; backup files under `src/dashboard/` are gitignored. The
   strict folder check stays (pushback: Pages builds from a clean checkout).
6. Booth's prompt: do not re-read CLAUDE.md or BOOTH_PROTOCOL.md after the
   stash. Booth skips PRs that edit its workflow; merges on Mark's say-so.
7. `tv_channels.main`'s folder defaults come from `paths.py`, and `COPIES`
   catches a `ROOT / 'predictions' / 'nfl'` default. After the 2026-10-08 lock.
8. `docs/traps.md`: a short rules index at the top and a size guard.

### Stage 37 - The honest states

1. My Picks: "0 counted -- N late, M untimed" on the scoreboard, the trend
   chart and the My Picks page, with the export/import hint. The kickoff
   lock stays.
2. Week Board: "regional" on Sunday-afternoon CBS and FOX pills; one header
   per kickoff slot under the chronological sort only.
3. The weekly run refreshes the game status of the week it grades, in the
   same commit, so Monday night's score reaches the page; backfill the
   week 1 to 3 snapshots. (Not a fourth cron.)
4. Line snapshots append when the line changed, with a `captured_utc`.
5. Methodology: what the page deliberately does not show.
6. A card note on neutral-site games.
Items 3 and 4 wait for the 2026-10-08 lock.

### Stage 38 - Registrations written now

Family `stage38`, two confirmatory slots (97.5%): C1 an offseason gap in
the team ratings (item 8; all weeks decide, weeks 1-4 reported); B1
week-block bootstrap over R1-R3 and the published comparisons (item 13,
measurement); M1 live reliability against the backtest (item 14, printed,
no alert); L1 market at the lock against market at the close (item 17,
measurement); L2 line movement toward the model (item 17, slot). The
neutral-site home term is Mark's methodology call (a test at four or five
games a season cannot decide it). Drafts are in `memory/2026-10-04.md`;
shown to Mark before any registry file is written.

### Stage 39 - Ready for the playoffs (by mid-December)

1. The synthetic league as named scenarios with asserted outcomes, first:
   a tie, a cancelled game (NaN scores), a neutral site, a postponed game,
   playoff weeks 19 to 22 and an empty week 23, a Wednesday game, the
   week-12 Thanksgiving slate, the Friday Christmas games, Saturday games.
2. Round names and `game_type` carried into saved picks and the week
   stepper (week numbering already walks 19 to 22).
3. `check_build` and "every game started" semantics for 6, 4, 2 and 1-game
   weeks.
4. Ratings use regular-season plays only, so they freeze through the
   playoffs: disclose it, or register a change (Mark's call).
5. Playoff TV: sourced `data/nfl/tv/exceptions.json` entries in December, and a
   canary rule that they exist before week 19.
6. Bracket status in place of the simulation once `games_remaining == 0`.
7. A test that every scheduled game gets a status refresh after kickoff.

Item 1, first part (2026-10-04): `tests/test_league_scenarios.py` holds the
postponed and the cancelled game. Found while writing it: a cancelled game
reads "started" on the Week Board for the rest of the season, because
`weekend_refresh.game_status` has no state for a game that kicked off and
will never have a score. Not asserted either way; a "no result" state is
Mark's call, and it touches the weekend refresh, so after the 2026-10-08
lock in any case. **Mark's call (2026-10-05):** the card stays with a
"Cancelled" label; its pick is shown but not graded, and is left out of
every count and accuracy figure. Built after the lock.

Items 2 (the week stepper's half: weeks 19 to 22 named by their round
from 2021), 3 and 7 (2026-10-09 overnight, #360). Item 7 found that
Friday games (Black Friday, Christmas) wait up to two days for a status
refresh: no slot runs between Friday 05:17 and Sunday 21:47 UTC; a
Saturday cron-job.org slot would close it (Mark's account). Left: item
2's `game_type` in saved picks, item 1's other scenarios, 5 (December),
6, and 4 (Mark's call).

### Stage 40 - Season turnover (January)

`docs/season-turnover.md` and `tasks.py turnover` (item 7); the 2026
forward test archived as `experiments/nfl/forward-2026/` with a Model Lab row
(item 9); the "season not started" state (10); My Picks per season (11);
the season in links and routes (12); whether R4's drift sample resets per
season or per `MODEL_VERSION`, decided before week 1; C1, L1 and L2 run
before the turnover.

### Stage 41 - Operations and releases

1. (Moved to Stage 42, item 1.)
2. Booth's run fails when its prose header and verdict block disagree (28
   of 322 reports did).
3. `tasks.py release`: a GitHub Release per `MODEL_VERSION` from
   `VERSION_HISTORY` (Mark: yes, 2026-10-04).
4. A "last 30 runs" table on Checking the AI's work, built from the public
   Actions API at page build, not a file every workflow commits.
5. Per-source reachability in the canary. Locking on a cached schedule is
   declined: the cached spread would silently change Model B's input.
6. A designed two-letter team tile shown beside today's fallback (the logo
   canary is declined: CI already proves the page works with ESPN blocked).
7. `data_provenance` in each saved pick.

**Order:** Stage 36 now (items 6 and 7 as noted); Stage 42 next (Mark
called the delays significant); Stage 38's drafts to Mark; Stage 37 after
the 2026-10-08 lock; Stage 21 when week 5 is graded; Stage 44 after 42,
then Stage 43; Stage 39 before December; Stage 41 when a week has slack;
Stage 40 in January. Items 18 to 21 and the audience switcher's rendered
options go to Stage 22.

### Stage 42 - On-time runs (Mark, 2026-10-04)

Mark: "preferably no delay at all", and the delays are significant.

GitHub's `schedule:` trigger is best-effort. Runs here started on time
until 2026-09-22 and 3.5 to 6.5 hours late since; `workflow_dispatch` runs
started within seconds throughout (2026-09-29). Nothing in Stages 36 to 41
prevented the delay, so this stage replaces the trigger, not the runner.

1. Every scheduled workflow records its start delay (cron time against
   `run_started_at`) in its summary, and warns at 7 hours (`LOCK_SLACK` is
   8). This was Stage 41 item 1.
2. cron-job.org (Mark's pick: a web page, nothing to deploy) sends
   `workflow_dispatch` for the Weekly update, the three weekend refreshes,
   the canary and the nightly mutation slice at their cron times. A
   fine-grained token for this repository only, Actions read and write,
   with an expiry; Mark creates it and the cron-job.org account, walked
   through step by step.
3. GitHub's own cron stays as the fallback. A `concurrency` group per
   workflow so the dispatch and a late cron run never overlap, and a test
   that a second run of the same slot changes nothing (a locked week is
   never rewritten; a refresh with nothing new commits nothing).
4. A missed dispatch is seen: cron-job.org's failure e-mail when GitHub
   refuses a request (an expired token, say), and item 1's delay line on
   the run that did start.
5. After four on-time weeks, `LOCK_SLACK` is revisited (Mark's call).

Item 1 done (2026-10-09 overnight, #358): `src/core/start_delay.py`, a
"Record the start delay" step in every scheduled workflow, warning at
seven hours late.

### Stage 43 - Spotter, the visual inspector (Mark, 2026-10-04)

A third agent, beside Scout and Booth. On every PR that changes the page
(`scout_preflight.page_files()`), Spotter builds the page, screenshots the
pages the diff touches at 390 and 1280 px in both themes, attaches the
images to the PR, and reads them against the repository's visual rules.
"Render it and look at it" stops being a process note.
1. Design and permissions: read and comment only, stated as Booth's are.
2. The screenshot job in CI, on the Playwright already in browser checks.
3. Spotter's prompt and its protocol file.
4. A fixture PR with a planted visual defect Spotter must catch, run like
   Booth's regression suite.
5. Booth cites Spotter's images instead of marking a visual claim
   UNVERIFIABLE.

### Stage 44 - Line Judge, the run watcher (Mark, 2026-10-04)

A fourth agent. After every scheduled run (Weekly update, weekend
refresh, canary, mutation slice) Line Judge reads the run's summary and
what it committed, and says whether it did the right thing: started on
time (Stage 42's delay line), locked before the first kickoff, every game
on the page, the drift report present. A run that went green and did the
wrong thing gets a diagnosed issue through `src/core/alerts.py`.
1. What "right" means for each workflow, written as checks; most become
   plain tests or scripts, and the agent explains what they find.
2. Triggered on `workflow_run` completion.
3. Issue wording and de-duplication through the existing alerts.
4. A planted bad run in the synthetic league that it must flag.
5. A weekly one-line digest.
After Stage 42, whose delay record it reads.
