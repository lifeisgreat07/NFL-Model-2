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
| `CLAUDE.md` | What stays true for months: methodology, stage plans, traps | When a rule or plan changes |
| `memory/` | One file per session: what happened and why | Appended, never edited |

**Session start:** `python src/session_start.py` — it computes the state rather
than restating it, and cross-checks what `docs/context.md` claims against git.
Then read `docs/context.md`, then CLAUDE.md. Reach for `memory/` only to answer
"why did we decide that".

**Session end:** `python src/session_wrapup.py`, then rewrite `docs/context.md`
and add a `memory/` entry.

Neither script fetches pull-request state — there is no `gh` CLI on this
machine, and a guessed PR status would be exactly the unverified claim this
project is built to avoid. Check open PRs on GitHub yourself.

## The model

| Path | What it does |
|---|---|
| `src/config.py` | Constants and `VERSION_HISTORY`. The changelog page renders from this object, so the page cannot drift from the constant. |
| `src/ratings_engine.py` | Opponent-adjusted ridge ratings and QB ratings. |
| `src/weekly_update.py` | The weekly routine: predictions, grading, playoff odds. |
| `src/calibration.py` | Backtest calibration. Run deliberately, not per build; takes minutes. |

## The dashboard

| Path | What it does |
|---|---|
| `src/dashboard_template.html` | The whole site: markup, CSS and render functions in one file. Placeholders like `__TEAMS_JSON__` are swapped at build time. |
| `src/generate_dashboard.py` | Reads `data/`, fills the placeholders, writes `index.html`. |
| `index.html` | The built page. Generated — never hand-edited. |
| `src/prune_build_churn.py` | Drops artifacts whose only change is a build timestamp. |

## The agents

| Path | What it does |
|---|---|
| `src/scout_preflight.py` | Checks a PR description against reality before it opens. |
| `src/booth_verdict.py` | Parses the machine-readable verdict block out of a Booth report. |
| `src/booth_fixture_runner.py` | Runs deliberately-bad PRs that Booth must catch. |
| `src/collect_agent_log.py` | Turns Booth's audit comments into the data the reliability page renders. |
| `src/session_start.py` | Orientation: branch state, branch list, what `docs/context.md` claims vs what git knows, suite count vs the documented one. Never gates. |
| `src/session_wrapup.py` | End-of-session checks. Mechanical ones plus a by-hand list. This one gates. |

## The tests worth knowing about

| Path | What it guards |
|---|---|
| `tests/mutation/` | The mutation corpus. `python tests/mutation/runner.py` — a case must name the test it expects to catch it. |
| `tests/test_claude_md_freshness.py` | Every path CLAUDE.md names exists; stage headings are ordered and unique. |
| `tests/test_plain_language.py` | Statistics vocabulary stays off the reader-facing pages. Reads the JavaScript, not just the markup. |
| `tests/test_workflow_docs.py` | These four documents stay honest — see it for what "honest" means here. |
| `tests/test_readme_accuracy.py` | README.md may not name a path that is not there, and its stated counts are compared against what they count. |
| `tests/test_wrapup_date_slack.py` | The wrap-up gate's date tolerance is one-directional — tomorrow passes, yesterday does not — and both directions are asserted. |

## Workflows

| Path | When it runs |
|---|---|
| `.github/workflows/booth-pr-audit.yml` | Every PR open, push and description edit. |
| `.github/workflows/generate-dashboard.yml` | Push to main touching `src/`, `data/`, `predictions/`, `results/`. |
| `.github/workflows/weekly-update.yml` | The weekly routine. |
| `.github/workflows/booth-regression.yml` | Manual dispatch only. |
| `.github/workflows/run-tests.yml` | The suite, on push and PR. |
| `.github/workflows/collect-agent-log.yml` | Manual dispatch, and pushes to main, to record what the agents actually did. |
| `.github/workflows/run-backtest.yml` | The backtest, deliberately not on every push. |
