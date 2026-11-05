# Operations

How to run Sportalytics, what runs on its own, and what to do when something breaks. Moved out of the
README, which now holds what a first-time reader needs (Stage 89 item 5); nothing here was shortened.

## When an alert issue opens

Every unattended job opens an issue when it fails, under a fixed title, and
comments on it instead of opening a second one while it is open
(`src/core/alerts.py`). A job's failure issue closes itself when a later run of
the same job succeeds. What each title means and what to do:

| Issue title | What happened | What to do |
|---|---|---|
| `NHL: daily run failed`, `NBA: daily run failed` | The day sport's run crashed. Any picks it saved before the crash are in the artifact `<sport>-daily-<run id>` on that run (predictions, results and data), which the body names. | Download the artifact and commit its picks **only if the first of their games has not started**; a pick on `main` after its start is not a prediction. Past that, leave them out: the next run marks those games missed. Then fix the cause; the next successful run closes the issue. |
| `NFL: Weekly update failed` | The Tuesday or Thursday run that grades, refreshes and locks failed. | Read the run's log and fix the cause. If the week had not locked yet, a run dispatched by hand before its first kickoff can still serve the slot (a dispatched run serves a slot within twelve hours, `src/core/start_delay.py`); a locked week is never re-locked. |
| `NFL: Weekly update slot guard failed` | The step that decides whether this run serves a slot could not decide. | Read the guard's note in the run summary; dispatch the workflow by hand if the slot was not served. |
| `NFL: Weekend refresh failed` | The refresh of game status, scores and lines failed. It never touches a saved pick. | Nothing is lost; fix the cause. The next refresh or Weekly update catches up. |
| `NHL: the daily run could not read an input`, `NBA: ...` | A source (odds, goalies, rosters, injuries) could not be read. The picks were still saved, each saying what it went without. | Nothing to redo: a saved pick is never redone. Check the source before the next run; if it changed shape, the canary will usually say so too. |
| `NHL: a game started with no saved pick`, `NBA: ...` | A game's start passed with no pick saved. | It cannot be made now. Find why: a run that started late (see the run's start delay), a failed run, or a schedule change. |
| `NHL: a daily run slot went missing`, `NBA: ...` | The page build (`src/site/missed_slots.py`, on every push to main) found the sport's schedule file older than yesterday, or a game that started in the last 36 hours with no saved pick and is not postponed or cancelled: usually a daily run that never started. The page is still published. | Check that day's daily runs and the cron-job.org job; dispatch the daily run by hand if the next slate has not locked. A game that has started cannot get a pick. The next page build that finds nothing missing closes the issue. |
| `NHL: drift check flagged`, `NBA: drift check flagged`, `Model drift detected` (NFL) | Live Model A log loss is significantly above its backtest at a registered look. | A reason to look, not proof that something broke: read `results/<sport>/drift_<season>.json` and the inputs the picks recorded. Nothing changes on its own. |
| `... Line Judge found ... left something wrong` | Line Judge's checks of what a run left behind found a problem; an agent's diagnosis follows as a comment. | Read the diagnosis, then fix the data or the code by pull request, before the next lock if picks are affected. |
| `NFL: Nightly canary failing`, `NHL: nightly canary failing`, `NBA: nightly canary failing`, `NBA: <source> failing in the nightly canary` | The nightly dry run of a sport's data path broke, usually a source changing shape. | Fix the reader before the next daily or weekly run; the canary closes the issue when it passes. |
| `cron-job.org did not start a scheduled run` | A slot that cron-job.org should have started was started only by GitHub's own, later cron. | Check the cron-job.org job for that workflow. GitHub's cron is the fallback, and it can run hours late. |
| `Pages: the site was not published` | The site build or the deploy failed, so the live site is still the last one published. | Read the run named in the issue and fix the cause; the next deploy that succeeds closes the issue. Picks and results are on main either way: only the page is behind. |
| `NFL: QB override watch failed` | The workflow that opens the "override waiting to merge" issue failed on a QB override pull request, so that issue may not have been opened or closed. | Look at the pull request named in the issue before Thursday's lock: only an override merged to main is used. The next watch run that succeeds closes the issue. |
| `Browser checks failing on main` | The page checks in Chromium failed on `main`. | Read the failed check's output; it says which page, width and rule. |
| `Nightly mutation slice failing` | A mutation case was not caught by the test it names. | Replay the night with the seed in the issue (`python tests/mutation/runner.py --sample 30 --seed <seed>`), then fix the guard or the case. |
| `Nightly shuffled suite failing` | A test passes in file order and fails in a shuffled order: it depends on what ran before it. | Replay with the seed in the issue and remove the dependence. |
| `Dependency audit found known vulnerabilities`, `Dependency audit could not run` | pip-audit found a known vulnerability in what CI installs, or could not run. | Moving a pin is a decision (see the header of `requirements.txt`): update it, or accept it with a review date in `.github/accepted-vulnerabilities.json`. |
| `Line Judge weekly digest failing` | Monday's digest of Line Judge's verdicts could not be written. | Read the run; the digest itself posts to the issue `Line Judge weekly digest`. |

