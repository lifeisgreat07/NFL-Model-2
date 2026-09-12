# NFL Pick'em Model

A real, backtested win-probability model for weekly NFL picks. Not a
heuristic -- trained and validated on 294,989 real plays from nflverse
(2020-2025), with honest, run backtest numbers.

**Live dashboard: https://lifeisgreat07.github.io/NFL-Model-2/**

## For recruiters -- project overview

This is a working prediction system, not a notebook. Every week it pulls
fresh play-by-play data, refits opponent-adjusted team ratings, writes
that week's picks to a timestamped file **before kickoff**, and grades
them against reality afterwards. The dashboard above is generated from
those files, so the accuracy record on it is the model's real record, not
a number typed in by hand.

What it is meant to demonstrate, and where to look:

- **A model that beats its baselines and admits where it doesn't.** The
  table below is a 2022-2025 holdout, 1,087 games, never trained on the
  season it is evaluated against. The football-only model beats
  home-team-always-wins by 8 points. It does *not* beat the betting
  market, and the README says so rather than quietly omitting the
  comparison. See `src/backtest.py` and `src/ratings_engine.py`.
- **Leak-free by construction, and tested for it.** Every rating a
  prediction uses is computed from data available before that game
  kicked off. `tests/test_leak_free.py` fails the build if a future
  observation ever reaches a past prediction.
- **Tuned constants with the experiment attached.** `src/config.py`
  carries every hyperparameter next to the backtest that justified it,
  so no number in the model is there because it looked about right.
- **AI-assisted development with an independent verifier.** Work is done
  in a "Scout" role and audited by a separate "Booth" role that shares no
  context with it, runs in CI on every pull request, and must re-execute
  the commands that would prove or disprove each claim before it reports.
  See `BOOTH_PROTOCOL.md`, `.github/workflows/booth-pr-audit.yml`, and
  `VERIFICATION.md` -- the last of which is the rule that no claim in this
  repository is made without evidence that was actually run.
- **Tests that are themselves tested.** A committed mutation corpus
  (`tests/mutation/`, 26 cases, one file per subject under test)
  deliberately breaks the code in known
  ways and fails if the suite does not catch the break -- because a test
  that passes against broken code is worse than no test.
- **Eight CI workflows** in `.github/workflows/` cover the test suite, the
  weekly data pull, the backtest, the Pages build-and-deploy, the
  agent-activity log, a pre-flight check on every pull request description,
  and both halves of the Booth audit.

If you have five minutes: open the live dashboard, read its **Methodology**
page, then read `VERIFICATION.md`. Those three cover what the model does,
how it was validated, and how the work on it is checked.

## Current model (v2)
- Opponent-adjusted team ratings: two-way fixed-effects ridge regression
  on play-level EPA, recency-weighted (16-game half-life), alpha=15
  (tuned via backtest -- see `src/config.py` for justification of every
  constant).
- Per-QB rating: leak-free trailing EPA/dropback for that week's actual
  starter, shrunk toward league average for small samples.
- Two models shown side by side: **Model A** (football-only) and
  **Model B** (blended with the current Vegas spread).

