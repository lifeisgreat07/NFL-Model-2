"""
Paired bootstrap on the Model B vs market comparison.

Why this exists: the reliability diagram on Model Lab reports that Model B has
better resolution than the market (0.039321 vs 0.038180) but worse reliability
(0.001697 vs 0.001334), with a Brier gap of 0.00062 in Model B's favour. The
page deliberately calls that "a lead, not a claim", because nothing had tested
whether those gaps survive resampling. This is the test that settles it.

Three decisions worth stating, because each one could quietly invalidate the
result if it went the other way.

  1. PAIRED, and structurally so. The two forecasters see the same games, so
     their errors are heavily correlated and an unpaired comparison would
     wildly overstate the uncertainty. Pairing only means anything if index i
     refers to the same game in both arrays -- so this script does not take
     two independent backtest() runs and hope their rows line up. It runs one
     walk-forward, predicts every model on the SAME test rows, and carries
     (season, week, away, home) keys the whole way so the alignment is
     checkable rather than assumed.

     That care is not hypothetical. backtest() drops rows with
     `dropna(subset=features)`, and the feature sets differ -- the market uses
     spread_line alone, Model A uses four play-by-play features, Model B uses
     all five. If any game is missing one but not the other, the three runs
     evaluate different game sets, and "0.00062 apart" would be comparing
     numbers built from different games. This script measures that overlap and
     prints it every run instead of leaving it to trust.

  2. Models still TRAIN on their own natural row set, exactly as the live
     pipeline and backtest() do; only the evaluation rows are held common.
     Restricting training to the intersection would make Model A a slightly
     different model from the one that ships, and this is a question about the
     models we actually have, not about ones built for the test.

  3. Reliability and resolution are re-decomposed INSIDE each resample, using
     calibration.py's own brier_decomposition -- imported, not reimplemented,
     so the thing under test is the thing that produced the published numbers.
     Bin membership shifts as games are resampled, which is exactly the
     variation being measured.

Sign convention throughout: every reported difference is (model_b - market).
Brier, log loss and reliability are LOWER-is-better, so a negative difference
favours Model B. Resolution is HIGHER-is-better, so a positive difference
favours Model B. Each row states its own direction rather than making the
reader remember.

A gap counts as real only when the 95% interval excludes zero -- the same bar
every other decision in this project has had to clear.

Usage: python src/bootstrap_brier_gap.py
Writes data/bootstrap_brier_gap.json and prints a summary table.
"""
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss

sys.path.insert(0, str(Path(__file__).parent))
from config import BACKTEST_SEASONS, MODEL_VERSION
# build_hist and brier_decomposition are imported, never reimplemented: the
# feature table must be the same one calibration.py used, and the
# decomposition under test must be the one that produced the published
# numbers. A second copy of either would let this script agree with itself
# while disagreeing with the dashboard.
from calibration import brier_decomposition, build_hist

DATA_DIR = Path(__file__).parent.parent / 'data'

FOOTBALL = ['off_matchup', 'def_matchup', 'qb_matchup', 'qb_change_diff']
MODELS = {
    'model_a': FOOTBALL,
    'model_b': FOOTBALL + ['spread_line'],
    'market': ['spread_line'],
}
# Every feature any model uses. A game is only usable for a PAIRED comparison
# if all of them are present -- otherwise some model in the comparison has
# nothing to say about it.
ALL_FEATURES = FOOTBALL + ['spread_line']

N_RESAMPLES = 5000
# Fixed so a re-run reproduces the published interval exactly. The
# cross-platform finding on Model Lab is about float arithmetic, not about
# RNG; numpy's PCG64 is deterministic given a seed on every platform.
SEED = 20260905

# Comparisons to test. (label, model, baseline)
COMPARISONS = [
    ('Model B vs market', 'model_b', 'market'),
    ('Model A vs market', 'model_a', 'market'),
    ('Model B vs Model A', 'model_b', 'model_a'),
]

# (metric key, human label, True when LOWER is better)
METRICS = [
    ('brier', 'Brier', True),
    ('log_loss', 'Log loss', True),
    ('reliability', 'Reliability', True),
    ('resolution', 'Resolution', False),
]