A Booth audit that fails (it posted no report, or its report disagrees with
itself) opens its own issue on the pull request's behalf; re-run the audit
once, and if it fails again, read why before editing anything.

## Repo layout
```
docs/
  architecture.md       -- the whole system on one diagram
  case-studies/         -- write-ups of real problems and how they were found
  lessons-learned.md    -- what it all taught, each lesson with its source
src/core/               -- shared by every sport (decision record 0006)
  sport.py              -- the interface a sport module satisfies
  isolation.py          -- the rules that keep sports apart, as checks
  model_specs.py        -- the models, written down once, and the walk-forward evaluation
  template_parts.py     -- joins the dashboard template's parts into one page
src/sports/nfl/         -- the NFL: what its scheduled workflows and the page build run
  config.py             -- every tuned constant, with the backtest that justified it
  data_loader.py        -- pulls fresh nflverse data automatically (no manual CSVs)
  ratings_engine.py     -- team + QB rating computation (leak-free, recency-weighted)
  weekly_update.py      -- main entrypoint: generates next week's predictions
  grade_predictions.py  -- grades a completed week against actual results
  generate_dashboard.py -- builds index.html from the template plus data/nfl/
src/sports/nfl/research/ -- run by hand: backtests, experiments, re-derived figures
  backtest.py           -- the holdout backtest behind the table above
  calibration.py        -- reliability of the stated probabilities
src/sports/nhl/         -- the NHL: schedule, history, model, lock rule, daily run, pages
src/sports/nba/         -- the NBA, the NHL's shape again: live from 2026-10-20
src/site/               -- the home page and the site build that joins every sport's pages
src/agents/             -- Booth, Scout and the session gates
  scout_preflight.py    -- checks a branch against the project's own rules
  session_wrapup.py     -- end-of-session checks (suite count, unpushed work, docs)
src/dashboard/          -- the dashboard template, in parts, with data injected at build
  page.html             -- the document; includes the three parts below
  styles.css, body.html, app.js -- stylesheet, markup and script
predictions/nfl/        -- one JSON file per week, saved BEFORE kickoff, never edited
results/nfl/            -- graded predictions, builds the season accuracy record
data/nfl/               -- generated inputs the dashboard reads
data/                   -- shared: Booth's audit log
assets/fonts/           -- the self-hosted Plus Jakarta Sans files and their licence
tests/                  -- the suite, plus tests/mutation/ (tests for the tests)
.github/workflows/      -- CI: tests, weekly update, backtest, dashboard, Booth
```

`index.html` and `dist/` are **build outputs and are not in the repository.**
Both are produced by `src/sports/nfl/generate_dashboard.py`; GitHub Pages publishes them
from a CI build, and the test suite builds them itself via the root
`conftest.py`. To see the dashboard locally, run the generator.

## Manual usage
```bash
pip install -r requirements.txt
python -m src.sports.nfl.weekly_update --season 2026 --week 2
# ... after that week's games finish ...
python -m src.sports.nfl.grade_predictions --season 2026 --week 2
# rebuild the dashboard from whatever is in data/ and results/
python -m src.sports.nfl.generate_dashboard
```

### Settings and the rules the code enforces

The environment variables the code reads, all optional:

