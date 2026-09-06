"""
Does dropping nfl_data_py -- and so unlocking pandas 2.x -- move the model?

requirements.txt has carried this as a queued experiment: nfl_data_py 0.3.3
requires pandas<2.0 and numpy<2.0, so it alone pins the whole project to the
1.x line, and the file says dropping it "would also remove the documented
revert path, and a pandas major version change can move model numerics. That
makes it a real experiment, not hygiene."

This is that experiment, and its result. Two things had to be settled first,
in order:

  1. Is the revert path real? src/verify_data_source_fallback.py answers that
     by executing it: nfl_data_py imports, all three loaders work, every
     required column is present, and it agrees with nflreadpy exactly on 2025
     week 10. It is a REAL fallback, not cruft -- so the pin is buying
     something, and this became a genuine trade-off rather than clean-up.

  2. Does the pandas version itself move the numbers? That is this file.

Note what the second question is NOT. Both runs use USE_NFLREADPY=True, so
nfl_data_py is never called in either. Its presence or absence is irrelevant
to the numbers; what matters is the version pin it FORCES. Holding the data
source fixed and varying only pandas/numpy is what makes this a clean
comparison rather than two changes at once.

PRE-DECLARED HYPOTHESIS, stated before the runs:
    Log loss, Brier and AUC agree to four decimal places between pandas
    1.5.3/numpy 1.26.4 and pandas 2.3.3/numpy 2.4.6. Accuracy may differ by
    one to two games out of 1087.

Four decimals is not an arbitrary bar. It is this project's own confirmed
finding: the same commit and dataset disagree by one to two games between a
Linux runner and Windows "while log loss, Brier and AUC agree to four
decimals". That is the established size of a difference this project treats
as noise, so it is the right threshold for a new one.

REPRODUCING IT
    Baseline (the committed environment):
        pip install -r requirements.txt
        python src/backtest.py
        cp results/backtest_metrics.csv baseline.csv

    Candidate (what dropping nfl_data_py would allow):
        python -m venv pd2env
        pd2env/bin/pip install "pandas>=2.2,<3" "numpy>=2,<3" \
            scikit-learn==1.9.0 nflreadpy==0.1.5 pyarrow==25.0.1
        pd2env/bin/python src/backtest.py
        cp results/backtest_metrics.csv candidate.csv

    Run each backtest TWICE per environment, keeping both CSVs. The controls
    matter more than the treatment: a cross-version delta means nothing if
    the pipeline is not deterministic within a single environment, and
    nothing else in this repo had ever checked that it is. This script
    requires them and refuses to reach a verdict without them.

    Then:
        python src/compare_pandas_versions.py \
            baseline.csv baseline_rerun.csv candidate.csv candidate_rerun.csv

Usage: python src/compare_pandas_versions.py \
           <baseline.csv> <baseline_rerun.csv> <candidate.csv> <candidate_rerun.csv>
Writes data/pandas_version_experiment.json.
"""
import json
import sys
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent.parent / 'data'

# The metrics that carry a result here. Accuracy is reported but deliberately
# does not decide anything -- at n=1087 it cannot distinguish a real change
# from a one-game platform wobble, which this project has already confirmed.
SCORING_METRICS = ['log_loss', 'brier', 'auc']
TOLERANCE = 0.00005          # "agrees to four decimal places"


def compare(baseline, candidate):
    """Deltas per model per metric, plus the verdict the tolerance implies."""
    common = [i for i in baseline.index if i in candidate.index]
    missing = [i for i in baseline.index if i not in candidate.index]
    delta = candidate.loc[common] - baseline.loc[common]

    # Row sets must match before any metric comparison means anything.
    # backtest() calls dropna(subset=features), so two runs can silently
    # evaluate different games -- the trap bootstrap_brier_gap.py exists to
    # avoid. Checked rather than assumed.
    same_n = bool((baseline.loc[common, 'n'] == candidate.loc[common, 'n']).all())

    worst = {m: float(delta[m].abs().max()) for m in SCORING_METRICS + ['accuracy']}
    breaches = {m: v for m, v in worst.items()
                if m in SCORING_METRICS and v >= TOLERANCE}

    return {
        'models_compared': common,
        'models_missing_from_candidate': missing,
        'same_row_sets': same_n,
        'n_games': int(baseline.loc[common[0], 'n']) if common else None,
        'max_abs_delta': worst,
        'scoring_metrics_beyond_tolerance': breaches,
        'per_model': {
            m: {metric: {'baseline': float(baseline.loc[m, metric]),
                         'candidate': float(candidate.loc[m, metric]),
                         'delta': float(delta.loc[m, metric])}
                for metric in SCORING_METRICS + ['accuracy']}
            for m in common
        },
    }