def walk_forward_aligned(hist, models=MODELS, test_seasons=BACKTEST_SEASONS):
    """One walk-forward producing every model's probability for the same games.

    Mirrors backtest()'s weekly-refit structure exactly -- train on everything
    strictly earlier, refit every week, predict that week -- with one
    difference: the TEST rows are the games usable by every model at once, so
    the outputs are aligned by construction.

    Returns (keys, y_true, {name: y_prob}, coverage) where coverage records how
    many rows each model would have had on its own, so the cost of insisting on
    a common set is visible rather than silent.
    """
    hist = hist.sort_values(['season', 'week'])

    coverage = {name: int(len(hist.dropna(subset=list(feats) + ['home_win'])))
                for name, feats in models.items()}
    common = hist.dropna(subset=ALL_FEATURES + ['home_win'])
    coverage['common'] = int(len(common))

    keys, all_true = [], []
    all_prob = {name: [] for name in models}

    for season in test_seasons:
        weeks = sorted(common[common['season'] == season]['week'].unique())
        for w in weeks:
            test_w = common[(common['season'] == season) & (common['week'] == w)]
            if len(test_w) == 0:
                continue

            # Fit each model on its OWN natural training rows, exactly as
            # backtest() does -- Model A is not penalised for the market's
            # missing spreads, and vice versa.
            fitted = {}
            for name, feats in models.items():
                d2 = hist.dropna(subset=list(feats) + ['home_win'])
                train = d2[(d2['season'] < season)
                           | ((d2['season'] == season) & (d2['week'] < w))]
                if len(train) < 50:
                    fitted[name] = None
                    continue
                m = LogisticRegression(max_iter=1000)
                m.fit(train[list(feats)].values, train['home_win'].values)
                fitted[name] = m

            # A week is only usable if every model can speak to it. Skipping
            # the whole week keeps the arrays aligned; letting one model sit
            # out would break the pairing silently.
            if any(m is None for m in fitted.values()):
                continue

            for name, feats in models.items():
                all_prob[name].extend(
                    fitted[name].predict_proba(test_w[list(feats)].values)[:, 1])
            all_true.extend(test_w['home_win'].values)
            # hist carries no team names -- build_historical_features keeps
            # season, week, the outcome and the features and nothing else --
            # so the identifier is the hist row index, which points straight
            # back at the game for anyone auditing a specific prediction.
            keys.extend((int(season), int(w), int(i)) for i in test_w.index)

    y_true = np.asarray(all_true, dtype=float)
    probs = {k: np.asarray(v, dtype=float) for k, v in all_prob.items()}
    for name, p in probs.items():
        assert len(p) == len(y_true), f"{name} produced {len(p)} rows against {len(y_true)} outcomes"
    return keys, y_true, probs, coverage


def metric_set(y_true, y_prob):
    """The four numbers being compared, for one model on one (re)sample."""
    d = brier_decomposition(y_true, y_prob)
    return {
        'brier': float(brier_score_loss(y_true, y_prob)),
        'log_loss': float(log_loss(y_true, y_prob, labels=[0, 1])),
        'reliability': d['reliability'],
        'resolution': d['resolution'],
    }


def paired_bootstrap(y_true, prob_a, prob_b, n_resamples=N_RESAMPLES, seed=SEED):
    """Resample GAMES (not models) and recompute every metric difference.

    The same index vector is applied to both forecasters on every draw. That
    is the whole point: it preserves the correlation between two models that
    got the same easy games right, so what is left is the difference between
    them rather than the difference between two sets of games.
    """
    rng = np.random.default_rng(seed)
    n = len(y_true)
    diffs = {k: np.empty(n_resamples) for k, _, _ in METRICS}

    for i in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        yt = y_true[idx]
        # A resample that draws only one outcome class makes log loss and the
        # decomposition meaningless. At n=1087 and a ~55% base rate this is
        # astronomically unlikely, but a silent nan would poison the interval.
        if yt.min() == yt.max():
            for k, _, _ in METRICS:
                diffs[k][i] = np.nan
            continue
        ma = metric_set(yt, prob_a[idx])
        mb = metric_set(yt, prob_b[idx])
        for k, _, _ in METRICS:
            diffs[k][i] = ma[k] - mb[k]

    return diffs


