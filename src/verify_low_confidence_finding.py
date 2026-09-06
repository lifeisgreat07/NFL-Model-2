"""
Re-derive the low-confidence finding that the dashboard states as CONFIRMED.

Model Lab has carried this claim since before 2026-09: "When Model A's own
probability is near a coin flip (within 0.05 of 50%), it hits just 52.5% --
barely above chance -- while the market stays at 64.4% in those same games. A
-11.95pt gap, CI [-18.37,-5.53], clearly excludes zero."

Booth flagged it UNVERIFIABLE on PR #18, and it was right to. Grepping the
repository finds those numbers in exactly two places -- the dashboard template
and the generated index.html -- and nowhere else. No script produced them, no
data file holds them, and the +/-0.05 band around 50% is not one of
calibration.json's bins, so it cannot even be read off the existing artifact.

That is the precise situation VERIFICATION.md exists to prevent, and this
project has already been burned by it once: the QB-shrinkage constant was
carried for weeks on a number that turned out not to reproduce. A public
CONFIRMED FINDING with nothing behind it is the same failure waiting to
happen, so this script either reproduces it or contradicts it.

Deliberately reuses walk_forward_aligned() from bootstrap_brier_gap.py rather
than rebuilding the walk-forward. Model A and the market must be scored on the
SAME games for a paired comparison, and that function already establishes and
prints that alignment. A second, independently-written walk-forward here would
be a second thing to get wrong, and it could agree with itself while disagreeing
with everything else on the site.

One honest note on method. This finding is stated in ACCURACY, and this project
has separately confirmed that accuracy is not reproducible across platforms --
the same commit and dataset disagree by one to two games out of ~1087 between
Linux and Windows. Within a subset this small that sensitivity is larger, not
smaller, so exact agreement to the tenth of a point is not the bar. The bar is
whether the finding's SUBSTANCE holds: a large negative gap whose interval
excludes zero.

Usage: python src/verify_low_confidence_finding.py
Writes data/low_confidence_finding.json and prints a verdict.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from config import BACKTEST_SEASONS, MODEL_VERSION
from calibration import build_hist
from bootstrap_brier_gap import walk_forward_aligned

DATA_DIR = Path(__file__).parent.parent / 'data'

# The slice as the dashboard describes it: Model A's OWN probability within
# 0.05 of a coin flip. Note this is defined by Model A's confidence, not the
# market's -- the claim is about what happens when *our* model says it does
# not know.
BAND = 0.05

# The published figures, so a discrepancy is reported as a discrepancy rather
# than quietly replaced by whatever came out today.
PUBLISHED = {
    'model_a_accuracy': 52.5,
    'market_accuracy': 64.4,
    'gap_pt': -11.95,
    'ci': [-18.37, -5.53],
}

N_RESAMPLES = 5000
SEED = 20260906


def paired_accuracy_bootstrap(y_true, prob_a, prob_m, n_resamples=N_RESAMPLES, seed=SEED):
    """Bootstrap the accuracy difference on a fixed subset of games.

    Paired: one index vector per resample, applied to both models, because
    they are being scored on the same games and their correctness is
    correlated."""
    rng = np.random.default_rng(seed)
    ca = (prob_a >= 0.5).astype(int) == y_true
    cm = (prob_m >= 0.5).astype(int) == y_true
    n = len(y_true)
    diffs = np.empty(n_resamples)
    for i in range(n_resamples):
        idx = rng.integers(0, n, n)
        diffs[i] = 100 * (ca[idx].mean() - cm[idx].mean())
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return 100 * (ca.mean() - cm.mean()), float(lo), float(hi)


def main():
    hist = build_hist()
    print("\nRunning the aligned walk-forward (Model A and market on the same games)...")
    _keys, y_true, probs, coverage = walk_forward_aligned(hist)
    pa, pm = probs['model_a'], probs['market']
    print(f"  {len(y_true)} games evaluated across {BACKTEST_SEASONS}")

    mask = np.abs(pa - 0.5) <= BAND
    n = int(mask.sum())
    print(f"\nGames where Model A's probability is within {BAND} of 50%: "
          f"{n} of {len(y_true)} ({100*n/len(y_true):.1f}%)")
    if n < 30:
        print("  WARNING: that subset is too small to support any claim.")

    yt, sa, sm = y_true[mask], pa[mask], pm[mask]
    acc_a = 100 * (((sa >= 0.5).astype(int) == yt).mean())
    acc_m = 100 * (((sm >= 0.5).astype(int) == yt).mean())
    gap, lo, hi = paired_accuracy_bootstrap(yt, sa, sm)

    print(f"\n{'':<26}{'published':<14}{'reproduced':<14}{'delta'}")
    rows = [
        ('Model A accuracy', PUBLISHED['model_a_accuracy'], acc_a),
        ('Market accuracy', PUBLISHED['market_accuracy'], acc_m),
        ('Gap (Model A - market)', PUBLISHED['gap_pt'], gap),
    ]
    for label, pub, got in rows:
        print(f"{label:<26}{pub:<14.2f}{got:<14.2f}{got-pub:+.2f}")
    print(f"{'95% CI':<26}{str(PUBLISHED['ci']):<14}[{lo:.2f}, {hi:.2f}]")

    excludes_zero = (lo > 0) or (hi < 0)
    # The substance of the claim, restated as three checkable conditions.
    substance_holds = (gap < 0) and excludes_zero and (acc_m > acc_a)
    close_to_published = abs(gap - PUBLISHED['gap_pt']) <= 3.0

    print(f"\nInterval excludes zero: {excludes_zero}")
    if substance_holds and close_to_published:
        verdict = 'CONFIRMED'
        note = ("The finding reproduces. Model A really is unreliable when it "
                "says it does not know, and the market really is not.")
    elif substance_holds:
        verdict = 'CONFIRMED IN SUBSTANCE, FIGURES DIFFER'
        note = ("The direction and significance hold, but the published "
                "numbers do not match what this run produces. Update the "
                "dashboard to the reproduced figures.")
    else:
        verdict = 'DOES NOT REPRODUCE'
        note = ("The published claim is not supported by this re-derivation. "
                "It must be corrected or withdrawn from the dashboard, not "
                "left standing.")
    print(f"\nVERDICT: {verdict}\n{note}")

    payload = {
        'model_version': MODEL_VERSION,
        'backtest_seasons': BACKTEST_SEASONS,
        'band': BAND,
        'n_games_total': int(len(y_true)),
        'n_games_in_band': n,
        'coverage': coverage,
        'published': PUBLISHED,
        'reproduced': {
            'model_a_accuracy': round(acc_a, 2),
            'market_accuracy': round(acc_m, 2),
            'gap_pt': round(gap, 2),
            'ci_lo': round(lo, 2),
            'ci_hi': round(hi, 2),
            'excludes_zero': bool(excludes_zero),
        },
        'n_resamples': N_RESAMPLES,
        'seed': SEED,
        'verdict': verdict,
    }
    DATA_DIR.mkdir(exist_ok=True)
    out = DATA_DIR / 'low_confidence_finding.json'
    with open(out, 'w') as f:
        json.dump(payload, f, indent=2)
    print(f"\nSaved to {out}")


if __name__ == '__main__':
    main()
