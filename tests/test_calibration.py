"""
Tests for src/calibration.py's statistics.

These cover the pure functions only -- no play-by-play, no network. The
expensive part (building the backtest feature table) is exercised by actually
running the script; what matters here is that the maths underneath the
reliability diagram is right, because a calibration chart with subtly wrong
intervals is worse than no chart at all. That is the exact failure this module
was written to correct.

Run with: pytest tests/test_calibration.py -v
"""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ============================================================
# Wilson score interval
# ============================================================
def test_wilson_matches_published_value():
    """5 of 10 with z=1.96 is a standard textbook case: (0.2366, 0.7634).
    Checked against the published value rather than against a
    reimplementation of the same formula, which would only prove the code
    agrees with itself."""
    from calibration import wilson_interval

    lo, hi = wilson_interval(5, 10)
    assert lo == pytest.approx(0.2366, abs=1e-4)
    assert hi == pytest.approx(0.7634, abs=1e-4)


def test_wilson_handles_zero_games():
    """An empty bin must not raise or divide by zero -- it knows nothing, so
    the interval is the whole range."""
    from calibration import wilson_interval

    assert wilson_interval(0, 0) == (0.0, 1.0)


def test_wilson_stays_inside_zero_to_one_at_the_extremes():
    """The normal approximation famously runs past 1.0 for 10/10; Wilson must
    not. This is the case that made Wilson the right choice for tail bins."""
    from calibration import wilson_interval

    lo, hi = wilson_interval(10, 10)
    assert 0.0 <= lo <= 1.0 and 0.0 <= hi <= 1.0
    assert hi <= 1.0
    assert lo < 1.0  # 10/10 is still not proof the true rate is 100%

    lo0, hi0 = wilson_interval(0, 10)
    assert lo0 >= 0.0 and hi0 > 0.0


def test_wilson_interval_narrows_as_n_grows():
    from calibration import wilson_interval

    widths = []
    for n in (10, 100, 1000):
        lo, hi = wilson_interval(n // 2, n)
        widths.append(hi - lo)
    assert widths[0] > widths[1] > widths[2]


# ============================================================
# Brier decomposition
# ============================================================
def _discrete_case():
    """Forecasts taking a few distinct values, each landing in its own bin.

    The Murphy identity is exact only when every forecast in a bin is
    identical -- binning continuous probabilities leaves a within-bin variance
    term, making it approximate. Using discrete values lets the identity be
    asserted exactly rather than with a fudge tolerance hiding a real error.
    """
    probs = np.array([0.25] * 40 + [0.55] * 40 + [0.75] * 40)
    rng = np.random.default_rng(0)
    truth = np.concatenate([
        (rng.random(40) < 0.25).astype(float),
        (rng.random(40) < 0.55).astype(float),
        (rng.random(40) < 0.75).astype(float),
    ])
    return truth, probs


def test_decomposition_identity_holds():
    """Brier == reliability - resolution + uncertainty."""
    from calibration import brier_decomposition

    truth, probs = _discrete_case()
    d = brier_decomposition(truth, probs)

    brier = float(np.mean((probs - truth) ** 2))
    rebuilt = d['reliability'] - d['resolution'] + d['uncertainty']
    assert rebuilt == pytest.approx(brier, abs=1e-9)


def test_perfect_calibration_gives_near_zero_reliability():
    """Forecasts that match observed frequency exactly must score ~0
    reliability (lower is better)."""
    from calibration import brier_decomposition

    # 100 games at 0.30 of which exactly 30 are wins, 100 at 0.70 with 70 wins.
    probs = np.array([0.30] * 100 + [0.70] * 100)
    truth = np.array([1.0] * 30 + [0.0] * 70 + [1.0] * 70 + [0.0] * 30)
    d = brier_decomposition(truth, probs)
    assert d['reliability'] == pytest.approx(0.0, abs=1e-12)


def test_base_rate_forecaster_has_zero_resolution():
    """A model that always predicts the base rate is perfectly calibrated and
    completely useless. Reliability ~0 AND resolution ~0 is what tells those
    two apart -- the reason resolution is reported at all."""
    from calibration import brier_decomposition

    truth = np.array([1.0] * 60 + [0.0] * 40)
    probs = np.full(100, 0.60)
    d = brier_decomposition(truth, probs)

    assert d['reliability'] == pytest.approx(0.0, abs=1e-12)
    assert d['resolution'] == pytest.approx(0.0, abs=1e-12)
    assert d['base_rate'] == pytest.approx(0.60)


# ============================================================
# Binning
# ============================================================
def test_bins_account_for_every_game():
    """No game may be silently dropped between bins -- an off-by-one on a bin
    edge would quietly shrink the sample the whole chart rests on."""
    from calibration import calibration_bins

    rng = np.random.default_rng(1)
    probs = rng.random(500)
    truth = (rng.random(500) < probs).astype(float)

    bins = calibration_bins(truth, probs)
    assert sum(b['n'] for b in bins) == 500


def test_probability_of_exactly_one_is_included():
    """p=1.0 must land in the last bin, not fall off the end."""
    from calibration import calibration_bins

    bins = calibration_bins(np.array([1.0]), np.array([1.0]), min_n=1)
    assert sum(b['n'] for b in bins) == 1


def test_small_bins_are_flagged_not_dropped():
    """The whole point: a thin bin keeps its real count and gets marked,
    rather than vanishing or being presented as a measurement."""
    from calibration import calibration_bins

    probs = np.array([0.62] * 3)
    truth = np.array([1.0, 0.0, 1.0])
    bins = calibration_bins(truth, probs, min_n=25)

    assert len(bins) == 1
    assert bins[0]['n'] == 3
    assert bins[0]['underpowered'] is True


def test_wide_interval_is_marked_consistent_with_perfect():
    """A bin whose interval straddles its own mean prediction cannot be called
    miscalibrated. Marking that is what stops a reader treating every
    off-diagonal point as a defect."""
    from calibration import calibration_bins

    probs = np.array([0.62] * 10
                     )
    truth = np.array([1.0] * 6 + [0.0] * 4)  # 60% observed vs 62% predicted
    bins = calibration_bins(truth, probs, min_n=1)
    assert bins[0]['consistent_with_perfect'] is True


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
