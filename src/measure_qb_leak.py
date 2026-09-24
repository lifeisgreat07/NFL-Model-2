"""
How much did the QB rating leak fixed in ec30887 actually move the backtest?

The leak: before ec30887 (2026-08-31), build_qb_ratings shrank every QB's
trailing rating toward ONE league average computed over the whole input --
in the backtest, every dropback from 2020 through 2025. So a 2022 week-5
prediction was shrunk toward a number that already knew about 2023, 2024 and
2025. The fix made the shrinkage target "league average as of this cutoff".

That fix shipped in the same PR as a retune of QB_SHRINK_K and a revert, so
its effect on the published numbers was never isolated. This script isolates
it, on today's code, with nothing else changed:

  * The feature table is built twice from ONE load of the data. The only
    difference between the two builds is the trailing_rating function handed
    to the feature builder: the shipped leak-free one, or the pre-fix one,
    reproduced verbatim from ec30887's parent (`git show ec30887~1:src/
    ratings_engine.py`, the body of trailing_rating) as leaky_trailing_rating
    below. Team ratings, schedules, QB_SHRINK_K and RECENCY_HALF_LIFE are
    shared, so nothing else can move.
  * Both tables go through bootstrap_brier_gap.walk_forward_aligned -- imported,
    not copied -- so the walk-forward is the one that produced the published
    Model B vs market interval.
  * The two runs must evaluate the same games in the same order with the same
    outcomes, or the comparison is refused. Pairing is asserted, not assumed.
  * Paired bootstrap, 5,000 resamples, the project's usual bar: a difference
    counts only when its 95% interval excludes zero.

Sign convention: every difference is (leaky - fixed). Brier and log loss are
lower-is-better, so a NEGATIVE difference means the leak made the model look
better than it really was.

Usage: python src/measure_qb_leak.py
Writes data/qb_leak_effect.json and prints a summary.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from config import (BACKTEST_SEASONS, MODEL_VERSION, QB_SHRINK_K,  # noqa: E402
                    RECENCY_HALF_LIFE, TRAIN_SEASONS)
from data_loader import load_plays, load_schedule  # noqa: E402
from ratings_engine import build_qb_ratings, build_team_ratings, prep_plays  # noqa: E402
from weekly_update import build_historical_features, build_qb_change_lookup  # noqa: E402
from bootstrap_brier_gap import (METRICS, N_RESAMPLES, SEED, metric_set,  # noqa: E402
                                 paired_bootstrap, summarise, walk_forward_aligned)

DATA_DIR = Path(__file__).parent.parent / 'data'
OUT = DATA_DIR / 'qb_leak_effect.json'

# The commit that fixed the leak. The case study cites it; the test checks the
# citation and this constant agree.
FIX_COMMIT = 'ec30887'

COMPARED = ('model_a', 'model_b')  # the market has no QB feature, so it cannot move


def leaky_trailing_rating(qb):
    """The pre-fix trailing_rating, reproduced from ec30887's parent.

    The only change from the shipped function is the shrinkage target:
    qb['league_avg'] is the mean over EVERY dropback in the input, where the
    shipped function uses the mean over dropbacks before the cutoff.
    """
    df = qb['plays']
    league_avg = qb['league_avg']

    def trailing_rating(player_id, cutoff_gwidx):
        prior = df[(df['passer_player_id'] == player_id) & (df['gwidx'] < cutoff_gwidx)]
        if len(prior) == 0:
            return league_avg
        distance = cutoff_gwidx - prior['gwidx'].values
        w = 0.5 ** (distance / RECENCY_HALF_LIFE)
        weighted_avg = np.average(prior['qb_epa'].values, weights=w)
        n_eff = w.sum()
        return (n_eff * weighted_avg + QB_SHRINK_K * league_avg) / (n_eff + QB_SHRINK_K)

    return trailing_rating


def build_both_tables():
    print("Loading play-by-play once for both builds...")
    raw = load_plays(TRAIN_SEASONS)
    plays, week_keys, week_to_idx = prep_plays(raw)
    team_ratings_by_week = build_team_ratings(plays, week_keys, upto_cutoff_i=None)
    schedules_by_season = {s: load_schedule(s) for s in TRAIN_SEASONS}

    tables = {}
    for variant in ('fixed', 'leaky'):
        qb = build_qb_ratings(raw)
        if variant == 'leaky':
            qb = dict(qb, trailing_rating=leaky_trailing_rating(qb))
        qb_change_lookup = build_qb_change_lookup(qb, TRAIN_SEASONS)
        tables[variant] = build_historical_features(
            plays, week_keys, week_to_idx, team_ratings_by_week, qb,
            schedules_by_season, ol_lookup=None, qb_change_lookup=qb_change_lookup,
        )
        print(f"  {variant}: {len(tables[variant])} historical games built")
    return tables


def provenance():
    """Where the numbers came from, the way calibration.json records it.

    A RECORD, NOT AN EXPLANATION. Booth re-ran this script twice on Linux
    while auditing #96: one run matched the Windows file in every figure the
    case study prints, the other had one fewer pick changing side per model.
    Nothing found says what separated those two runs, and it may be nothing
    this block records -- the second audit found its library versions matching the ones
    recorded here, and the first run predates this block. So matching versions do
    not promise a matching table; only the verdict has held in every run."""
    import importlib.metadata as md
    import platform

    def ver(pkg):
        try:
            return md.version(pkg)
        except Exception:
            return 'absent'

    return {
        'system': platform.system(),
        'platform': platform.platform(),
        'python': platform.python_version(),
        'numpy': ver('numpy'),
        'pandas': ver('pandas'),
        'scikit-learn': ver('scikit-learn'),
    }


def head_sha():
    try:
        return subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return None


def main():
    tables = build_both_tables()
    fixed, leaky = tables['fixed'], tables['leaky']

    # The two tables must describe the same games. Only QB-derived columns may
    # differ; if anything else moved, the experiment is not isolating the leak.
    assert list(fixed.index) == list(leaky.index), "the two builds produced different games"
    for col in fixed.columns:
        if col in ('qb_matchup', 'qb_change_diff'):
            continue
        a, b = fixed[col], leaky[col]
        same = (a == b) | (a.isna() & b.isna())
        assert bool(same.all()), f"column {col} differs between builds -- not an isolated change"

    moved = (fixed['qb_matchup'] - leaky['qb_matchup']).abs()
    # A vacuity guard: if the leaky function were accidentally the fixed one,
    # every number below would be a clean zero and read as "the leak did
    # nothing". Refuse to report that.
    assert moved.max() > 0, "leaky and fixed QB features are identical -- the leak was not reproduced"

    print("\nRunning the aligned walk-forward on each table...")
    k_f, y_f, p_f, cov_f = walk_forward_aligned(fixed)
    k_l, y_l, p_l, cov_l = walk_forward_aligned(leaky)
    assert k_f == k_l, "the two walk-forwards evaluated different games"
    assert np.array_equal(y_f, y_l), "the two walk-forwards saw different outcomes"

    payload = {
        'fix_commit': FIX_COMMIT,
        'measured_at': head_sha(),
        'provenance': provenance(),
        'model_version': MODEL_VERSION,
        'qb_shrink_k': QB_SHRINK_K,
        'backtest_seasons': BACKTEST_SEASONS,
        'n_games': int(len(y_f)),
        'n_resamples': N_RESAMPLES,
        'seed': SEED,
        'qb_matchup_abs_change': {
            'max': float(moved.max()),
            'mean': float(moved.mean()),
            'rows': int(moved.notna().sum()),
        },
        'models': {},
    }

    for name in COMPARED:
        pl, pf = p_l[name], p_f[name]
        point_l, point_f = metric_set(y_f, pl), metric_set(y_f, pf)
        diffs = paired_bootstrap(y_f, pl, pf)
        res = summarise(point_l, point_f, diffs, y_f, pl, pf)
        flips = int(((pl >= 0.5) != (pf >= 0.5)).sum())
        acc_l = float(((pl >= 0.5) == y_f).mean())
        acc_f = float(((pf >= 0.5) == y_f).mean())
        payload['models'][name] = {
            'picks_flipped': flips,
            'accuracy_leaky': acc_l,
            'accuracy_fixed': acc_f,
            'max_abs_prob_change': float(np.abs(pl - pf).max()),
            'metrics': res,
        }
        print(f"\n=== {name}: leaky - fixed ({N_RESAMPLES} paired resamples, n={len(y_f)}) ===")
        print(f"  picks that change side: {flips}")
        print(f"  accuracy: leaky {acc_l:.4f}  fixed {acc_f:.4f}")
        for key, _, _ in METRICS:
            r = res[key]
            print(f"  {r['label']:<12}{r['difference']:+.6f}  "
                  f"[{r['ci_lo']:+.6f}, {r['ci_hi']:+.6f}]  {r['verdict']}")

    DATA_DIR.mkdir(exist_ok=True)
    with open(OUT, 'w') as f:
        json.dump(payload, f, indent=2)
    print(f"\nSaved to {OUT}")


if __name__ == '__main__':
    main()
