# Where everything is

A map, not a description. Answers "which file do I open for X" so a session
does not have to grep the repository to find out what it already built.

Updated when the structure changes, not every session.

---

## The four documents, and which job each has

Splitting these was the point: one file was doing all four jobs and going stale
in the parts that changed fastest.

| File | Holds | Rewritten |
|---|---|---|
| `docs/context.md` | What is true TODAY: open branches, the next action | Every session |
| `docs/index.md` | This map | When structure changes |
| `CLAUDE.md` | What stays true for months: methodology, findings, environment, the PR loop | When a rule changes |
| `docs/traps.md` | Every trap that has actually bitten, and the durable shape of each | When something surprises a session |
| `docs/stage-history.md` | Every stage, finished or planned, under its frozen number | When a stage is planned or finished |
| `memory/` | One file per session: what happened and why | Appended, never edited |

**Every command in one place:** `python tasks.py` lists the tasks (test,
lint, build, browser checks, the mutation slice, the wrap-up), each held
to the workflow it copies by `tests/test_tasks.py`.

**Session start:** `python -m src.agents.session_start` — it computes the state rather
than restating it, and cross-checks what `docs/context.md` claims against git.
Then read `docs/context.md`, then CLAUDE.md, then `docs/traps.md` before a
PR, a measurement or a mutation run. Reach for `memory/` only to answer
"why did we decide that".

**Session end:** `python -m src.agents.session_wrapup`, then rewrite `docs/context.md`
and add a `memory/` entry.

Neither script fetches pull-request state — there is no `gh` CLI on this
machine, and a guessed PR status would be exactly the unverified claim this
project is built to avoid. Check open PRs on GitHub yourself.

## The model

