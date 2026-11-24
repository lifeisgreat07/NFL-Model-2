# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history; history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-11-24 (session 1123: Monday 2026-11-23 with Mark, then overnight with Mark asleep; #809 to #827)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked figure, split five ways by `tests/suite_classes.json` (`session_wrapup --suite-line` writes it). NFL in `src/sports/nfl/`, shared modules in `src/core/`.
**Sportalytics** (Stage 67) is live: home `/`, NFL `/nfl/` (Model **v2.6**), NHL `/nhl/`, NBA `/nba/` (picks saved twice a day). **MLB's pages are all built, tested and unpublished** (Stage 100: board #808, standings odds #809, Standings #815, Power Ratings #818, Model Lab and Methodology #821, Teams and What's Changed #823, Season Accuracy and Checking the AI's work #824, the home card #813, the read-set test #825; `build.SPORTS` does not list MLB, and the home card stays dark until it does). March Madness (Stage 103) is built; its page and card appear only from the lock to 15 April.

**Booth has 35 minutes and 210 turns (#810)**, and still sometimes needs them; audits run one at a time. **Run tests has 35 minutes.** The six `actions/*` are on their newest majors (#822).

**Merge rule (Mark):** Booth SAFE TO MERGE with 0 discrepancies, audited head = PR head, every check green; or (Mark, 2026-11-23) NEEDS HUMAN REVIEW with 0 discrepancies, every check green, and the only unverifiable claims the full-suite count and/or the archive-built mutation-scope list. Anything else, a second Booth timeout, and any PR that changes booth-pr-audit.yml (Scout's auditor-edits rule) go to Mark. `merge_item.py PR WT_NAME BRANCH "Title"`.
**At the final head, before opening:** prechecks (ruff, the three mypy steps at run-tests.yml lines 79, 84, 89), every figure and mutation case by exact id, the suite (the session archive's prep and go scripts; CLAUDE.local.md has the paths). A body may be corrected after opening (the session archive's set-body script, which re-triggers Booth).
**Mutation scope = every case whose own target or tests file the branch changes** (scope_by_target.py; full_prep.ps1 -Scope). Name the cases a scoped file holds but the scope leaves out (the session archive's scope-left script), or Booth counts the whole file and calls it a discrepancy.
**Rules on main that bind every branch:** every workflow installs with `pip install --require-hashes -r requirements.lock`;
every python or pip step of an alerting scheduled job has its own `timeout-minutes`; src/core, src/site, src/sports/nhl,
src/sports/nba and src/sports/mlb pass `mypy --strict`; **a new test file needs a line in `tests/suite_classes.json`**, and two
branches adding lines beside each other conflict there, so merge main before opening; **no test skips on a missing node by
hand**: `require_tool('node')`; **every mutation case names its real file**; **a new page meets every page guard at once**
(CSP `PAGES`, `SPORT_SHEETS`, Spotter's `RULES` and spotter.yml paths, the day boards' three-way copy guard); **a title a
workflow closes with `--resolve` is raised in the same file** (`tests/test_alerts_raised.py`, #814); **tasks.py's
browser-check task runs what browser-checks.yml runs, in order** (`tests/test_tasks.py`).

**Single next action:** Mark decides the three PRs waiting on him: #826 (MLB browser checks, the last of Stage 100), #827 (#582's Booth post job, brought current) and the claude-code-action 1.0.276 PR. Then Stage 101.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| #826 MLB browser checks (Stage 100 item 4) | 0 discrepancies, all green; NEEDS HUMAN REVIEW because Booth's runner cannot run Chromium (outside the merge rule) | Mark merges |
| #827 Booth post job (Stage 82 item 4; #582 re-applied on main) | Opened overnight; changes booth-pr-audit.yml | Mark reads the `post` job and merges; then #582 closes and Stage 82 item 5 |
| claude-code-action 1.0.236 to 1.0.276 (branch claude-code-action-1-0-276, last of #683) | Prepped or opened overnight; changes booth-pr-audit.yml | Mark merges (he chose to decide it himself) |
| MLB Stage 99 (model and backtest) | History, tuning, market, confirmation code (#728-#735) | Retrosheet's 2026 log (gl2026.zip not out on 2026-11-23), then `python -m src.sports.mlb.backtest confirm`, once |
| MLB Stage 101 | Not started: forward-test registration, daily run writing the schedule, standings, ratings and pick files, canary, going live (add 'mlb' to `build.SPORTS`, the strip's names, the home layout of four cards) | Opening Day 2027 (Thu Mar 25) |
| v2 and v3 shadows (Stage 95, Stage 105) | Writers live | Decided once after the 2026 regular season |
| NCAAM Stage 103 | Everything built | The lock between Selection Sunday and the First Four |
| NFL week 12 | QB overrides #816 merged themselves (AUTO_MERGE_OVERRIDES is on); Tuesday's run locks all 16 games | The 07:30 ET check-in confirms it ran |
| Stage 88 item 1 (actions): one dispatch of each writer | Not done | Mark (dispatching the Weekly update can lock a week) |
| Open alerts | #769, #671 (NHL), #541 (Line Judge digest, now retried on a 5xx, #811) | Mark |

## Known and deliberately not fixed


- **34 saved live picks were fitted on games of their own slate day** (5 NBA, 29 NHL; 26 earlier NHL picks
  cannot be checked). Saved picks are never rewritten; s85d lists them in both registrations and fits per day.
- **Booth's post job needs the Write tool**: told to write a file without it, Booth ends with permission denials
  and no report (#578, #580). Keep Write in `--allowedTools` while the report is a file.
- **Force-killing the mutation runner leaves its mutation in place**, and editing a worktree while its suite runs
  tests no commit. Let both finish.
- **Spotter's reading job takes its protocol and its checker from the pull request's base**, so it skips (and passes) on a base that predates them.
- **Spotter's clean-control key is looser than first written**: a problem is allowed only where its bullet says the base picture shows it too (the real reading listed base-present problems). Disclosed in the fixture and in #535; Mark has not yet ruled on it. **Spotter's head and base pictures can differ by a few antialiased pixels**; no pixel comparison is made on purpose. Both checkouts take full history because the NFL page reads the git log.
- **A browser check that assumes the pre-season page ages out on opening night.** `tests/browser/pre_opening.py` rewinds a built NBA page (no picks, every game scheduled); the countdown, rows and accuracy checks read it (#536). A new check about a state the real page has left should do the same.
- **GitHub's cron starts hours late**; cron-job.org starts on time. Every Weekly update slot runs once (slot guard).
- **Booth's prose can disagree with its own verdict block** (#286 ... #433). Re-run once; red again for the same reason, merge and log it.
- **Booth can say NEEDS HUMAN REVIEW on an all-green PR.** When the only unverifiable claims are the full-suite count and/or the archive-built mutation-scope list, the merge rule above covers it (Mark, 2026-11-23). When a browser render is among them (Booth's runner has no Chromium, #826), it is Mark's call, not a re-run.
- **Booth's runner has no Playwright**, so a Chromium claim in a PR body is UNVERIFIABLE there. Mark's PC has none either; the container has Playwright and Chromium and can run a `tests/browser` check, but its Python cannot install the repo's pinned pandas.
- **Scout's body check ties any number near a test file's name to that file's whole count**, and reads `--id "glob"` as a mutation scope: quote the file's total, and run mutation cases by exact id.
- **The file bridge can report a write and keep the old file**: commit to a new name, copy into place, compare hashes. **A PowerShell `>` redirect writes UTF-16**, which `git apply` refuses: write patches with `git format-patch -o`, or a Python script written with the file tool.
- **The drift check re-tests a growing sample every week**, so it will sometimes flag by chance.
- **A failed Thursday run leaves Thursday night's game unpicked** unless dispatched by hand that day.
- **GitHub moves `ubuntu-latest` to Ubuntu 26 from 2026-10-19; nothing here follows it.** All 35 `runs-on` are `ubuntu-24.04`, held by `tests/test_runner_image.py`. Moving is a deliberate change: run the suite and one of each writer on `ubuntu-26.04` first, then change WANT and every workflow together.
- **Mark's PC runs on Eastern time and GitHub's runners on UTC**: a clock-reading test pins `TZ` (#501), and a guard for an ET clock runs node with `TZ` far from ET (Stage 77 item 30). **Windows Python ships no tz database**: `ZoneInfo('America/New_York')` fails at import on Mark's PC and passes on Linux CI. Read Eastern time through pandas, as `src/sports/nfl/tv_channels.py` does.
- **Mark's PC checks files out as CRLF (autocrlf)**: a test that builds CRLF by replacing `\n` makes `\r\r\n`; write both forms from LF yourself (#538).
- **A parametrize over a page script needs `ids=`**: unnamed, the script is the test id, and Windows refuses an environment variable over 32,767 characters (items 57, 61).
- **The plain-language guard reads only `RENDERERS`**: add each new markup function with its page; a top-level literal is charged to the function above it (items 28, 31).
- **A test that calls a writer's `main()` writes into the real `data/` on a runner** when the code records only under
  `GITHUB_ACTIONS=true` (#661). Such a test chdirs to its tmp folder and pins the runner variables; reproduce with
  `GITHUB_ACTIONS=true` set on the PC.
- **One process per worktree**: mutation cases run while that worktree's suite runs fail the suite.
- **Scout reads any "N passed" in a body as the whole suite's count, "N test" in a commit message as a suite count,
  and `--durations=0 tests/test_x.py` as 0 for that file**: say "all N of their tests pass", keep counts out of commits,
  put flags after the files.
- **The anonymous GitHub API allows 60 requests an hour**: poll Booth with the session archive's authenticated
  `scratch-nba/pr_runs.py PR --wait SECONDS`, not every 15 s anonymously.
- **The NBA daily run's end-to-end test** (`tests/test_daily_end_to_end.py::test_the_nba_daily_run_end_to_end`) takes about 3 minutes alone on Mark's PC and sometimes 15 or more inside the full suite (CPU-bound ridge solves in `src/core/day_ratings.py`). A prep stuck at "5%" is this test, not a hang; CI is unaffected.
- **A page joining MLB's More sheet changes `OVERFLOW_PAGES`**, which `mlb-lab-page-method-not-in-more` anchors on: re-anchor it with the same mutation.
- **Scout rejects "on screen" without an attached image** (its visual-evidence rule): say what a check reported instead.
