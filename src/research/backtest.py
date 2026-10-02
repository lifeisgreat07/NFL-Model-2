"""
Chronological backtest -- run this to re-validate the model whenever you
change config.py or add a season of real data. Not run automatically by
the weekly routine (too expensive to do every week); run manually every
few weeks or once per season.

Fixed from an earlier broken version that hardcoded a local sandbox path
and referenced sr_off_matchup/sr_def_matchup features that don't exist
anywhere in this repo's actual pipeline (leftover from an early draft).
This version is self-contained and uses only ratings_engine.py + data_loader.py,
matching what weekly_update.py actually does.

Usage: python -m src.research.backtest
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score

from src.pipeline.config import BACKTEST_SEASONS, TRAIN_SEASONS
from src.pipeline.data_loader import load_plays, load_schedule, load_snap_counts
from src.pipeline.model_specs import (
    MARKET_FEATURES,
    MODEL_A_FEATURES,
    MODEL_B_FEATURES,
    ModelSpec,
    walk_forward,
)
from src.pipeline.ol_continuity import compute_ol_continuity_lookup
from src.pipeline.ratings_engine import build_qb_ratings, build_team_ratings, prep_plays
from src.pipeline.weekly_update import (  # reuse the same feature logic
    build_historical_features,
    build_qb_change_lookup,
)


def backtest(hist, features, test_seasons, refit_every_n_weeks=1, return_raw=False):
    """Weekly-refitting walk-forward evaluation (default: refit every week).
    Adopted 2026-08 (Stage 9) after confirming it matches the live model's
    actual behavior -- weekly_update.py always trains on all real data
    available up to "now" on every run, so it was ALREADY effectively
    refitting weekly in production. This backtest function previously only
    refit once per season, which meant our evaluation methodology didn't
    match how the live model actually operates. Tested against the
    season-level version: tied or better on every metric on the true
    confirmatory holdout (2024-2025), though the accuracy delta itself
    (+0.37pt) was not statistically significant (bootstrap 95% CI
    [-0.37, +1.10]). Adopted anyway for the same reason as the QB
    shrinkage fix: it's the methodologically correct practice (using more
    real available data before each prediction) independent of whether
    this specific delta is provably real.

    Pass refit_every_n_weeks=None to restore the old season-level-only
    behavior for comparison.

    Since Stage 33 item 21 the loop itself is `walk_forward` in
    src/pipeline/model_specs.py, shared with the live fit. `features` is a
    list of columns (fitted as the published incumbent, C=1.0 with an L2
    penalty) or a ModelSpec, for a candidate with other settings.
    """
    spec = features if isinstance(features, ModelSpec) else ModelSpec(tuple(features))
    scored, all_prob = walk_forward(spec, hist, test_seasons, refit_every_n_weeks=refit_every_n_weeks)
    all_true = np.array(scored['home_win'].values)
    pred = (all_prob >= 0.5).astype(int)
    metrics = {
        'n': len(all_true),
        'accuracy': accuracy_score(all_true, pred),
        'log_loss': log_loss(all_true, all_prob),
        'brier': brier_score_loss(all_true, all_prob),
        'auc': roc_auc_score(all_true, all_prob),
    }
    if return_raw:
        return metrics, all_true, all_prob
    return metrics


def main():
    print("Loading data and building historical features (this takes a while)...")
    raw = load_plays(TRAIN_SEASONS)
    plays, week_keys, week_to_idx = prep_plays(raw)
    team_ratings_by_week = build_team_ratings(plays, week_keys, upto_cutoff_i=None)
    qb = build_qb_ratings(raw)
    snap_counts = load_snap_counts(TRAIN_SEASONS)
    ol_lookup = compute_ol_continuity_lookup(snap_counts)
    qb_change_lookup = build_qb_change_lookup(qb, TRAIN_SEASONS)
    schedules_by_season = {s: load_schedule(s) for s in TRAIN_SEASONS}
    hist = build_historical_features(plays, week_keys, week_to_idx, team_ratings_by_week,
                                       qb, schedules_by_season, ol_lookup=ol_lookup, qb_change_lookup=qb_change_lookup)
    print(f"{len(hist)} historical games built.\n")

    print(f"{'Model':<40}{'Accuracy':<10}{'LogLoss':<10}{'Brier':<8}{'AUC':<8}")
    results = {}
    for name, features in [
        ('Football-only (off+def+qb)', ['off_matchup', 'def_matchup', 'qb_matchup']),
        ('LIVE MODEL A (off+def+qb+qbchange)', list(MODEL_A_FEATURES)),
        ('[reference only] + OL continuity', ['off_matchup', 'def_matchup', 'qb_matchup', 'qb_change_diff', 'ol_continuity_diff']),
        ('Market alone', list(MARKET_FEATURES)),
        ('LIVE MODEL B (+ market)', list(MODEL_B_FEATURES)),
        ('[reference only] + OL + market', ['off_matchup', 'def_matchup', 'qb_matchup', 'qb_change_diff', 'ol_continuity_diff', 'spread_line']),
    ]:
        m = backtest(hist, features, BACKTEST_SEASONS)
        results[name] = m
        print(f"{name:<40}{m['accuracy']:<10.4f}{m['log_loss']:<10.4f}{m['brier']:<8.4f}{m['auc']:<8.4f}")

    out_dir = Path(__file__).parents[2] / 'results'
    out_dir.mkdir(exist_ok=True)
    pd.DataFrame(results).T.to_csv(out_dir / 'backtest_metrics.csv')
    print(f"\nSaved to {out_dir / 'backtest_metrics.csv'}")


if __name__ == '__main__':
    main()
