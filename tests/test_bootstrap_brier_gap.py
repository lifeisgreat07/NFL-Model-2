"""
Tests for src/bootstrap_brier_gap.py.

These cover the statistics only -- no play-by-play, no network. The expensive
half (one aligned walk-forward over six seasons) is exercised by running the
script; what matters here is that the inference underneath it is sound,
because a bootstrap that is subtly wrong still prints a confident interval and
nothing about the output looks broken.

The test that earns its place most is test_pairing_is_tighter_than_unpaired.
Pairing is the entire reason this script exists rather than a
two-sample comparison, and pairing done wrong -- arrays that don't line up,
or independent index draws for the two models -- produces a WIDER interval
that quietly turns a real difference into "inconclusive". That failure looks
exactly like an honest null result, which is the most dangerous kind of bug
this project could ship.

Run with: pytest tests/test_bootstrap_brier_gap.py -v
"""
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / 'src'))

from bootstrap_brier_gap import (  # noqa: E402
    METRICS, metric_set, paired_bootstrap, summarise,
)


# ============================================================
# Fixtures: two forecasters on the same games
# ============================================================
def make_pair(n=1200, sharper_noise=0.05, duller_noise=0.30, seed=7):
    """Two forecasters looking at the same games, one clearly better.

    Both are built from the same latent truth, so their errors are correlated
    the way two real NFL models' errors are -- which is the situation pairing
    exists to exploit."""
    rng = np.random.default_rng(seed)
    latent = rng.uniform(0.15, 0.85, n)
    y = (rng.random(n) < latent).astype(float)
    clip = lambda p: np.clip(p, 0.02, 0.98)
    sharp = clip(latent + rng.normal(0, sharper_noise, n))
    dull = clip(latent + rng.normal(0, duller_noise, n))
    return y, sharp, dull


# ============================================================
# metric_set
# ============================================================
def test_metric_set_reports_every_metric_the_summary_expects():
    y, sharp, _ = make_pair(300)
    m = metric_set(y, sharp)
    for key, _, _ in METRICS:
        assert key in m, f"metric_set is missing {key}, which summarise() will read"
        assert np.isfinite(m[key])


def test_a_sharper_forecaster_scores_a_lower_brier():
    y, sharp, dull = make_pair()
    assert metric_set(y, sharp)['brier'] < metric_set(y, dull)['brier']


# ============================================================
# The bootstrap itself
# ============================================================
def test_identical_forecasters_produce_an_interval_pinned_to_zero():
    """The strongest check on the pairing. If the same index vector is applied
    to both models, two identical forecasters differ by exactly zero on every
    resample. Any spread here means the two arrays are being resampled
    independently, and every interval this script prints would be inflated."""
    y, sharp, _ = make_pair(400)
    diffs = paired_bootstrap(y, sharp, sharp, n_resamples=200, seed=1)
    for key, _, _ in METRICS:
        assert np.allclose(diffs[key], 0.0, atol=1e-12), (
            f"{key} varies between two identical forecasters -- the resample "
            f"is not being applied to both models together")


def test_a_real_difference_is_detected():
    y, sharp, dull = make_pair()
    diffs = paired_bootstrap(y, sharp, dull, n_resamples=600, seed=2)
    lo, hi = np.percentile(diffs['brier'], [2.5, 97.5])
    assert hi < 0, f"sharper model's Brier advantage was not detected: CI [{lo}, {hi}]"


def test_two_equally_good_forecasters_come_back_inconclusive():
    """The other direction. A bootstrap that only ever finds differences is
    worse than useless -- most of this project's experiments are nulls, and
    the method has to be able to say so."""
    y, a, b = make_pair(duller_noise=0.05)  # same noise level as `sharp`
    diffs = paired_bootstrap(y, a, b, n_resamples=600, seed=3)
    lo, hi = np.percentile(diffs['brier'], [2.5, 97.5])
    assert lo < 0 < hi, f"two equally good models produced a 'real' gap: [{lo}, {hi}]"


