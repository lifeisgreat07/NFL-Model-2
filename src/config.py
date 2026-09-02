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
# dropbacks in their sample.
#
# Full honest history, because this constant has been through three
# different states and the truth is more useful than the cleanest-sounding
# one:
#   1. Originally 8, chosen by convention -- never backtested at all.
#   2. Retuned to 96 (2026-08, Stage 2): adopted despite the confirmatory
#      accuracy delta's bootstrap CI including zero, because the direction
#      (higher k better) was at least consistent across accuracy and log
#      loss at the time.
#   3. That retune turned out not to reproduce: by 2026-08-31, two things
#      had changed underneath it (OL continuity removed, Stage 6; backtest
#      switched to weekly refitting, Stage 9) so it was evaluating a
#      different model than the one actually live, and separately
#      build_qb_ratings' shrinkage target was found to be leaking future
#      weeks into every "as of" prediction (fixed the same day, see
#      ratings_engine.py -- checked directly, that leak was NOT what broke
#      the reproduction, it's just also fixed now). A fresh retune under
#      the current, fixed config -- real script, src/tune_qb_shrink_k.py,
#      committed and reusable regardless of this outcome -- grid-searched
#      k=1 to 2048 on validation seasons 2022-2023 only (broad flat
#      optimum k=64-256 on log loss, winner k=128) and confirmed on
#      held-out 2024-2025 (n=544): k=8 won accuracy (63.79% vs 63.60%),
#      Brier (0.224668 vs 0.224831), and AUC (0.686688 vs 0.683713); k=128
#      only edged log loss (0.641264 vs 0.641721). Paired bootstrap (5000
#      resamples): accuracy delta -0.18pt, 95% CI [-1.65, +1.29] --
#      includes zero. Neither retuned value (96 or 128) has consistent
#      support across metrics against the original k=8, so reverted to
#      k=8 as the more defensible default: it's the one that isn't
#      relying on a single-metric edge inside a statistically
#      insignificant result. Revisit if/when more season data accumulates
#      and the confirmatory sample is large enough to actually resolve
#      this.
QB_SHRINK_K = 8

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
#   v2.3 (2026-08-31) -- fixed a real leak in build_qb_ratings (shrinkage
#                          target was a global average, not cutoff-scoped;
#                          see ratings_engine.py); QB_SHRINK_K re-tuned
#                          96->128 via a real, committed, reproducible
#                          script (src/tune_qb_shrink_k.py), superseding
#                          the prior retune whose own numbers couldn't be
#                          reproduced from anything in this repo
#   v2.4 (2026-08-31) -- QB shrinkage investigation: found the original
#                          k=96 decision didn't reproduce under later
#                          config changes (OL removal, weekly refit);
#                          the fresh retune above (k=128) then turned out
#                          inconsistent across metrics on confirmatory
#                          data too (k=8 won 3 of 4); reverted to k=8 as
#                          the defensible default. tune_qb_shrink_k.py
#                          stays committed -- real, reusable methodology,
#                          independent of what it concluded this time.
MODEL_VERSION = "2.4"

TRAIN_SEASONS = [2020, 2021, 2022, 2023, 2024, 2025]
BACKTEST_SEASONS = [2022, 2023, 2024, 2025]

# Canonical backtest accuracy, current (leak-fixed, k=8) code, n=1087 games
# across BACKTEST_SEASONS. This is the reference point drift monitoring
# compares real, live 2026+ results against -- deliberately a fixed,
# documented value rather than something recomputed live each week, so the
# comparison target doesn't silently move along with whatever's being
# checked against it. Update this only when a real, intentional backtest
# re-run changes the canonical number (and note it in the changelog above
# when you do), not automatically.
BACKTEST_ACCURACY = {'model_a': 0.628, 'model_b': 0.682}
