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
from weekly_update import build_historical_features  # reuse the same feature logic
from ol_continuity import compute_ol_continuity_lookup


def backtest(hist, features, test_seasons):
    all_true, all_prob = [], []
    for test_season in test_seasons:
        train = hist[hist['season'] < test_season].dropna(subset=list(features) + ['home_win'])
        test = hist[hist['season'] == test_season].dropna(subset=list(features) + ['home_win'])
        if len(train) < 50 or len(test) == 0:
            continue
        m = LogisticRegression(max_iter=1000)
        m.fit(train[list(features)].values, train['home_win'].values)
        probs = m.predict_proba(test[list(features)].values)[:, 1]
        all_true.extend(test['home_win'].values)
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
    schedules_by_season = {s: load_schedule(s) for s in TRAIN_SEASONS}
    hist = build_historical_features(plays, week_keys, week_to_idx, team_ratings_by_week,
                                       qb, schedules_by_season, ol_lookup=ol_lookup)
    print(f"{len(hist)} historical games built.\n")

    print(f"{'Model':<40}{'Accuracy':<10}{'LogLoss':<10}{'Brier':<8}{'AUC':<8}")
    results = {}
    for name, features in [
        ('Football-only (off+def+qb)', ['off_matchup', 'def_matchup', 'qb_matchup']),
        ('Football-only + OL continuity', ['off_matchup', 'def_matchup', 'qb_matchup', 'ol_continuity_diff']),
        ('Market alone', ['spread_line']),
        ('Football + OL + Market (blended)', ['off_matchup', 'def_matchup', 'qb_matchup', 'ol_continuity_diff', 'spread_line']),
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
