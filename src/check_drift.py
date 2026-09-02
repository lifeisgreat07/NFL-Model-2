"""
Model drift monitoring -- compares real, live prediction accuracy against
the canonical backtest baseline (config.BACKTEST_ACCURACY), and flags when
the gap is large enough to be a real statistical signal rather than
small-sample noise.

Why this exists: this project has found three real, silent bugs this
season (a leak in QB rating shrinkage, an unreproducible hyperparameter
decision, and a production pipeline with no scheduled trigger at all) --
all found by someone manually digging in, not by anything automated. This
script is meant to catch the next one earlier: if live accuracy quietly
diverges from what the backtest promised, that's worth a flag before it
becomes a months-old mystery.

Run standalone: python src/check_drift.py
Exit code 0 = no concerning drift (or not enough data yet to tell).
Exit code 1 = statistically significant underperformance detected.
"""
import json
import math
import re
from pathlib import Path

from config import BACKTEST_ACCURACY, BACKTEST_SEASONS

RESULTS_DIR = Path(__file__).parent.parent / 'results'
MIN_GAMES_TO_TEST = 30  # below this, any gap could easily just be noise
SIGNIFICANCE_Z = 1.96  # two-sided 95% -- consistent with the CIs used everywhere else in this project


def load_live_results():
    """Loads every graded result file for a season NOT in BACKTEST_SEASONS
    -- i.e., real, live predictions made after the backtest period, not
    the historical games the backtest itself was evaluated on."""
    records = []
    if not RESULTS_DIR.exists():
        return records
    for path in RESULTS_DIR.glob('*_graded.json'):
        m = re.match(r'(\d+)_week(\d+)_graded\.json', path.name)
        if not m:
            continue
        season = int(m.group(1))
        if season in BACKTEST_SEASONS:
            continue  # this is backtest-period data, not live monitoring data
        with open(path) as f:
            records.extend(json.load(f))
    return records


def one_proportion_z_test(observed_correct, n, expected_p):
    """Standard one-sample z-test for a proportion. Returns (z, is_significant_and_worse).
    No scipy dependency -- this script's only job is to be a reliable
    safety check, so it shouldn't itself depend on anything that could
    fail to be present in a given environment."""
    if n == 0:
        return None, False
    observed_p = observed_correct / n
    se = math.sqrt(expected_p * (1 - expected_p) / n)
    if se == 0:
        return None, False
    z = (observed_p - expected_p) / se
    is_significant_and_worse = z <= -SIGNIFICANCE_Z
    return z, is_significant_and_worse


def check_model(records, key, expected_p, label):
    graded = [r for r in records if r.get(key) is not None]
    n = len(graded)
    correct = sum(r[key] for r in graded)

    print(f"\n{label}:")
    print(f"  Live games graded: {n}")
    if n == 0:
        print("  No live results yet -- nothing to check.")
        return False
    observed_p = correct / n
    print(f"  Observed accuracy: {correct}/{n} = {observed_p*100:.1f}%")
    print(f"  Backtest baseline: {expected_p*100:.1f}%")

    if n < MIN_GAMES_TO_TEST:
        print(f"  Below {MIN_GAMES_TO_TEST} games -- too early to test statistically, watching only.")
        return False

    z, flagged = one_proportion_z_test(correct, n, expected_p)
    print(f"  z-score: {z:.2f}" if z is not None else "  z-score: undefined")
    if flagged:
        print(f"  *** DRIFT WARNING: live accuracy is significantly below the backtest baseline (z={z:.2f}, threshold={-SIGNIFICANCE_Z}) ***")
        print(f"  This does not automatically mean something is broken -- real variance happens -- but it's")
        print(f"  a large enough, unlikely-by-chance gap that it's worth a real look, not just noting and moving on.")
    else:
        print("  No significant drift detected.")
    return flagged


def main():
    records = load_live_results()
    print(f"Loaded {len(records)} live (non-backtest-season) graded predictions.")

    flagged_a = check_model(records, 'model_a_correct', BACKTEST_ACCURACY['model_a'], 'Model A')
    flagged_b = check_model(records, 'model_b_correct', BACKTEST_ACCURACY['model_b'], 'Model B')

    if flagged_a or flagged_b:
        print("\n=== DRIFT CHECK: WARNING FLAGGED ===")
        return 1
    print("\n=== DRIFT CHECK: OK ===")
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
