"""Stage 95 item 38: the calibration intercept and slope are two separate fits,
and the forward-test file and both pages say so (audit 7 M13: a reader takes
an intercept and a slope printed side by side as one recalibration).

Run with: pytest tests/test_calibration_two_fits.py -v
"""
from pathlib import Path

import numpy as np
import pytest

from src.core import forward_test as ft
from tests.page_script import day_script

ROOT = Path(__file__).resolve().parents[1]
SENTENCE = ('They are two fits, not one: the intercept is fitted with the slope held at 1 (calibration in the large), '
            'and the slope is fitted with an intercept of its own.')


def test_the_intercept_and_the_slope_are_two_fits_and_the_file_says_so():
    rng = np.random.default_rng(1)
    p = rng.uniform(0.3, 0.7, 400)
    y = (rng.uniform(size=400) < p).astype(float)
    days = np.repeat(np.arange(40), 10)
    out = ft.calibration(p, y, days, seed=1, n=200)
    assert out['fits'] == ft.FITS and out['fits'].startswith('two:')
    x = ft._logit(p)
    one = np.ones((1, len(p)))
    a_large, _ = ft.recalibrate(x, y, one, slope_free=False)
    a_free, b_free = ft.recalibrate(x, y, one, slope_free=True)
    assert out['intercept']['value'] == pytest.approx(a_large[0])
    assert out['slope']['value'] == pytest.approx(b_free[0])
    assert abs(a_large[0] - a_free[0]) > 1e-6, 'the intercept shown is not the slope fit\'s own intercept'


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_each_page_says_the_pair_is_two_fits(sport):
    js = day_script(sport)
    body = js[js.index('function calibrationTable('):js.index('function m2Html(')]
    assert SENTENCE in body
