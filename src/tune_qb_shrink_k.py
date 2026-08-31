"""
QB_SHRINK_K tuning: validation-then-confirm grid search.

Fills a real documentation gap: ratings_engine.py's module docstring has
referenced a "METHODOLOGY.md" with "the real, run numbers" that never
actually existed in this repo, and the QB_SHRINK_K comment in config.py
described a prior retune (k=8 -> 96) whose supporting numbers turned out
not to be reproducible from anything committed here. This script is that
missing methodology, runnable end to end, so the config.py value can
always be traced back to a real backtest instead of a comment.

Methodology (same discipline as the original retune, restated so it's
never ambiguous again):
  1. Grid search QB_SHRINK_K on VALIDATION_SEASONS only (2022-2023),
     using the current live 4-feature model (off+def+qb+qbchange) and the
     current weekly-refitting backtest methodology. Selection criterion:
     lowest validation log loss (matches the original tuning's stated
     criterion -- "found a broad, flat optimum ... on log loss").
  2. The validation winner is then evaluated on CONFIRMATORY_SEASONS
     (2024-2025), which the grid search never saw, to check the choice
     actually generalizes rather than overfitting the validation split.
  3. Both are also reported for k=8 (the pre-2026-08 default) so the
     size of any real improvement is visible directly, not asserted.

Run: python src/tune_qb_shrink_k.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from data_loader import load_plays, load_schedule, load_snap_counts
from ratings_engine import prep_plays, build_team_ratings, build_qb_ratings
import ratings_engine
from config import TRAIN_SEASONS
from weekly_update import build_historical_features, build_qb_change_lookup
from ol_continuity import compute_ol_continuity_lookup
from backtest import backtest

VALIDATION_SEASONS = [2022, 2023]
CONFIRMATORY_SEASONS = [2024, 2025]
LIVE_MODEL_A_FEATURES = ['off_matchup', 'def_matchup', 'qb_matchup', 'qb_change_diff']

# Broad geometric-ish sweep -- wide enough to find an interior optimum
# (or confirm none exists) rather than assuming the answer is near the
# previous default.
K_GRID = [1, 2, 4, 8, 12, 16, 24, 32, 48, 64, 96, 128, 160, 192, 256, 320, 384, 512, 768, 1024, 1536, 2048]


def hist_for_k(k, plays, week_keys, week_to_idx, team_ratings_by_week, raw, schedules_by_season, ol_lookup):
    ratings_engine.QB_SHRINK_K = k  # trailing_rating() reads this module global at call time
    qb = build_qb_ratings(raw)
    qb_change_lookup = build_qb_change_lookup(qb, TRAIN_SEASONS)
    return build_historical_features(plays, week_keys, week_to_idx, team_ratings_by_week,
                                       qb, schedules_by_season, ol_lookup=ol_lookup, qb_change_lookup=qb_change_lookup)


def main():
    print("Loading data once, reused across the whole grid...")
    raw = load_plays(TRAIN_SEASONS)
    plays, week_keys, week_to_idx = prep_plays(raw)
    team_ratings_by_week = build_team_ratings(plays, week_keys, upto_cutoff_i=None)
    snap_counts = load_snap_counts(TRAIN_SEASONS)
    ol_lookup = compute_ol_continuity_lookup(snap_counts)
    schedules_by_season = {s: load_schedule(s) for s in TRAIN_SEASONS}

    print(f"\nStep 1: grid search on VALIDATION_SEASONS={VALIDATION_SEASONS} only (log loss is the selection criterion)\n")
    print(f"{'k':<8}{'val_acc':<12}{'val_logloss':<14}{'val_brier':<12}{'val_auc':<10}{'n':<6}")
    val_rows = []
    for k in K_GRID:
        hist = hist_for_k(k, plays, week_keys, week_to_idx, team_ratings_by_week, raw, schedules_by_season, ol_lookup)
        m = backtest(hist, LIVE_MODEL_A_FEATURES, VALIDATION_SEASONS)
        val_rows.append({'k': k, **m})
        print(f"{k:<8}{m['accuracy']:<12.6f}{m['log_loss']:<14.6f}{m['brier']:<12.6f}{m['auc']:<10.6f}{m['n']:<6}")

    val_df = pd.DataFrame(val_rows).set_index('k')
    winner_k = val_df['log_loss'].idxmin()
    print(f"\nValidation winner (lowest log loss): k={winner_k} (val log loss {val_df.loc[winner_k, 'log_loss']:.6f})")

    print(f"\nStep 2: confirm on true held-out CONFIRMATORY_SEASONS={CONFIRMATORY_SEASONS} "
          f"(never touched during the grid search above)\n")
    shortlist = sorted(set([winner_k, 8, 96]))  # winner, pre-2026-08 default, prior (unreproducible) default
    print(f"{'k':<8}{'confirm_acc':<14}{'confirm_logloss':<18}{'confirm_brier':<16}{'confirm_auc':<12}{'n':<6}")
    confirm_rows = []
    for k in shortlist:
        hist = hist_for_k(k, plays, week_keys, week_to_idx, team_ratings_by_week, raw, schedules_by_season, ol_lookup)
        m = backtest(hist, LIVE_MODEL_A_FEATURES, CONFIRMATORY_SEASONS)
        confirm_rows.append({'k': k, **m})
        tag = " <- validation winner" if k == winner_k else ""
        print(f"{k:<8}{m['accuracy']:<14.6f}{m['log_loss']:<18.6f}{m['brier']:<16.6f}{m['auc']:<12.6f}{m['n']:<6}{tag}")

    out_dir = Path(__file__).parent.parent / 'results'
    out_dir.mkdir(exist_ok=True)
    val_df.to_csv(out_dir / 'qb_shrink_k_validation.csv')
    pd.DataFrame(confirm_rows).set_index('k').to_csv(out_dir / 'qb_shrink_k_confirmatory.csv')
    print(f"\nSaved to {out_dir / 'qb_shrink_k_validation.csv'} and {out_dir / 'qb_shrink_k_confirmatory.csv'}")
    print(f"\nRECOMMENDATION: QB_SHRINK_K = {winner_k} (picked on validation only, confirmed above on held-out data)")


if __name__ == '__main__':
    main()
