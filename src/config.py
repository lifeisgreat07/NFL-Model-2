"""
Model configuration -- every constant here was chosen via backtest,
not convention. If you change one, re-run backtest.py and update the
comment with the new justification before trusting the result.
"""

# Ridge regularization strength for the opponent-adjusted team rating
# regression. Tested [1,3,5,10,15,25,40,50,100,200,400,800,1600] via
# chronological backtest (2022-2025 holdout) on log loss. Plateaus flat
# from 1-15, degrades above ~100. 15 chosen as a stable point in the flat
# region rather than the literal minimum, to avoid overfitting to backtest
# noise at the extreme low end.
RIDGE_ALPHA = 15.0

# Recency half-life in games for both team and QB ratings. Tested [6,10,16]
# for team ratings; 16 won on log loss (shorter windows were noisier, not
# better). Independently re-validated for QB ratings via a joint grid
# search with QB_SHRINK_K (2026-08 Stage 2 QB Model V2 pass, validation
# seasons 2022-2023, confirmed on held-out 2024-2025): 16 remains
# near-optimal for QB too, so no change was needed here.
RECENCY_HALF_LIFE = 16

# Shrinkage pseudo-count for QB ratings: a QB's trailing rating is blended
# toward league average, weighted as if there were this many league-average
# dropbacks in their sample. Originally 8, chosen by convention with no
# backtest -- flagged as a known gap in the methodology doc.
#
# Re-tuned 2026-08 (Stage 2 QB Model V2): joint grid over half-life x
# shrink_k on validation seasons 2022-2023 found a broad, flat optimum
# around k=96-128 (log loss ~0.658 vs. 0.661 at k=8) -- not a fragile
# single-point peak. Confirmed on truly held-out 2024-2025 (never touched
# during tuning): 63.42% vs. 63.05% accuracy (+0.37pt), log loss 0.6482
# vs. 0.6485. Paired bootstrap (5000 resamples) on the confirmatory set:
# 95% CI [-0.92, +1.65] -- NOT statistically significant at this sample
# size. Adopted anyway: k=96 replaces an admittedly-arbitrary constant
# with one chosen via real validation/test separation, which is a
# methodological correctness improvement independent of whether the
# accuracy delta itself is provably real. Revisit significance once more
# season data accumulates.
QB_SHRINK_K = 96

# Minimum plays required before computing a team rating cutoff (avoids
# degenerate very-early-season fits).
MIN_PLAYS_FOR_RATING = 200

# Seasons used for training/backtesting. Extend this list each year after
# a season completes.
# Model version -- bump this whenever the feature set or a tuned constant
# changes, so saved predictions can be traced to exactly what produced
# them. History:
#   v1.0 (2026-08-17) -- initial 3-feature model (off, def, qb)
#   v1.1 (2026-08-17) -- added OL continuity + QB-change (5 features)
#   v2.0 (2026-08-24, Stage 2)  -- QB_SHRINK_K retuned 8->96
#   v2.1 (2026-08-24, Stage 6)  -- OL continuity removed (4 features: off, def, qb, qbchange)
#   v2.2 (2026-08-24, Stage 9)  -- backtest methodology switched to weekly refitting
#                                   (no live-model code change, live pipeline already did this)
MODEL_VERSION = "2.2"

TRAIN_SEASONS = [2020, 2021, 2022, 2023, 2024, 2025]
BACKTEST_SEASONS = [2022, 2023, 2024, 2025]
