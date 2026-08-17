# NFL Pick'em Model

A real, backtested win-probability model for weekly NFL picks. Not a
heuristic -- trained and validated on 294,989 real plays from nflverse
(2020-2025), with honest, run backtest numbers (see METHODOLOGY.md).

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

## Repo layout
```
src/
  config.py           -- every tuned constant, with the backtest that justified it
  data_loader.py       -- pulls fresh nflverse data automatically (no manual CSVs)
  ratings_engine.py    -- team + QB rating computation (leak-free, recency-weighted)
  weekly_update.py     -- main entrypoint: generates next week's predictions
  grade_predictions.py -- grades a completed week against actual results
  backtest.py           -- (add your own copy of the full backtest script here)
predictions/            -- one JSON file per week, saved BEFORE kickoff, never edited
results/                 -- graded predictions, builds the season accuracy record
dashboard.html            -- the command-board UI (regenerate manually for now)
```

## Manual usage
```bash
pip install -r requirements.txt
python src/weekly_update.py --season 2026 --week 2
# ... after that week's games finish ...
python src/grade_predictions.py --season 2026 --week 2
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
   - Or on the web at `claude.ai/code/routines` → New routine, for more
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
> Regenerate dashboard.html with the new predictions, flags, and updated
> accuracy record. Open a PR with all changes -- do not push directly to
> main.

7. **Review each week's PR before merging**, at least at first -- per
   Anthropic's own guidance, unattended agent runs should produce a
   reviewable draft for anything not fully reversible, and "this is what
   I'm picking for a paid competition" qualifies.

## What this does NOT automate yet
- Confirming genuinely uncertain starting QB situations (e.g. a team
  benching its starter) -- the routine prompt above asks Claude to
  web-search for this each run, but treat it as a flag to double check,
  not a guarantee.
- The dashboard regeneration script (`generate_dashboard.py`) isn't built
  yet in this repo -- the current `dashboard.html` was hand-updated. A
  Routine run should either build this properly or keep editing the file
  directly via the prompt.
- Hyperparameters (alpha, half-life, QB shrinkage) are NOT re-tuned
  automatically each week -- they're fit once via backtest and left fixed
  in `config.py`. Re-running the full backtest sweep weekly would be
  needlessly expensive; do it manually every few weeks or once per season.
