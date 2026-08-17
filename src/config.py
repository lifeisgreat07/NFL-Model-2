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
# better). Re-used for QB ratings without a separate QB-specific sweep --
# worth testing independently if QB feature performance plateaus.
RECENCY_HALF_LIFE = 16

# Shrinkage pseudo-count for QB ratings: a QB's trailing rating is blended
# toward league average, weighted as if there were this many league-average
# dropbacks in their sample. Chosen by convention (not backtested) --
# flagged as a gap, same as the original alpha=200 was.
QB_SHRINK_K = 8

# Minimum plays required before computing a team rating cutoff (avoids
# degenerate very-early-season fits).
MIN_PLAYS_FOR_RATING = 200

# Seasons used for training/backtesting. Extend this list each year after
# a season completes.
TRAIN_SEASONS = [2020, 2021, 2022, 2023, 2024, 2025]
BACKTEST_SEASONS = [2022, 2023, 2024, 2025]