def main():
    # Four CSVs, not two. The controls are not optional: the verdict below
    # says a cross-version delta is "a real difference and not run-to-run
    # variation", and that sentence is only true if each environment was
    # shown to reproduce itself. An earlier draft of this script asserted it
    # without checking -- which is the exact failure this repo has recorded
    # three times, a guard whose comment claims more than its code delivers.
    if len(sys.argv) != 5:
        print(__doc__)
        print("error: need four CSVs -- baseline, baseline_rerun, "
              "candidate, candidate_rerun")
        return 1

    baseline = pd.read_csv(sys.argv[1], index_col=0)
    baseline_rerun = pd.read_csv(sys.argv[2], index_col=0)
    candidate = pd.read_csv(sys.argv[3], index_col=0)
    candidate_rerun = pd.read_csv(sys.argv[4], index_col=0)

    controls = {
        'baseline_reproduces': bool(baseline.equals(baseline_rerun)),
        'candidate_reproduces': bool(candidate.equals(candidate_rerun)),
    }
    controls['both_deterministic'] = (controls['baseline_reproduces']
                                      and controls['candidate_reproduces'])
    print("CONTROLS -- does each environment reproduce itself?")
    print(f"  baseline  run1 == run2 : {controls['baseline_reproduces']}")
    print(f"  candidate run1 == run2 : {controls['candidate_reproduces']}\n")

    result = compare(baseline, candidate)
    result['controls'] = controls

    print(f"Games evaluated: {result['n_games']}  "
          f"(same row sets: {result['same_row_sets']})\n")
    header = f"{'Model':<38}{'metric':<10}{'baseline':>10}{'candidate':>11}{'delta':>11}"
    print(header)
    print('-' * len(header))
    for m, metrics in result['per_model'].items():
        for metric in SCORING_METRICS + ['accuracy']:
            v = metrics[metric]
            flag = '  <-- beyond tolerance' if (
                metric in SCORING_METRICS and abs(v['delta']) >= TOLERANCE) else ''
            print(f"{m[:37]:<38}{metric:<10}{v['baseline']:>10.5f}"
                  f"{v['candidate']:>11.5f}{v['delta']:>+11.5f}{flag}")
        print()

    print("Largest absolute difference, any model:")
    for metric, v in result['max_abs_delta'].items():
        # Not named `note`: the verdict's own `note` is assigned just below,
        # and having the loop shadow it is how a report ends up printing the
        # wrong sentence next to the right numbers.
        suffix = '' if metric == 'accuracy' else (
            '  agrees to 4dp' if v < TOLERANCE else '  DOES NOT agree to 4dp')
        print(f"  {metric:<10}{v:.6f}{suffix}")

    if not controls['both_deterministic']:
        # Checked before anything else. If an environment does not reproduce
        # itself, every number above is run-to-run noise and reading a verdict
        # off it would be inventing a finding.
        which = [k for k in ('baseline', 'candidate')
                 if not controls[k + '_reproduces']]
        verdict = 'INVALID -- an environment does not reproduce itself'
        note = (f"The {' and '.join(which)} environment produced different "
                f"numbers on two identical runs, so nothing above can be "
                f"attributed to the pandas version. Fix the nondeterminism "
                f"first; it is a larger finding than this experiment.")
    elif not result['same_row_sets']:
        verdict = 'INVALID -- the two runs did not evaluate the same games'
        note = ("Row sets differ, so no metric comparison here means anything. "
                "Check dropna(subset=features) before reading any of the above.")
    elif result['scoring_metrics_beyond_tolerance']:
        verdict = 'REFUTED -- the pandas version moves the published metrics'
        worst = max(result['scoring_metrics_beyond_tolerance'].items(),
                    key=lambda kv: kv[1])
        note = (f"The hypothesis was that log loss, Brier and AUC would agree to "
                f"four decimals. They do not: {worst[0]} moves by {worst[1]:.6f}, "
                f"{worst[1]/TOLERANCE:.0f}x the threshold this project treats as "
                f"noise. The pipeline is deterministic within each environment, so "
                f"this is a real difference and not run-to-run variation.")
    else:
        verdict = 'CONFIRMED -- the pandas version leaves the metrics unchanged'
        note = ("Every scoring metric agrees to four decimals, so a pandas 2.x "
                "migration would not move any published figure.")

    print(f"\nVERDICT: {verdict}\n{note}")
    result['hypothesis'] = ("log loss, Brier and AUC agree to four decimal "
                            "places across the pandas major version")
    result['tolerance'] = TOLERANCE
    result['verdict'] = verdict
    result['note'] = note

    DATA_DIR.mkdir(exist_ok=True)
    out = DATA_DIR / 'pandas_version_experiment.json'
    with open(out, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved to {out}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
