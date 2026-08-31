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
# Re-tuned 2026-08-31, run via src/tune_qb_shrink_k.py (a real, committed,
# reproducible script -- see it for the exact method). This supersedes the
# prior "k=8 -> 96" retune: that decision's own supporting numbers
# (63.42% vs. 63.05% confirmatory accuracy) could not be reproduced from
# anything in this repo when checked, for reasons unrelated to the leak
# below -- most likely a script or data snapshot that no longer exists.
# Also, by the time this ran, two things had changed underneath the
# original retune: OL continuity was removed from the live feature set
# (Stage 6) and the backtest switched to weekly refitting (Stage 9), so
# even a reproduced version of that retune would've been evaluating a
# different model than the one actually live today. And separately,
# build_qb_ratings' league-average shrinkage target was found to leak
# future weeks into every "as of" prediction (fixed the same day, see
# ratings_engine.py) -- checked directly, that leak did NOT explain the
# irreproducibility above (near-identical k=8-vs-96 comparison with the
# leak present or fixed), but it's fixed regardless and this retune runs
# under the fixed code.
#
# Grid search (1 to 2048) on validation seasons 2022-2023 only, current
# live 4-feature model, weekly-refit backtest: broad flat optimum roughly
# k=64-256 (log loss 0.6547-0.6555), winner k=128 (val log loss 0.654660
# vs. 0.658188 at k=8). Confirmed on held-out 2024-2025 (n=544): k=128
# accuracy 63.60%, log loss 0.641264; k=8 accuracy 63.79%, log loss
# 0.641721; k=96 (old default) accuracy 63.05%, log loss 0.641058 --
# genuinely mixed across metrics, no k in the whole grid dominates.
# Paired bootstrap (5000 resamples), k=128 vs. k=8 on confirmatory:
# accuracy delta -0.18pt, 95% CI [-1.65, +1.29] -- NOT statistically
# significant, same epistemic status as the original retune. Adopted
# anyway for the same reason as before: k=128 is what the validation-only
# selection criterion (log loss) actually picked, via a method that's now
# reproducible end to end, independent of whether this specific delta is
# provably real. Revisit once more season data accumulates.
QB_SHRINK_K = 128

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
MODEL_VERSION = "2.3"

TRAIN_SEASONS = [2020, 2021, 2022, 2023, 2024, 2025]
BACKTEST_SEASONS = [2022, 2023, 2024, 2025]
