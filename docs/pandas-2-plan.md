# The pandas 2 move: a plan

Stage 88 item 7 of the 2026-11-02 review: "The pandas 2 move is planned as its own piece of work,
regenerating every published figure as part of it." This is that plan. Nothing in it has been done;
`requirements.txt` still pins `pandas==1.5.3` and `numpy==1.26.4`.

## Why it is its own piece of work

`requirements.txt` explains the pin. `nfl_data_py` (the NFL's checked fallback loader) requires
pandas and numpy below 2.0. And the one experiment run on the question
(`src/sports/nfl/research/compare_pandas_versions.py`, `data/nfl/pandas_version_experiment.json`)
found that a newer pandas moves every model built on EPA-derived features: log loss by up to 0.00034
and AUC by up to 0.00125 over the same 1,087 games, while "Market alone", which aggregates nothing,
is bit-identical. No conclusion changes; every published figure moves in the third or fourth decimal.

So the move is a migration of published numbers, not a dependency bump. Done as a bump, the
page's figures, the tests that tie them to files, and the drift baselines would all disagree with the
code that produced them, and the first anyone would hear of it is a red suite or a drift flag.

## What has changed since the experiment

- pandas 1.5.3 receives no fixes, and the suite prints numpy's deprecation of `find_common_type`
  from inside pandas on every run.
- pandas 3.0 has shipped (copy-on-write by default, a pyarrow-backed string type by default). The
  item names pandas 2; the target version is the first decision below.
- The project now has three sports. The NHL and NBA daily runs refit Model A and Model B on every
  run with pandas-built feature tables, under registrations (`experiments/nhl/stage58`,
  `experiments/nba/stage65`) that name the backtest each forward test and drift check is held to.

## Decisions to make first (Mark's)

1. **Target version.** pandas 2.3 (the last 2.x; numpy 2 supported; the smaller change), or straight
   to 3.x (copy-on-write and string dtype changes reach every frame the code mutates). Recommended:
   2.3 now, 3.x as a later piece of work with its own experiment.
2. **The NFL fallback loader.** `nfl_data_py` cannot install beside pandas 2. Either drop it (and
   `USE_NFLREADPY`, and `data/nfl/data_source_fallback.json`'s claim that the revert path is real),
   or keep it only in a separate pinned environment that the canary exercises. Recommended: drop
   it; nflreadpy has carried every live run since 2026-08.
3. **When.** A new pandas changes the pick a daily run makes from the same data. During a season
   that is a change to a registered model, which needs a registered amendment and a disclosure, and
   it splits a forward test between two code versions. Recommended: between seasons, after the NBA
   and NHL seasons end and before the 2027 NFL season's first lock; or, if security forces it
   earlier, as a registered deviation in all three registrations, dated before any pick it touches.

## The steps

1. **Branch and pin.** One branch. `requirements.txt` moves pandas and numpy together, with
   `pyarrow`, `scikit-learn` and `scipy` checked against them; `nfl_data_py` goes or moves per
   decision 2. CI's Python stays 3.11.
2. **Make the code run.** Fix what the new pandas refuses (chained assignment, removed
   arguments, dtype changes in `groupby` and `concat`). Each fix is behaviour-preserving and tested
   on the old pin first where it can be.
3. **Re-run the experiment.** `compare_pandas_versions.py` on the new pin against today's, all
   models, extended from the NFL's backtest to the NHL's and NBA's. The pre-declared tolerance stays four decimals; anything
   beyond it is reported, model by model, before anything is regenerated.
4. **Regenerate every published figure, in one place.** Each file below is rebuilt by the script
   that made it, at the new pin, and committed with the before and after in the PR body:
   - NFL: `data/nfl/calibration.json` (the backtest table on the page and README),
     `experiments/nfl/stage5/results/*.json` and `stage5/residuals.json` (Stage 33 R4's drift
     baseline and the lagged-QB figure beside it), `experiments/nfl/stage6/results/*.json`,
     `experiments/nfl/stage33/results/*.json`, `data/nfl/bootstrap_brier_gap.json`,
     `data/nfl/ats_evaluation.json`, `data/nfl/qb_leak_effect.json`,
     `data/nfl/low_confidence_finding.json`, and then `data/nfl/reproducibility_audit.json` by
     re-running the audit.
   - NHL: `experiments/nhl/stage56/results/confirmation.json` and `tuning.json`, the season
     spread file Stage 85 item 3 adds, and `data/nhl/drift_baseline.json` from them.
   - NBA: `experiments/nba/stage61/results/confirmation.json` and `tuning.json`, the season spread
     file, and `data/nba/drift_baseline.json` (both baselines, with and without availability, since
     Stage 85 item 2).
   - Model Lab rows and every README or page figure that `tests/test_backtest_figures_tie.py` and
     the per-sport tie tests read; a figure printed anywhere and tied by no test is found by
     searching the old value, not assumed absent.
5. **Amend the registrations.** Each of the three live registrations gets a dated amendment: the
   pin moved, the baseline moved from X to Y, and which picks were made under which pin (the picks'
   `code` field already records the version). Saved picks are never rewritten.
6. **Hold it.** The suite, the browser checks and a full site build pass at the new pin; the
   nightly canary runs green for a week on the branch's pin before it merges if any season is live.

## What would stop it

A figure that moves beyond the four-decimal tolerance on a model the page draws a conclusion
from, a drift baseline that moves enough to change a look's verdict, or a forward test whose
comparison changes sign. Any of these is reported and decided on before the merge, not after.

## What it does not cover

Python 3.12 or later, scikit-learn's own major versions, and the move to pandas 3.x if decision 1
stops at 2.3. Each is its own experiment for the same reason this one is.