def summarise(point_a, point_b, diffs, y_true, prob_a, prob_b):
    """Point estimate, 95% interval, and a verdict for each metric.

    The point estimate is the full-sample difference, not the bootstrap mean --
    the resamples estimate the spread around the observed value, they do not
    replace it.
    """
    out = {}
    for key, label, lower_better in METRICS:
        d = diffs[key]
        good = d[~np.isnan(d)]
        lo, hi = np.percentile(good, [2.5, 97.5])
        point = point_a[key] - point_b[key]
        excludes_zero = (lo > 0) or (hi < 0)
        favours_a = (point < 0) if lower_better else (point > 0)
        out[key] = {
            'label': label,
            'lower_is_better': lower_better,
            'a': point_a[key],
            'b': point_b[key],
            'difference': point,
            'ci_lo': float(lo),
            'ci_hi': float(hi),
            'excludes_zero': bool(excludes_zero),
            'favours': ('a' if favours_a else 'b'),
            'verdict': ('REAL DIFFERENCE' if excludes_zero else 'INCONCLUSIVE'),
            'degenerate_resamples': int(np.isnan(d).sum()),
        }

    # Independent check on the Brier interval. Brier is the mean of per-game
    # squared errors, so the difference is the mean of a per-game difference
    # and has a closed-form standard error. Two methods that disagree mean the
    # bootstrap is wired wrong -- this is the cheapest way to find that out.
    per_game = (prob_a - y_true) ** 2 - (prob_b - y_true) ** 2
    se = per_game.std(ddof=1) / np.sqrt(len(per_game))
    out['brier']['analytic_ci_lo'] = float(per_game.mean() - 1.96 * se)
    out['brier']['analytic_ci_hi'] = float(per_game.mean() + 1.96 * se)
    return out


def main():
    hist = build_hist()
    print("\nRunning one aligned walk-forward for all three models...")
    keys, y_true, probs, coverage = walk_forward_aligned(hist)

    print(f"\nRow coverage (games each model could evaluate on its own):")
    for name in MODELS:
        print(f"  {name:<10}{coverage[name]}")
    print(f"  {'common':<10}{coverage['common']}   <- games usable by all three")
    print(f"  {'PAIRED':<10}{len(y_true)}   <- games actually compared")
    if coverage['common'] != min(coverage[n] for n in MODELS):
        print("  NOTE: the models do NOT all see the same games on their own; the "
              "paired comparison below is restricted to those they share.")

    points = {name: metric_set(y_true, p) for name, p in probs.items()}
    print("\nFull-sample metrics on the paired set:")
    print(f"{'model':<10}{'Brier':<12}{'LogLoss':<12}{'Reliab.':<13}{'Resol.':<12}")
    for name, m in points.items():
        print(f"{name:<10}{m['brier']:<12.6f}{m['log_loss']:<12.6f}"
              f"{m['reliability']:<13.6f}{m['resolution']:<12.6f}")

    payload = {
        'model_version': MODEL_VERSION,
        'backtest_seasons': BACKTEST_SEASONS,
        'n_games': int(len(y_true)),
        'n_resamples': N_RESAMPLES,
        'seed': SEED,
        'coverage': coverage,
        'full_sample': points,
        'comparisons': {},
    }

    for label, a, b in COMPARISONS:
        print(f"\n=== {label} ({N_RESAMPLES} paired resamples) ===")
        diffs = paired_bootstrap(y_true, probs[a], probs[b])
        res = summarise(points[a], points[b], diffs, y_true, probs[a], probs[b])
        payload['comparisons'][f'{a}_vs_{b}'] = {'label': label, 'metrics': res}

        print(f"{'metric':<13}{'diff':<13}{'95% CI':<26}{'verdict'}")
        for key, _, _ in METRICS:
            r = res[key]
            ci = f"[{r['ci_lo']:+.6f}, {r['ci_hi']:+.6f}]"
            print(f"{r['label']:<13}{r['difference']:<+13.6f}{ci:<26}{r['verdict']}")
        br = res['brier']
        print(f"  Brier cross-check (analytic paired SE): "
              f"[{br['analytic_ci_lo']:+.6f}, {br['analytic_ci_hi']:+.6f}]")

    DATA_DIR.mkdir(exist_ok=True)
    out = DATA_DIR / 'bootstrap_brier_gap.json'
    with open(out, 'w') as f:
        json.dump(payload, f, indent=2)
    print(f"\nSaved to {out}")
    print("A difference counts only when its 95% interval excludes zero.")


if __name__ == '__main__':
    main()