def test_pairing_is_tighter_than_treating_the_models_as_independent():
    """Why paired at all. Drawing separate index vectors for the two models
    destroys the correlation between them and widens the interval -- turning
    a genuine difference into a null. This asserts the pairing is actually
    buying what it is supposed to buy."""
    y, sharp, dull = make_pair()
    paired = paired_bootstrap(y, sharp, dull, n_resamples=600, seed=4)['brier']

    rng = np.random.default_rng(4)
    n = len(y)
    unpaired = np.empty(600)
    for i in range(600):
        ia, ib = rng.integers(0, n, n), rng.integers(0, n, n)
        unpaired[i] = (metric_set(y[ia], sharp[ia])['brier']
                       - metric_set(y[ib], dull[ib])['brier'])

    width = lambda d: np.subtract(*np.percentile(d, [97.5, 2.5]))
    assert width(paired) < width(unpaired), (
        f"paired interval ({width(paired):.6f}) is not tighter than unpaired "
        f"({width(unpaired):.6f}) -- the pairing is not doing anything")


def test_the_bootstrap_is_reproducible_from_its_seed():
    """A published interval that can't be regenerated is not evidence."""
    y, sharp, dull = make_pair(400)
    a = paired_bootstrap(y, sharp, dull, n_resamples=100, seed=99)['brier']
    b = paired_bootstrap(y, sharp, dull, n_resamples=100, seed=99)['brier']
    assert np.array_equal(a, b)
    c = paired_bootstrap(y, sharp, dull, n_resamples=100, seed=100)['brier']
    assert not np.array_equal(a, c)


# ============================================================
# summarise: signs, verdicts, and the analytic cross-check
# ============================================================
def test_verdict_and_direction_respect_each_metric_s_own_polarity():
    """Reliability is better when lower, resolution when higher. Reporting a
    raw difference without tracking that is how a result gets described
    backwards."""
    y, sharp, dull = make_pair()
    pa, pb = metric_set(y, sharp), metric_set(y, dull)
    diffs = paired_bootstrap(y, sharp, dull, n_resamples=400, seed=5)
    res = summarise(pa, pb, diffs, y, sharp, dull)

    # The sharper model should win on both, despite the opposite polarity.
    assert res['brier']['difference'] < 0 and res['brier']['favours'] == 'a'
    assert res['resolution']['difference'] > 0 and res['resolution']['favours'] == 'a'
    for key, _, _ in METRICS:
        assert res[key]['verdict'] in ('REAL DIFFERENCE', 'INCONCLUSIVE')
        assert res[key]['excludes_zero'] == (res[key]['ci_lo'] > 0 or res[key]['ci_hi'] < 0)


def test_bootstrap_and_analytic_brier_intervals_agree():
    """Brier is a mean of per-game squared errors, so its paired difference has
    a closed-form standard error. Two independent routes to the same interval
    is the check that the resampling is wired to the right arrays."""
    y, sharp, dull = make_pair()
    pa, pb = metric_set(y, sharp), metric_set(y, dull)
    diffs = paired_bootstrap(y, sharp, dull, n_resamples=2000, seed=6)
    res = summarise(pa, pb, diffs, y, sharp, dull)['brier']

    assert res['ci_lo'] == pytest.approx(res['analytic_ci_lo'], abs=2e-3)
    assert res['ci_hi'] == pytest.approx(res['analytic_ci_hi'], abs=2e-3)
    # And both must agree with the observed difference they bracket.
    assert res['ci_lo'] < res['difference'] < res['ci_hi']


def test_point_estimate_is_the_observed_difference_not_the_bootstrap_mean():
    """The resamples describe the spread around what was observed; they do not
    replace it. Substituting the bootstrap mean would introduce a small bias
    and quietly detach the headline number from the real backtest."""
    y, sharp, dull = make_pair(400)
    pa, pb = metric_set(y, sharp), metric_set(y, dull)
    diffs = paired_bootstrap(y, sharp, dull, n_resamples=200, seed=8)
    res = summarise(pa, pb, diffs, y, sharp, dull)
    assert res['brier']['difference'] == pytest.approx(pa['brier'] - pb['brier'], abs=1e-15)


def test_degenerate_resamples_are_counted_not_silently_dropped():
    """A resample that draws a single outcome class can't be scored. It is
    excluded from the percentile, but the count is reported -- a run where
    that number is large would mean the interval rests on less than it
    claims."""
    y, sharp, dull = make_pair(300)
    pa, pb = metric_set(y, sharp), metric_set(y, dull)
    diffs = paired_bootstrap(y, sharp, dull, n_resamples=200, seed=9)
    res = summarise(pa, pb, diffs, y, sharp, dull)
    for key, _, _ in METRICS:
        assert res[key]['degenerate_resamples'] == 0


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
