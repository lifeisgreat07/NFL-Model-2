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

Usage: python src/backtest.py
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss, roc_auc_score

sys.path.insert(0, str(Path(__file__).parent))
from data_loader import load_plays, load_schedule, load_snap_counts
from ratings_engine import prep_plays, build_team_ratings, build_qb_ratings
from config import TRAIN_SEASONS, BACKTEST_SEASONS
from weekly_update import build_historical_features, build_qb_change_lookup  # reuse the same feature logic
from ol_continuity import compute_ol_continuity_lookup


def backtest(hist, features, test_seasons, refit_every_n_weeks=1):
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
    """
    hist = hist.sort_values(['season', 'week'])
    all_true, all_prob = [], []
    for test_season in test_seasons:
        d2 = hist.dropna(subset=list(features) + ['home_win'])
        season_weeks = sorted(d2[d2['season'] == test_season]['week'].unique())
        if not season_weeks:
            continue
        if refit_every_n_weeks is None:
            train = d2[d2['season'] < test_season]
            test = d2[d2['season'] == test_season]
            if len(train) < 50 or len(test) == 0:
                continue
            m = LogisticRegression(max_iter=1000)
            m.fit(train[list(features)].values, train['home_win'].values)
            probs = m.predict_proba(test[list(features)].values)[:, 1]
            all_true.extend(test['home_win'].values)
            all_prob.extend(probs)
        else:
            last_refit_week = None
            model = None
            for w in season_weeks:
                if last_refit_week is None or (w - last_refit_week) >= refit_every_n_weeks:
                    train = d2[(d2['season'] < test_season) | ((d2['season'] == test_season) & (d2['week'] < w))]
                    if len(train) < 50:
                        continue
                    model = LogisticRegression(max_iter=1000)
                    model.fit(train[list(features)].values, train['home_win'].values)
                    last_refit_week = w
                if model is None:
                    continue
                test_w = d2[(d2['season'] == test_season) & (d2['week'] == w)]
                if len(test_w) == 0:
                    continue
                probs = model.predict_proba(test_w[list(features)].values)[:, 1]
                all_true.extend(test_w['home_win'].values)
                all_prob.extend(probs)
    all_true, all_prob = np.array(all_true), np.array(all_prob)
    pred = (all_prob >= 0.5).astype(int)
    return {
        'n': len(all_true),
        'accuracy': accuracy_score(all_true, pred),
        'log_loss': log_loss(all_true, all_prob),
        'brier': brier_score_loss(all_true, all_prob),
        'auc': roc_auc_score(all_true, all_prob),
    }


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
        ('LIVE MODEL A (off+def+qb+qbchange)', ['off_matchup', 'def_matchup', 'qb_matchup', 'qb_change_diff']),
        ('[reference only] + OL continuity', ['off_matchup', 'def_matchup', 'qb_matchup', 'qb_change_diff', 'ol_continuity_diff']),
        ('Market alone', ['spread_line']),
        ('LIVE MODEL B (+ market)', ['off_matchup', 'def_matchup', 'qb_matchup', 'qb_change_diff', 'spread_line']),
        ('[reference only] + OL + market', ['off_matchup', 'def_matchup', 'qb_matchup', 'qb_change_diff', 'ol_continuity_diff', 'spread_line']),
    ]:
        m = backtest(hist, features, BACKTEST_SEASONS)
        results[name] = m
        print(f"{name:<40}{m['accuracy']:<10.4f}{m['log_loss']:<10.4f}{m['brier']:<8.4f}{m['auc']:<8.4f}")

    out_dir = Path(__file__).parent.parent / 'results'
    out_dir.mkdir(exist_ok=True)
    pd.DataFrame(results).T.to_csv(out_dir / 'backtest_metrics.csv')
    print(f"\nSaved to {out_dir / 'backtest_metrics.csv'}")


if __name__ == '__main__':
    main()
