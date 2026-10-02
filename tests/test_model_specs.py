"""Stage 33 item 21: one definition of the published models.

The live pipeline and the backtest used to build their own
`LogisticRegression(max_iter=1000)` and keep their own feature lists. Both
now fit from `MODEL_SPECS` (src/pipeline/model_specs.py). These tests hold:

- the published specs are exactly the old default fit, written out, so the
  refactor and the explicit C=1.0 / L2 moved nothing;
- the registry's settings (penalty None, a StandardScaler) mean what the
  registry says, spelled the way the pinned scikit-learn accepts without a
  deprecation warning;
- the live fit and the backtest both go through the specs, and the feature
  order the specs name is the order predict_week builds its rows in.

Byte-identity on the real six seasons is shown outside the suite (it needs
nflverse): the PR records the before/after comparison and the
reproducibility audit.
"""
import inspect
import warnings

import numpy as np
import pandas as pd
import pytest
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.pipeline import model_specs as ms
from src.pipeline import weekly_update as wu
from src.pipeline.model_specs import (
    MODEL_A_FEATURES,
    MODEL_B_FEATURES,
    MODEL_SPECS,
    ModelSpec,
)
from src.research import backtest as bt
from src.research import calibration


def _hist(seed=3):
    """Three seasons of six weeks, every feature on a different scale (as the
    real ones are), and one game in eight with no line."""
    rng = np.random.default_rng(seed)
    rows = []
    for season in (2020, 2021, 2022):
        for week in range(1, 7):
            for _ in range(16):
                off, dfn = rng.normal(scale=0.09, size=2)
                qb, chg = rng.normal(scale=0.2), int(rng.integers(-1, 2))
                spread = rng.normal(scale=6.0)
                logit = 8 * off + 8 * dfn + 2 * qb + 0.3 * chg + 0.1 * spread
                rows.append({'season': season, 'week': week, 'off_matchup': off,
                             'def_matchup': dfn, 'qb_matchup': qb, 'qb_change_diff': chg,
                             'spread_line': np.nan if rng.random() < 0.125 else spread,
                             'home_win': int(rng.random() < 1 / (1 + np.exp(-logit)))})
    return pd.DataFrame(rows)


# --- the published specs: today's fit, written out --------------------------

def test_the_published_specs_are_the_old_default_fit_written_out():
    """C=1.0 with an L2 penalty, max_iter 1000, no scaler: the fit both paths
    made before item 21, with nothing left to a library default. Parameter
    equality with the old `LogisticRegression(max_iter=1000)` is what makes
    writing them out a no-op."""
    assert set(MODEL_SPECS) == {'model_a', 'model_b', 'market'}
    for name, spec in MODEL_SPECS.items():
        assert (spec.penalty, spec.C, spec.scaler, spec.max_iter) == ('l2', 1.0, None, 1000), name
        est = spec.estimator()
        assert isinstance(est, LogisticRegression), name
        assert est.get_params() == LogisticRegression(max_iter=1000).get_params(), name
        assert est.get_params()['C'] == 1.0 and est.get_params()['l1_ratio'] == 0.0, name


def test_fitting_any_registered_setting_warns_about_nothing():
    """scikit-learn 1.9 deprecates `penalty` (gone in 1.10). A spec that
    passed it would warn on every weekly fit and break on the next upgrade."""
    hist = _hist()
    specs = [*MODEL_SPECS.values(),
             ModelSpec(MODEL_A_FEATURES, penalty=None, C=None),
             ModelSpec(MODEL_A_FEATURES, scaler='standard')]
    for spec in specs:
        # FutureWarning is scikit-learn's deprecation category; pandas 1.5's
        # own DeprecationWarning from numpy is not this test's subject.
        with warnings.catch_warnings():
            warnings.simplefilter('error', FutureWarning)
            warnings.simplefilter('error', ConvergenceWarning)
            spec.fit(hist)


def test_an_unpenalised_spec_is_sklearns_unpenalised_fit():
    """The registry's R1 candidate is `penalty=None`. Spelled C=inf, it must be
    the same fit, to the bit, as the deprecated spelling."""
    hist = _hist().dropna()
    X, y = hist[list(MODEL_A_FEATURES)].values, hist['home_win'].values
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', FutureWarning)
        old = LogisticRegression(max_iter=1000, penalty=None).fit(X, y)
    new = ModelSpec(MODEL_A_FEATURES, penalty=None, C=None).fit(hist)
    assert new.get_params()['C'] == np.inf
    assert new.coef_.tobytes() == old.coef_.tobytes()
    assert new.intercept_.tobytes() == old.intercept_.tobytes()
    incumbent = MODEL_SPECS['model_a'].fit(hist)
    assert not np.allclose(new.coef_, incumbent.coef_), 'the unpenalised fit is the penalised one'


def test_a_scaled_spec_fits_its_scaler_on_the_training_rows():
    """R2: the scaler is part of the estimator, so each refit fits it on its
    own training rows and nothing later."""
    spec = ModelSpec(MODEL_A_FEATURES, scaler='standard')
    est = spec.estimator()
    assert isinstance(est, Pipeline)
    assert isinstance(est.steps[0][1], StandardScaler)
    assert est.steps[-1][1].get_params() == LogisticRegression(max_iter=1000).get_params()
    train = _hist().query('season == 2020')
    fitted = spec.fit(train)
    np.testing.assert_allclose(fitted.steps[0][1].mean_, train[list(MODEL_A_FEATURES)].mean().values)