| Path | What it does |
|---|---|
| `src/pipeline/config.py` | Constants and `VERSION_HISTORY`. The changelog page renders from this object, so the page cannot drift from the constant. |
| `src/pipeline/ratings_engine.py` | Opponent-adjusted ridge ratings and QB ratings. |
| `src/pipeline/weekly_update.py` | The weekly routine: predictions, grading, playoff odds. |
| `src/research/calibration.py` | Backtest calibration. Run deliberately, not per build; takes minutes. |
| `src/research/compare_data_sources.py` | Run by hand before flipping `USE_NFLREADPY` in `src/pipeline/data_loader.py`: checks the two loaders agree on values (the loader's own `__main__` checks the columns). Not dead, though the 2026-09-29 re-audit read it so. |
| `src/research/backfill_game_dates.py` | Run by hand: adds the schedule's `gameday`, `gametime_et` and `weekday` to prediction files saved before those fields existed, never changing an existing key; `--check` writes nothing. `tests/test_game_datetime_fields.py` names it as the repair when a file lacks them. |

## Stage 5: model experiments

| Path | What it does |
|---|---|
| `experiments/stage5/registry.json` | Every question Stage 5 asks, the rule that decides it, and the confirmatory budget. Committed before any answer. |
| `experiments/stage5/results/` | One file per answered question, with the numbers the label rests on. |
| `src/research/stage5_run.py` | `build` makes the feature table (and proves it matches production); `run <id>` answers one registered question. |
| `src/research/stage5_eval.py` | Walk-forward, paired bootstrap, the screen, the budget, and the forward-holdout refusal. |
| `src/research/stage5_data.py` | The game table: incumbent features plus every registered variant, including the three quarterback specs. |
| `src/research/kalman_ratings.py` | State-space team ratings (H7). |
| `src/research/stage5_residuals.py` | Descriptive only: where the live Model A loses log loss, by pre-chosen slice. Writes `experiments/stage5/residuals.json`. |
| `tests/test_stage5_published_numbers.py` | Every figure in `experiments/stage5/README.md` against the file it came from. |
| `tests/test_stage5_registry.py` | Registration before answer, labels recomputed, budget held, and the harness's own rules. |

## Stage 6: new data sources

| Path | What it does |
|---|---|
| `experiments/stage6/registry.json` | Every question Stage 6 asks (Next Gen Stats first), the order they may be asked in, and one confirmatory budget for the stage. Committed before any Next Gen Stats data was loaded. |
| `experiments/stage6/README.md` | The questions in plain words, and why the budget is five. |
| `tests/test_stage6_registry.py` | Registration before answer, labels recomputed, preconditions held, budget fixed and not overspent. |
| `src/research/stage6_run.py` | `build` loads play-by-play and Next Gen Stats and makes the inputs (and proves the game table matches production); `run <id>` answers one registered question. |
| `src/research/stage6_data.py` | Trailing values in the production QB rating's shape, qb_games, the N1 feature sets, weighted least squares, the cluster bootstrap and the screen rule. |
| `tests/test_stage6_data.py` | Trailing values against the production QB rating, no week reaching its own inputs, and the screen's arithmetic. |

## The dashboard

| Path | What it does |
|---|---|
| `src/dashboard/` | The whole site, as a template in parts: `src/dashboard/page.html` includes `src/dashboard/styles.css`, `src/dashboard/body.html` and `src/dashboard/app.js`. Placeholders like `__TEAMS_JSON__` are swapped at build time. |
| `src/pipeline/template_parts.py` | Joins the parts into the one template the generator fills; `read_template()` is how tests read it. |
| `src/pipeline/generate_dashboard.py` | Reads `data/`, fills the placeholders, writes `index.html`. |
| `conftest.py` | Repository root. Builds the page once per test session, because roughly a dozen tests read it and seven of them *skip* rather than fail when it is absent. |

`index.html` and `dist/` are build outputs and are **not tracked**. Pages
publishes them from a CI build; run `src/pipeline/generate_dashboard.py` to see them
locally. They were committed until Stage 8c phase 2, which is why several
notes elsewhere still describe them as files you can open in the repository.

## The agents

| Path | What it does |
|---|---|
| `src/agents/scout_preflight.py` | Checks a PR description against reality before it opens. |
| `src/agents/booth_verdict.py` | Parses the machine-readable verdict block out of a Booth report. |
| `src/agents/booth_fixture_runner.py` | Runs deliberately-bad PRs that Booth must catch. |
| `src/agents/collect_agent_log.py` | Turns Booth's audit comments into the data the reliability page renders. |
| `src/agents/session_start.py` | Orientation: branch state, branch list, what `docs/context.md` claims vs what git knows, suite count vs the documented one, and (unless `--offline`) the unattended jobs' last 36 hours, the QB routine's latest PR, open PRs and open issues from GitHub's public API. Never gates. |
| `src/agents/session_wrapup.py` | End-of-session checks. Mechanical ones plus a by-hand list. This one gates. |

## Case studies (Stage 7)

| Path | What it does |
|---|---|
| `docs/case-studies/` | One write-up per real problem, for a technical reader. `README.md` there is the index. |
| `src/research/measure_qb_leak.py` | Measures what the QB rating leak did to the backtest, on today's code. Writes `data/qb_leak_effect.json`. |
| `docs/architecture.md` | The whole system on one diagram, with the file behind each box. |
| `docs/decisions/README.md` | The decision records (Stage 49 item 22): one page per decision the rest rests on, with why, the cost and what would reopen it. |
| `docs/lessons-learned.md` | The lessons across all of it, each pointing at where it came from. Linked from "Checking the AI's work". |
| `tests/test_lessons_learned.py` | Every link, path and trap the lessons cite still exists, in the document each citation names. |
| `tests/test_case_studies.py` | Cards on "Checking the AI's work" against the files; every cited commit and quoted figure against its commit; measured figures against their data file. |

## The tests worth knowing about

| Path | What it guards |
|---|---|
| `tests/mutation/` | The mutation corpus. `python tests/mutation/runner.py` — a case must name the test it expects to catch it. |
| `tests/test_claude_md_freshness.py` | Every path and test CLAUDE.md, `docs/traps.md` and `docs/stage-history.md` name exists; stage headings are ordered and unique; CLAUDE.md holds no stage section, points at both files and stays under 450 lines. |
| `tests/test_plain_language.py` | Statistics vocabulary stays off the reader-facing pages. Reads the JavaScript, not just the markup. |
| `tests/test_workflow_docs.py` | These four documents stay honest — see it for what "honest" means here. |
| `tests/test_readme_accuracy.py` | README.md may not name a path that is not there, and its stated counts are compared against what they count. |
| `tests/test_wrapup_date_slack.py` | The wrap-up gate's date tolerance is one-directional — tomorrow passes, yesterday does not — and both directions are asserted. |
| `tests/test_generated_data_reaches_the_page.py` | A workflow that writes data the dashboard reads must also cause a rebuild. The collector wrote 44 audits to main and the page never changed. |

## Workflows

| Path | When it runs |
|---|---|
| `.github/workflows/booth-pr-audit.yml` | Every PR open, push and description edit. |
| `.github/workflows/booth-alert.yml` | After every Booth audit run. A failed or timed-out audit becomes an issue (`src/agents/booth_alert.py`, `src/pipeline/alerts.py`); cancelled and successful runs raise nothing. |
| `.github/workflows/nightly-canary.yml` | 06:00 UTC every night, and by hand. Runs the weekly data path without writing anything (`src/pipeline/canary.py`): the loads, the data-quality checks, nflverse's columns against `data/nflverse_schema.json` (`src/pipeline/schema_check.py`), and the shape of next week's nfl.com schedule page, the TV-channel source. A failure opens or comments on the issue "Nightly canary failing". |
| `.github/workflows/nightly-mutation.yml` | 06:30 UTC every night, and by hand. Runs 30 cases of the mutation corpus chosen by a seed that is the UTC date (`tests/mutation/runner.py --sample 30 --seed YYYYMMDD`), and writes the counts by status to the run's summary. Anything not caught by the test it names fails the run. Writes nothing to the repository. |
| `.github/workflows/nightly-random-order.yml` | 07:15 UTC every night, and by hand. The whole suite in a random order across all files, seeded by the UTC date (`--random-order-bucket=global --random-order-seed=YYYYMMDD`), so a test that depends on what ran before it fails. pytest-random-order is installed in this job only. A failure opens or comments on the issue "Nightly shuffled suite failing" with the replay command. Writes nothing. |
| `.github/workflows/weekly-update.yml` | The weekly routine. After grading it runs the drift check (`src/pipeline/drift_alert.py`), which opens the issue "Model drift detected" on a flag and never fails the run. Writes a summary to the run's page (`src/pipeline/weekly_summary.py`), then reads TV channels and team news in steps that cannot fail the run, and a failed run opens the issue "Weekly update failed". Commits predictions, results and data, after rebasing onto main so a merge during the run cannot make the push fail — **not** the dashboard, which the Pages deploy below rebuilds from that push. |
| `.github/workflows/weekend-refresh.yml` | Friday 05:17, Sunday 21:47 and Monday 05:37 UTC, and by hand. Runs `src/pipeline/weekend_refresh.py`, which writes game status, final scores and the latest line for each locked, not yet fully graded week to `data/game_status/`, appends the same weeks' spreads to `data/line_history/` (Stage 33 item 23, so the archive reaches the closing line), and commits those two directories only -- never a pick or a grade. It then reads TV channels (`src/pipeline/tv_channels.py --pending`) and team news (`src/pipeline/team_news.py --pending`) and commits their week files too, each in a step that cannot fail the run. It rebases onto main just before committing, so a merge during the run cannot lose its snapshot. A failure opens the issue "Weekend refresh failed". |
| `.github/workflows/booth-regression.yml` | Manual dispatch only. |
| `.github/workflows/run-tests.yml` | The suite, on push and PR. |
| `.github/workflows/browser-checks.yml` | PRs touching the page's inputs, and pushes to main. Builds the page and runs `tests/browser/check_page.py` over every page at six widths in Chromium, after `--self-test` proves each rule can fail. Playwright and axe-core are installed in the runner, pinned, and never committed. |
| `.github/workflows/nhl-daily.yml` | 14:00 and 21:00 UTC, and by hand. The NHL's daily run (`src/sports/nhl/daily.py`): saves each game's pick before it starts, grades final games, runs the drift check, and commits only the NHL's own folders. Alerts "NHL: daily run failed" and "NHL: drift check flagged" (Stage 58). |
| `.github/workflows/nhl-canary.yml` | 06:40 UTC, and by hand. Every read the NHL's daily run makes (`src/sports/nhl/canary.py`); writes nothing. Alerts "NHL: nightly canary failing" (Stage 58). |
| `.github/workflows/nhl-data-probe.yml` | PRs touching it, and by hand. Runs `src/sports/nhl/data_probe.py`: can GitHub's runners read every source the NHL's go/no-go relies on (the league's schedule, play-by-play, box score and live odds, ESPN's past odds, the SportsDataverse fallback, Daily Faceoff's goalies), each in the shape a later stage needs? Writes nothing (Stage 51; `docs/nhl-data.md`). |
| `.github/workflows/nfl-schedule-probe.yml` | PRs touching it, and by hand. Runs `src/pipeline/nfl_schedule_probe.py`: can GitHub's runners read nfl.com's by-week schedule, and is every game complete and from the week asked for? Writes nothing. |
| `.github/workflows/collect-agent-log.yml` | Manual dispatch, and each pull request merged into main, to record what the agents actually did. |
| `.github/workflows/run-backtest.yml` | The backtest, deliberately not on every push. |
| `.github/workflows/releases.yml` | A GitHub Release for each tagged model version, by hand (Stage 41) or when a `v*` tag is pushed (Stage 49). |
| `.github/workflows/scout-preflight.yml` | Every PR open, push and description edit. Runs `src/agents/scout_preflight.py` against the PR description so a wrong count is caught before Booth spends an audit on it. It existed as a manual tool from PR #26 and nothing ran it; the defect it was built to catch then shipped four more times. Also re-checks on `synchronize`, because a rebase can falsify a number nobody retyped. |
| `.github/workflows/deploy-pages.yml` | Push to main touching `src/`, `data/`, `predictions/`, `results/`, `assets/` (the self-hosted font, inlined at build) — **and** after `.github/workflows/collect-agent-log.yml` finishes, because a commit pushed by another workflow's GITHUB_TOKEN cannot trigger a workflow on its own — plus manual dispatch. The **only** builder of the published site, and it refuses to publish a page whose data is missing or empty (`src/pipeline/check_build.py`). `index.html` and `dist/` are untracked, so there is no committed copy to serve; it does not commit anything, and `contents: read` means it cannot. Before building it reads the scheduled jobs' last 30 runs from GitHub's Actions API (`src/pipeline/recent_runs.py`, with `actions: read`) into a gitignored file the page shows on Checking the AI's work. |
