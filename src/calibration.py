"""
Calibration analysis over the real backtest window.

Why this exists: the dashboard's live calibration panel is computed from
graded results, and as of 2026-09 that is 14 games -- six buckets of one to
six games each. That is not enough to say anything, and until 2026-09-05 the
dashboard was charting it anyway. Calibration is a claim about how often a
stated probability comes true, and it needs a lot of games before it means
anything.

The backtest already has those games: ~1087 across BACKTEST_SEASONS, with a
leak-free weekly-refit walk-forward behind every one of them. backtest()
already exposes them via return_raw=True; nothing was reading it. This script
turns that into a real reliability diagram and writes data/calibration.json
for the dashboard to render.

Three deliberate choices:

  1. Bins are over the predicted probability of a HOME win across [0,1], not
     over "probability of whichever side we picked". Folding to the picked
     side throws away the direction of the miscalibration -- it cannot tell
     you whether the model is overconfident about home teams specifically,
     which is exactly the kind of bias worth finding.

  2. Every bin carries a Wilson score interval. A reliability diagram of bare
     points invites the same error the live panel made: a bin of 12 games at
     "58% actual" looks like a finding until you see the interval spans 30
     points. The interval is the honest part of the chart.

  3. Brier score is decomposed into reliability / resolution / uncertainty
     (Murphy 1973). Accuracy cannot distinguish "well calibrated" from
     "confidently right", and this project has already confirmed accuracy is
     too knife-edge at this sample size to carry a claim at all -- it moves by
     a full game between platforms on identical code. Reliability and
     resolution are the numbers that survive that.

Usage: python src/calibration.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from data_loader import load_plays, load_schedule
from ratings_engine import prep_plays, build_team_ratings, build_qb_ratings
from config import TRAIN_SEASONS, BACKTEST_SEASONS, MODEL_VERSION
from weekly_update import build_historical_features, build_qb_change_lookup
from backtest import backtest

DATA_DIR = Path(__file__).parent.parent / 'data'

# Bin edges over predicted home-win probability. Wider in the tails because
# there are simply fewer games out there -- equal-width bins would leave the
# extremes with counts too small to interpret, which is the failure this whole
# module exists to avoid.
BIN_EDGES = [0.0, 0.20, 0.30, 0.40, 0.45, 0.50, 0.55, 0.60, 0.70, 0.80, 1.0]

# Bins below this are still reported -- with their real count -- but flagged,
# so the dashboard can render them differently instead of pretending a
# handful of games measured something.
MIN_BIN_N = 25

MODELS = {
    'model_a': ['off_matchup', 'def_matchup', 'qb_matchup', 'qb_change_diff'],
    'model_b': ['off_matchup', 'def_matchup', 'qb_matchup', 'qb_change_diff', 'spread_line'],
    'market': ['spread_line'],
}


def wilson_interval(successes, n, z=1.96):
    """Wilson score interval for a binomial proportion.

    Chosen over the normal approximation because the normal one is badly
    wrong exactly where this matters: small n and proportions near 0 or 1,
    which is precisely the tail-bin case. Returns (lo, hi) as proportions.
    """
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return ((centre - margin) / denom, (centre + margin) / denom)


def brier_decomposition(y_true, y_prob, bin_edges=None):
    """Murphy (1973) decomposition: Brier = reliability - resolution + uncertainty.

    reliability  -- mean squared gap between predicted probability and observed
                    frequency within each bin. LOWER is better; 0 is perfect
                    calibration.
    resolution   -- how far bin frequencies sit from the base rate. HIGHER is
                    better; it measures whether the model separates games at
                    all. A model that always predicts the base rate is
                    perfectly calibrated and completely useless: reliability 0,
                    resolution 0.
    uncertainty  -- variance of the outcome itself. A property of the games,
                    not the model; nothing you do can change it.
    """
    edges = bin_edges or BIN_EDGES
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    n = len(y_true)
    base = y_true.mean()

    reliability = 0.0
    resolution = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (y_prob >= lo) & (y_prob < hi) if hi < 1.0 else (y_prob >= lo) & (y_prob <= hi)
        k = int(mask.sum())
        if k == 0:
            continue
        mean_pred = float(y_prob[mask].mean())
        obs = float(y_true[mask].mean())
        reliability += k * (mean_pred - obs) ** 2
        resolution += k * (obs - base) ** 2

    return {
        'reliability': reliability / n,
        'resolution': resolution / n,
        'uncertainty': float(base * (1 - base)),
        'base_rate': float(base),
    }


def calibration_bins(y_true, y_prob, bin_edges=None, min_n=MIN_BIN_N):
    """Bin predictions and report observed frequency with a Wilson interval."""
    edges = bin_edges or BIN_EDGES
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)

    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (y_prob >= lo) & (y_prob < hi) if hi < 1.0 else (y_prob >= lo) & (y_prob <= hi)
        k = int(mask.sum())
        if k == 0:
            continue
        wins = int(y_true[mask].sum())
        ci_lo, ci_hi = wilson_interval(wins, k)
        out.append({
            'lo': round(lo, 3),
            'hi': round(hi, 3),
            'label': f"{int(lo * 100)}-{int(hi * 100)}%",
            'n': k,
            'mean_predicted': round(float(y_prob[mask].mean()) * 100, 2),
            'observed': round(100 * wins / k, 2),
            'ci_lo': round(ci_lo * 100, 2),
            'ci_hi': round(ci_hi * 100, 2),
            # A bin whose interval straddles the diagonal is consistent with
            # perfect calibration -- worth marking, because "the point is off
            # the line" means nothing on its own.
            'consistent_with_perfect': bool(
                ci_lo * 100 <= float(y_prob[mask].mean()) * 100 <= ci_hi * 100
            ),
            'underpowered': k < min_n,
        })
    return out


def build_hist():
    """The same leak-free feature table backtest.py builds, minus the OL
    lookup. Neither fitted model uses ol_continuity_diff, so loading snap
    counts here would cost an upstream data source for a column nothing
    reads -- the same reasoning that removed it from the live weekly path."""
    print("Loading play-by-play and building historical features (slow first time)...")
    raw = load_plays(TRAIN_SEASONS)
    plays, week_keys, week_to_idx = prep_plays(raw)
    team_ratings_by_week = build_team_ratings(plays, week_keys, upto_cutoff_i=None)
    qb = build_qb_ratings(raw)
    qb_change_lookup = build_qb_change_lookup(qb, TRAIN_SEASONS)
    schedules_by_season = {s: load_schedule(s) for s in TRAIN_SEASONS}
    hist = build_historical_features(
        plays, week_keys, week_to_idx, team_ratings_by_week, qb,
        schedules_by_season, ol_lookup=None, qb_change_lookup=qb_change_lookup,
    )
    print(f"  {len(hist)} historical games built.")
    return hist


def main():
    hist = build_hist()

    # Provenance. These numbers are platform-sensitive at the margin (see the
    # Model Lab cross-platform reproducibility finding), so a file that says
    # nothing about where it came from cannot be checked later. Records the
    # machine, the interpreter and the exact versions of the libraries that
    # do the arithmetic.
    import platform
    import importlib.metadata as _md
    from datetime import datetime, timezone

    def _ver(pkg):
        try:
            return _md.version(pkg)
        except Exception:
            return 'absent'

    payload = {
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
        'provenance': {
            'platform': platform.platform(),
            'python': platform.python_version(),
            'numpy': _ver('numpy'),
            'pandas': _ver('pandas'),
            'scikit-learn': _ver('scikit-learn'),
        },
        'model_version': MODEL_VERSION,
        'backtest_seasons': BACKTEST_SEASONS,
        'bin_edges': BIN_EDGES,
        'min_bin_n': MIN_BIN_N,
        'models': {},
    }

    print(f"\n{'Model':<10}{'n':<7}{'Brier':<10}{'Reliability':<14}{'Resolution':<13}{'LogLoss':<10}")
    for name, features in MODELS.items():
        metrics, y_true, y_prob = backtest(hist, features, BACKTEST_SEASONS, return_raw=True)
        decomp = brier_decomposition(y_true, y_prob)
        bins = calibration_bins(y_true, y_prob)
        payload['models'][name] = {
            'features': features,
            'metrics': {k: (float(v) if k != 'n' else int(v)) for k, v in metrics.items()},
            'decomposition': {k: round(v, 6) for k, v in decomp.items()},
            'bins': bins,
        }
        print(f"{name:<10}{metrics['n']:<7}{metrics['brier']:<10.5f}"
              f"{decomp['reliability']:<14.6f}{decomp['resolution']:<13.6f}{metrics['log_loss']:<10.5f}")

    DATA_DIR.mkdir(exist_ok=True)
    out = DATA_DIR / 'calibration.json'
    with open(out, 'w') as f:
        json.dump(payload, f, indent=2)
    print(f"\nSaved to {out}")
    print("Lower reliability is better (0 = perfectly calibrated). "
          "Higher resolution is better (0 = says nothing).")


if __name__ == '__main__':
    main()