@pytest.mark.parametrize('kwargs', [
    {'penalty': 'l1'},
    {'penalty': 'l2', 'C': None},
    {'penalty': None, 'C': 1.0},
    {'scaler': 'minmax'},
])
def test_a_spec_refuses_settings_it_cannot_mean(kwargs):
    with pytest.raises(ValueError):
        ModelSpec(MODEL_A_FEATURES, **kwargs)


def test_a_spec_refuses_a_bare_string_of_features():
    """('spread_line') is a string, not a tuple: it would fit on characters."""
    with pytest.raises(ValueError):
        ModelSpec('spread_line')


# --- both paths fit from the specs -------------------------------------------

def test_model_a_features_are_in_the_order_predict_week_builds_them():
    """predict_week builds its rows positionally and names Model A's "why"
    coefficients 0 to 3 by position. A reordered spec would fit fine and
    mislabel every breakdown on the page."""
    assert MODEL_A_FEATURES == ('off_matchup', 'def_matchup', 'qb_matchup', 'qb_change_diff')
    assert MODEL_B_FEATURES == MODEL_A_FEATURES + ('spread_line',)
    assert MODEL_SPECS['model_a'].features == MODEL_A_FEATURES
    assert MODEL_SPECS['model_b'].features == MODEL_B_FEATURES
    assert MODEL_SPECS['market'].features == ('spread_line',)
    src = inspect.getsource(wu.predict_week)
    row = ', '.join(MODEL_A_FEATURES)
    assert f'model_a.predict_proba([[{row}]])' in src
    assert f'model_b.predict_proba([[{row}, spread]])' in src
    for i, name in enumerate(('off_matchup', 'def_matchup', 'qb_matchup')):
        assert f"'{name}': round(float(coefs[{i}] * {name}), 4)" in src
    assert "'qb_change': round(float(coefs[3] * qb_change_diff), 4)" in src


def test_the_calibration_file_names_the_specs_features():
    assert calibration.MODELS == {n: list(s.features) for n, s in MODEL_SPECS.items()}


def test_the_live_fit_is_the_spec_fit(monkeypatch):
    """fit_models fits Model A and Model B from MODEL_SPECS, and Model B only
    on games with a line, as the spec's own fit does."""
    hist = _hist()
    a, b = wu.fit_models(hist)
    for model, name in ((a, 'model_a'), (b, 'model_b')):
        ref = MODEL_SPECS[name].fit(hist)
        assert model.get_params() == ref.get_params(), name
        assert model.coef_.tobytes() == ref.coef_.tobytes(), name
        assert model.intercept_.tobytes() == ref.intercept_.tobytes(), name

    seen = []
    real_fit = ModelSpec.fit

    def spy(self, rows):
        seen.append(self)
        return real_fit(self, rows)
    monkeypatch.setattr(ModelSpec, 'fit', spy)
    wu.fit_models(hist)
    assert seen == [MODEL_SPECS['model_a'], MODEL_SPECS['model_b']]


def test_the_backtest_is_walk_forward_of_the_spec():
    """backtest() with a feature list scores the published incumbent; with a
    ModelSpec it scores that spec, through the same loop."""
    hist = _hist()
    _, y, p = bt.backtest(hist, list(MODEL_A_FEATURES), [2022], return_raw=True)
    scored, p2 = ms.walk_forward(MODEL_SPECS['model_a'], hist, [2022])
    assert p.tobytes() == p2.tobytes()
    np.testing.assert_array_equal(y, scored['home_win'].values)

    candidate = ModelSpec(MODEL_A_FEATURES, penalty=None, C=None)
    _, yc, pc = bt.backtest(hist, candidate, [2022], return_raw=True)
    _, pc2 = ms.walk_forward(candidate, hist, [2022])
    assert pc.tobytes() == pc2.tobytes()
    assert not np.allclose(pc, p), 'a candidate spec passed to backtest() was scored as the incumbent'
    np.testing.assert_array_equal(yc, y)


def test_two_specs_with_the_same_features_score_the_same_games():
    """Pairing a candidate with the incumbent needs identical rows: the
    registry's paired bootstrap resamples games, not two separate lists."""
    hist = _hist()
    specs = [MODEL_SPECS['model_b'], ModelSpec(MODEL_B_FEATURES, penalty=None, C=None),
             ModelSpec(MODEL_B_FEATURES, scaler='standard')]
    rows = [ms.walk_forward(s, hist, [2021, 2022])[0] for s in specs]
    for r in rows[1:]:
        pd.testing.assert_frame_equal(r, rows[0])
    assert rows[0]['spread_line'].notna().all()
    expected = hist[hist['season'].isin([2021, 2022])].dropna(subset=list(MODEL_B_FEATURES))
    assert len(rows[0]) == len(expected)


def test_walk_forward_with_no_scoreable_season_returns_nothing():
    scored, prob = ms.walk_forward(MODEL_SPECS['model_a'], _hist(), [2030])
    assert len(scored) == 0 and len(prob) == 0