| Variable | What it does | Who sets it |
|---|---|---|
| `NHL_CACHE` | A folder for finished NHL seasons' schedules and raw box scores, read from disk instead of refetched. The current season is never cached. | Anyone re-reading the NHL's history (`python -m src.sports.nhl.history`). The daily run and the canary never set it. |
| `NBA_CACHE` | A folder for finished NBA seasons' schedules and raw box scores, read from disk instead of refetched. The current season is never cached. | Anyone re-reading the NBA's history (`python -m src.sports.nba.history`, a later branch). Nothing scheduled sets it. |
| `NFL_PBP_CACHE` | A folder for finished seasons of play-by-play, read from disk instead of refetched. The current season is always fetched. | Only the nightly canary. The weekly run never does: the run that makes picks always fetches fresh. |
| `STAGE5_CACHE` | Where the Stage 5 experiment runner keeps its game table. Defaults to nfl-cache/stage5 beside the repository folder. | Anyone re-running a registered Stage 5 question. |
| `STAGE6_CACHE` | The same for the Stage 6 data-source runner (nfl-cache/stage6). | Anyone re-running Stage 6. |
| `GITHUB_TOKEN` | Read by `src/sports/nfl/recent_runs.py` for GitHub's Actions API; without it the anonymous limit applies (60 calls an hour, four used per read). | The deploy job, with its own token. |
| `GITHUB_SHA` | Read by `src/core/provenance.py`: the commit a day sport's daily run checked out, saved on each pick as `code_commit` (Stage 95 item 39). Unset, it is git's HEAD, or none outside a checkout. | GitHub Actions, on every runner. |
| `GH_TOKEN` | Read by `src/core/job_logs.py`, which fetches a failed run's job logs for the Line Judge's diagnosis; without it the fetch stops with an error. It sends the token to GitHub's API only, never to the log's signed link. | The diagnose workflow, with the run's own read-only token. |
| `GITHUB_OUTPUT` | Read by `src/sports/nfl/slot_guard.py`: where it writes `run` and `slot` for the Weekly update's later steps. Unset, it prints its decision and writes nothing. | GitHub Actions, on every runner. |
| `GITHUB_STEP_SUMMARY` | Read by `src/sports/nfl/slot_guard.py`: a skipped slot is noted in the run's summary. Read by `src/core/start_delay.py`: each scheduled run's start delay is written there. Unset, nothing is noted. | GitHub Actions, on every runner. |
| `GITHUB_EVENT_NAME` | Read by `src/core/start_delay.py`: a run GitHub's cron started always serves a slot; a dispatched one serves it only within twelve hours. Unset, the run is measured as dispatched. | GitHub Actions, on every runner. |
| `CRON_SCHEDULE` | Read by `src/core/start_delay.py`: the cron line that fired a scheduled run (the NHL and NBA daily workflows pass `github.event.schedule`), so a late copy of one slot is measured against that slot, not the next. Unset or empty, the latest slot of any line is used. | The NHL and NBA daily workflows' start-delay step. |
| `GITHUB_ACTIONS` | Read by `src/sports/nba/data_probe.py`: on a runner it adds one notice line summing up every source, readable from the run's annotations. Unset, the probe only prints. | GitHub Actions, on every runner. |
| `GITHUB_RUN_ID` | Read by `src/sports/nfl/slot_guard.py`: stored with the slot it marks as served. Unset, the run id is stored as null. | GitHub Actions, on every runner. |

Four rules that live in the code rather than in any one document:

- **A saved prediction is permanent.** `src/sports/nfl/weekly_update.py` will not
  overwrite `predictions/nfl/<season>_week<N>.json`; it warns and writes nothing. That
  refusal is what makes "saved before kickoff" a claim anyone can check.
- **The next week is worked out, not configured.** With no `--week`, the run
  takes one past the latest week saved or recorded as skipped, which is how
  it walks through the playoffs unattended.
- **The test suite and mutation runs rewrite `index.html`.** Several tests
  build the page, and a mutation run can build it with a mutation applied, so
  rebuild it (`python -m src.sports.nfl.generate_dashboard`) right before looking at it.
- **CLAUDE.md's `Suite: **N passing**` line is read by software.**
  `src/agents/session_wrapup.py` and `src/agents/session_start.py` parse that exact shape;
  reword it and they report the line missing.

`tests/test_readme_accuracy.py` fails if the code reads an environment
variable this table does not name.