Real backtest results (2022-2025 holdout, 1,087 games, never trained on
the season it's evaluated against):

| Model | Accuracy | Log Loss | AUC |
|---|---|---|---|
| Coin flip | 50.0% | 0.693 | 0.500 |
| Home team always wins | 54.6% | - | - |
| Model A (football + QB) | 62.6% | 0.655 | 0.662 |
| Vegas market alone | 68.1% | 0.607 | 0.724 |
| Model B (+ market) | 68.3% | 0.608 | 0.726 |

The full methodology write-up lives on the dashboard's **Methodology**
page rather than in a separate file, so that the explanation and the
numbers it explains are regenerated from the same data in the same step.

## Repo layout
```
src/
  config.py             -- every tuned constant, with the backtest that justified it
  data_loader.py        -- pulls fresh nflverse data automatically (no manual CSVs)
  ratings_engine.py     -- team + QB rating computation (leak-free, recency-weighted)
  weekly_update.py      -- main entrypoint: generates next week's predictions
  grade_predictions.py  -- grades a completed week against actual results
  backtest.py           -- the holdout backtest behind the table above
  calibration.py        -- reliability of the stated probabilities
  generate_dashboard.py -- builds index.html from the template plus data/
  dashboard_template.html -- the dashboard's markup, with data injected at build
  scout_preflight.py    -- checks a branch against the project's own rules
  session_wrapup.py     -- end-of-session checks (suite count, unpushed work, docs)
predictions/            -- one JSON file per week, saved BEFORE kickoff, never edited
results/                -- graded predictions, builds the season accuracy record
data/                   -- generated inputs the dashboard reads
tests/                  -- the suite, plus tests/mutation/ (tests for the tests)
.github/workflows/      -- CI: tests, weekly update, backtest, dashboard, Booth
```

`index.html` and `dist/` are **build outputs and are not in the repository.**
Both are produced by `src/generate_dashboard.py`; GitHub Pages publishes them
from a CI build, and the test suite builds them itself via the root
`conftest.py`. To see the dashboard locally, run the generator.

## Manual usage
```bash
pip install -r requirements.txt
python src/weekly_update.py --season 2026 --week 2
# ... after that week's games finish ...
python src/grade_predictions.py --season 2026 --week 2
# rebuild the dashboard from whatever is in data/ and results/
python src/generate_dashboard.py
```

Running the tests:
```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Automating this with Claude Code Routines

This is designed to run unattended on a schedule. Setup (verified against
current Claude Code docs, code.claude.com/docs/en/routines):

1. **Push this repo to GitHub.** Routines clone from GitHub on every run.
2. **Connect GitHub to Claude Code**, if you haven't already: run
   `/web-setup` inside Claude Code (this is separate from installing the
   GitHub App -- both are required for the routine to actually trigger).
3. **Create the routine.** Either:
   - In Claude Code CLI: type `/schedule` and describe the task in plain
     language (see prompt below) -- Claude will ask what repo, what
     schedule, and set it up.
   - Or on the web at `claude.ai/code/routines` -> New routine, for more
     control (you can see all fields before creating).
4. **Set the trigger to "schedule," weekly, timed for after Monday Night
   Football completes** (e.g. Tuesday 6 AM ET during the season).
5. **Make sure the routine's cloud environment has network access
   enabled** -- it needs to reach nflverse's GitHub-hosted data and do web
   research for injury/QB news. This is a setting on the routine's
   environment, not on by default for every environment type.
6. **Give it real, unattended-safe instructions** -- routines run with no
   permission prompts mid-run, so be explicit. Suggested prompt:

> Run `python src/weekly_update.py --season 2026 --week {current_week}` to
> generate this week's predictions. Before finalizing, web-search for any
> starting QB changes, injuries, or coaching news for each team playing
> this week that might contradict the script's assumed starter (which is
> just "who had the most dropbacks last week" -- a lagging signal). Add a
> flag note to any game where you find a meaningful discrepancy. Then run
> `python src/grade_predictions.py` for last week if not already graded.

> Regenerate the dashboard with `python src/generate_dashboard.py` so the
> new predictions, flags, and updated accuracy record are picked up. Open
> a PR with all changes -- do not push directly to main.

7. **Review each week's PR before merging**, at least at first -- per
   Anthropic's own guidance, unattended agent runs should produce a
   reviewable draft for anything not fully reversible, and "this is what
   I'm picking for a paid competition" qualifies.

## What this does NOT automate yet
- Confirming genuinely uncertain starting QB situations (e.g. a team
  benching its starter) -- the routine prompt above asks Claude to
  web-search for this each run, but treat it as a flag to double check,
  not a guarantee.
- Hyperparameters (alpha, half-life, QB shrinkage) are NOT re-tuned
  automatically each week -- they're fit once via backtest and left fixed
  in `src/config.py`. Re-running the full backtest sweep weekly would be
  needlessly expensive; do it manually every few weeks or once per season.
- The model does not beat the betting market on its own. Model B only
  matches it, within noise. Treating Model A as an edge against a market
  price would be a misreading of the table above.
