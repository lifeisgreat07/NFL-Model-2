"""
Stage 5's evaluation rules, as code. Every model comparison in the Stage 5
family goes through here, so the rules below cannot be applied differently
to a result that happens to look good.

The rules are fixed in experiments/stage5/registry.json BEFORE any result is
computed, and this module reads them from there rather than restating them:

  * Walk-forward, weekly refit -- the same structure as backtest.py and
    bootstrap_brier_gap.py. Train on every game strictly earlier, predict the
    week, move on.
  * PAIRED. Candidate and incumbent are scored on exactly the same games.
    Each trains on its own natural rows (as the live models do), but the test
    rows are the games BOTH can speak to, and the comparison refuses to run
    if the two arrays are not the same games in the same order.
  * Validation seasons screen, confirmation seasons decide. A candidate only
    reaches confirmation if its validation log loss beats the incumbent's, and
    every candidate that reaches confirmation spends one slot of the family's
    budget whatever happens next.
  * The confirmatory interval is not 95%. With m slots in the budget, each
    confirmatory test uses alpha/m (Bonferroni), so the bar is set by how many
    questions the family is allowed to ask, not by how many happen to be
    asked before something works. That is the difference between a search and
    a test.
  * The forward holdout season is never evaluated here. Refusing it is a
    raised error, not a convention, because the only protection a holdout has
    is that nobody looked.

Decision labels are the project's own: ACCEPT (interval excludes zero in the
candidate's favour), REJECT (excludes zero against it), INCONCLUSIVE
(contains zero), and NOT ADVANCED for a candidate that failed the validation
screen. decide() computes the label from the numbers; nothing downstream is
allowed to write one by hand.
"""
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / 'experiments' / 'stage5' / 'registry.json'

EPS = 1e-15


def load_registry(path=REGISTRY_PATH):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


class ForwardHoldoutError(RuntimeError):
    """Raised when anything asks to evaluate on the forward holdout season."""


def guard_seasons(seasons, registry):
    forbidden = registry['protocol']['forward_holdout_season']
    touched = [s for s in seasons if s >= forbidden]
    if touched:
        raise ForwardHoldoutError(
            f"season(s) {touched} are the forward holdout (>= {forbidden}). Stage 5 "
            "may not evaluate on them until the season is over and the forward "
            "test is run as its own registered step."
        )


def confirmatory_level(registry):
    p = registry['protocol']
    return 1.0 - p['alpha'] / p['budget_m']


def per_game_losses(y, p):
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    y = np.asarray(y, dtype=float)
    ll = -(y * np.log(p) + (1 - y) * np.log(1 - p))
    br = (p - y) ** 2
    return ll, br


def walk_forward(games, feature_sets, test_seasons, min_train=50):
    """Aligned weekly-refit walk-forward for several feature sets at once.

    games: DataFrame with 'season', 'week', 'home_win', 'game_id' and every
    feature column named in feature_sets. feature_sets: {name: [columns]}.

    Returns (game_ids, y, {name: probs}). Test rows are the games where EVERY
    feature set is complete; each model trains on its own complete rows.
    """
    games = games.sort_values(['season', 'week', 'game_id']).reset_index(drop=True)
    all_cols = sorted({c for cols in feature_sets.values() for c in cols})
    common = games.dropna(subset=all_cols + ['home_win'])
    own = {n: games.dropna(subset=list(c) + ['home_win']) for n, c in feature_sets.items()}

    ids, ys = [], []
    probs = {n: [] for n in feature_sets}
    for season in test_seasons:
        for w in sorted(common.loc[common['season'] == season, 'week'].unique()):
            test = common[(common['season'] == season) & (common['week'] == w)]
            fitted = {}
            for n, cols in feature_sets.items():
                d = own[n]
                train = d[(d['season'] < season) | ((d['season'] == season) & (d['week'] < w))]
                if len(train) < min_train:
                    fitted = None
                    break
                m = LogisticRegression(max_iter=1000)
                m.fit(train[list(cols)].values, train['home_win'].values)
                fitted[n] = m
            if fitted is None:
                continue
            for n, cols in feature_sets.items():
                probs[n].extend(fitted[n].predict_proba(test[list(cols)].values)[:, 1])
            ys.extend(test['home_win'].values)
            ids.extend(test['game_id'].tolist())
    y = np.asarray(ys, dtype=float)
    out = {n: np.asarray(v, dtype=float) for n, v in probs.items()}
    for n, p in out.items():
        assert len(p) == len(y), f"{n}: {len(p)} predictions for {len(y)} games"
    return ids, y, out


def paired_bootstrap(y, p_cand, p_inc, n_resamples, seed):
    """Resampled (candidate - incumbent) mean log loss and Brier. Negative favours the candidate."""
    ll_c, br_c = per_game_losses(y, p_cand)
    ll_i, br_i = per_game_losses(y, p_inc)
    d_ll, d_br = ll_c - ll_i, br_c - br_i
    rng = np.random.default_rng(seed)
    n = len(y)
    idx = rng.integers(0, n, size=(n_resamples, n))
    return d_ll, d_br, d_ll[idx].mean(axis=1), d_br[idx].mean(axis=1)


def interval(samples, level):
    tail = (1 - level) / 2 * 100
    lo, hi = np.percentile(samples, [tail, 100 - tail])
    return float(lo), float(hi)


def label_from_interval(lo, hi):
    if hi < 0:
        return 'ACCEPT'
    if lo > 0:
        return 'REJECT'
    return 'INCONCLUSIVE'


def compare(y, p_cand, p_inc, level, n_resamples, seed):
    d_ll, d_br, bs_ll, bs_br = paired_bootstrap(y, p_cand, p_inc, n_resamples, seed)
    ll_lo, ll_hi = interval(bs_ll, level)
    br_lo, br_hi = interval(bs_br, level)
    ll95 = interval(bs_ll, 0.95)
    # Closed-form cross-check on the log-loss interval: the difference of
    # means is a mean of per-game differences. If the bootstrap and this
    # disagree badly the resampling is wired wrong.
    se = d_ll.std(ddof=1) / np.sqrt(len(d_ll))
    return {
        'n_games': int(len(y)),
        'log_loss_candidate': float(per_game_losses(y, p_cand)[0].mean()),
        'log_loss_incumbent': float(per_game_losses(y, p_inc)[0].mean()),
        'brier_candidate': float(per_game_losses(y, p_cand)[1].mean()),
        'brier_incumbent': float(per_game_losses(y, p_inc)[1].mean()),
        'accuracy_candidate': float(((p_cand >= 0.5) == (y == 1)).mean()),
        'accuracy_incumbent': float(((p_inc >= 0.5) == (y == 1)).mean()),
        'log_loss_diff': float(d_ll.mean()),
        'log_loss_ci': [ll_lo, ll_hi],
        'log_loss_ci_95': list(ll95),
        'log_loss_ci_analytic_95': [float(d_ll.mean() - 1.96 * se), float(d_ll.mean() + 1.96 * se)],
        'brier_diff': float(d_br.mean()),
        'brier_ci': [br_lo, br_hi],
        'ci_level': level,
    }


def decide(validation, confirmation):
    """The label, from the numbers. confirmation is None when the screen failed."""
    if validation['log_loss_diff'] >= 0:
        return 'NOT ADVANCED'
    if confirmation is None:
        raise ValueError("candidate passed the validation screen but has no confirmation result")
    lo, hi = confirmation['log_loss_ci']
    return label_from_interval(lo, hi)