Running the tests needs Python 3.11 (as `.python-version` says) and, for
the tests that run the dashboard's own JavaScript, node 24; without node
those tests skip rather than fail. From the repository root:
```bash
pip install -r requirements.txt -r requirements-dev.txt
ruff check .
python -m pytest
```
The mutation corpus runs separately, one case at a time or a sample of
it; a full run takes well over an hour:
```bash
python tests/mutation/runner.py --id <case id>
python tests/mutation/runner.py --sample 30 --seed 20260929
```
Every one of these, and the page build, the browser checks and the
end-of-session gate, is also a task in `tasks.py`, which runs exactly what CI
runs (`tests/test_tasks.py` holds each task to its workflow). `python
tasks.py` lists them; `python tasks.py check` is lint plus the suite.
`python tasks.py quick` is the suite without the twelve tests marked `slow`
(nine drive a whole daily run, two re-derive a saved pick from the whole
history, one drives the NHL's run on a renamed odds payload), for
iterating; CI and the Suite line still run every test.

## Automating this with Claude Code Routines

The weekly pipeline itself needs no Claude at all. The repository's
**Weekly update** workflow (`.github/workflows/nfl-weekly-update.yml`) runs on
GitHub every Tuesday and Thursday at 11:00 UTC. It grades finished
weeks, refreshes the ratings, playoff odds and line archive, and locks the
next week's picks at the right run: Thursday usually, and Tuesday for a
week with an earlier game (Thanksgiving, a Wednesday game). See
`decide_lock` in `src/sports/nfl/weekly_update.py`. Its data commit then triggers the
site rebuild.

What a routine adds is the one thing a script can't do: read the news.
Picks use the starter listed on nflverse's schedule, and that list can lag
the news. On 2026-09-22 it still listed two starters who had already been
ruled out. A sourced override in `data/nfl/qb_overrides/<season>_week<N>.json`
takes precedence over it.

Setup (verified against current Claude Code docs,
code.claude.com/docs/en/routines):

1. **Push this repo to GitHub.** Routines clone from GitHub on every run.
2. **Connect GitHub to Claude Code**, if you haven't already: run
   `/web-setup` inside Claude Code (this is separate from installing the
   GitHub App -- both are required for the routine to actually trigger).
3. **Create the routine** on the web at `claude.ai/code/routines` -> New
   routine, or with `/schedule` in the Claude Code CLI.
4. **Schedule it Monday and Wednesday evening** (`0 22 * * 1,3`, UTC), so
   a PR is waiting before each scheduled lock: Wednesday's before
   Thursday's, Monday's before a Tuesday lock.
5. **Make sure the routine's cloud environment has network access
   enabled** -- it needs nflverse's GitHub-hosted data and web search for
   QB news. This is a setting on the routine's environment.
6. **Give it narrow, unattended-safe instructions.** The routine this repo
   runs, "Weekly QB override research", is told to:
   - find the next week to predict with `determine_next_week`;
   - web-search starting-QB news for every team playing that week;
   - record a team only when a credible source says the listed starter
     won't start, or names another starter;
   - write the override file as a list of
     `{"team", "player_id", "player_name", "source"}`, where `player_id`
     is the GSIS id (00-0000000) and `source` is a link, and validate it
     with `load_qb_overrides`;
   - open a PR titled "QB overrides: <season> week N", or stop with one
     line if nothing needs overriding.

   It must NOT run `src/sports/nfl/weekly_update.py`, `src/sports/nfl/grade_predictions.py` or
   `src/sports/nfl/generate_dashboard.py`. The workflow owns those, and a second writer of
   saved predictions would be a second way to break a lock.
7. **Merge the override PR before the lock.** On a normal week, that means
   before Thursday 11:00 UTC. An override merged after the lock changes
   nothing, because a locked week is final.

## What this does NOT automate yet
- Confirming genuinely uncertain starting QB situations (e.g. a team
  benching its starter) -- the routine above researches them and opens a
  PR, but a person still decides whether to merge it.
- Hyperparameters (alpha, half-life, QB shrinkage) are NOT re-tuned
  automatically each week -- they're fit once via backtest and left fixed
  in `src/sports/nfl/config.py`. Re-running the full backtest sweep weekly would be
  needlessly expensive; do it manually every few weeks or once per season.
- The model does not beat the betting market on its own. Model B only
  matches it, within noise. Treating Model A as an edge against a market
  price would be a misreading of the table above.
