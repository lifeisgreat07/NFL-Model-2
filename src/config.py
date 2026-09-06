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
# changes, so saved predictions can be traced to exactly what produced them.
#
# The history below used to live in this comment. It is a real list now
# because the dashboard's Changelog page is generated from it, and a page
# rendered out of a Python comment is the "prose drifts" failure this project
# has already been burned by: nothing would have connected the words on the
# page to anything, and reformatting the comment would have silently emptied
# it. tests/test_version_history.py holds the two ends together -- every
# release needs an entry, and MODEL_VERSION has to be the newest one.
#
# One thing was dropped in the move. Three entries carried a stage number
# ("v2.0 (2026-08-24, Stage 2)"). Those pointed at a plan that has since been
# renumbered twice, so on a public page they would read as the CURRENT Stage 2
# and mean something entirely different. The dates and the substance are the
# durable part; the stage labels were not.
MODEL_VERSION = "2.4"

VERSION_HISTORY = [
    {
        'version': '2.4',
        'date': '2026-08-31',
        'headline': 'Reverted QB shrinkage to k=8 after the retune failed to hold up',
        'detail': (
            "Investigated QB shrinkage properly and found the original k=96 "
            "decision did not reproduce under later config changes (OL "
            "removal, weekly refitting). The fresh retune to k=128 then turned "
            "out inconsistent across metrics on confirmatory data as well -- "
            "k=8 won three of four. Reverted to k=8 as the defensible default. "
            "src/tune_qb_shrink_k.py stays committed: the methodology is real "
            "and reusable regardless of what it concluded this time."
        ),
    },
    {
        'version': '2.3',
        'date': '2026-08-31',
        'headline': 'Fixed a real leak in build_qb_ratings',
        'detail': (
            "The shrinkage target was a global average rather than being "
            "cutoff-scoped, so a QB rating could see beyond its own cutoff "
            "(see ratings_engine.py). With the leak closed, QB_SHRINK_K was "
            "re-tuned 96 to 128 by a committed, reproducible script -- "
            "superseding an earlier retune whose numbers could not be "
            "reproduced from anything in this repository."
        ),
    },
    {
        'version': '2.2',
        'date': '2026-08-24',
        'headline': 'Backtest switched to weekly refitting',
        'detail': (
            "A methodology change with no live-model code change behind it: "
            "the live pipeline already refit weekly, and the backtest was the "
            "thing out of step. Recorded as a version bump because it moves "
            "the published numbers even though the model itself is untouched."
        ),
    },
    {
        'version': '2.1',
        'date': '2026-08-24',
        'headline': 'OL continuity removed -- down to four features',
        'detail': (
            "Offensive-line continuity did not earn its place. Feature set "
            "back to off, def, qb and qb-change."
        ),
    },
    {
        'version': '2.0',
        'date': '2026-08-24',
        'headline': 'QB_SHRINK_K retuned 8 to 96',
        'detail': (
            "Superseded twice over: v2.3 re-tuned it again after finding a "
            "leak, and v2.4 reverted the whole line of reasoning back to k=8. "
            "Kept here because a changelog that quietly deletes the decisions "
            "that were later reversed is not a changelog."
        ),
    },
    {
        'version': '1.1',
        'date': '2026-08-17',
        'headline': 'Added OL continuity and QB-change (five features)',
        'detail': "Both added on plausibility. One of them did not survive v2.1.",
    },
    {
        'version': '1.0',
        'date': '2026-08-17',
        'headline': 'Initial three-feature model',
        'detail': "Opponent-adjusted offence, defence and QB rating.",
    },
]

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
