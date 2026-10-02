"""The models this project fits, written down once (Stage 33 item 21).

Until this file, the live pipeline (`weekly_update.fit_models`) and the
backtest (`src/research/backtest.py`) each built their own
`LogisticRegression(max_iter=1000)`, and each wrote out its own feature
list. They agreed because two people copied carefully, not because anything
made them agree. A model is now a `ModelSpec`: its features and its
regularisation, with nothing left to a library default. `MODEL_SPECS` holds
the three published models, and both paths fit from it.

`walk_forward(spec, hist, ...)` is the published evaluation: refit every
week on every game strictly earlier, predict that week. `backtest()` is
now a thin wrapper over it, so the Stage 33 registrations
(`experiments/stage33/registry.json`) can score a candidate spec through
exactly the code that scored the incumbent.

**On `penalty`.** The registry writes the incumbent as `C=1.0,
penalty='l2'`, sklearn's defaults when it was written. The pinned
scikit-learn (1.9.0) deprecates the `penalty` argument (removed in 1.10):
passing it warns on every fit. So a spec states `penalty` in the registry's
words, and `estimator()` spells it the supported way: L2 is `l1_ratio=0.0`
with `C`, no penalty is `C=inf`. `tests/test_model_specs.py` holds the
incumbent's parameters equal to the old `LogisticRegression(max_iter=1000)`,
so writing the defaults out changed nothing.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

MODEL_A_FEATURES = ('off_matchup', 'def_matchup', 'qb_matchup', 'qb_change_diff')
MODEL_B_FEATURES = MODEL_A_FEATURES + ('spread_line',)
MARKET_FEATURES = ('spread_line',)

#: A refit with fewer complete training games than this is skipped.
MIN_TRAIN = 50

PENALTIES = ('l2', None)
SCALERS = (None, 'standard')


@dataclass(frozen=True)
class ModelSpec:
    """One logistic regression: its features and how it is regularised.

    penalty 'l2' needs a C; penalty None takes none (an unpenalised fit has
    no strength to set). scaler 'standard' puts a StandardScaler in front,
    fitted on each refit's own training rows, because it is part of the
    estimator that each refit fits."""
    features: tuple[str, ...]
    penalty: str | None = 'l2'
    C: float | None = 1.0
    scaler: str | None = None
    max_iter: int = 1000

    def __post_init__(self):
        if not self.features or isinstance(self.features, str):
            raise ValueError(f'features must be a non-empty tuple of column names, got {self.features!r}')
        if self.penalty not in PENALTIES:
            raise ValueError(f'penalty must be one of {PENALTIES}, got {self.penalty!r}')
        if self.penalty == 'l2' and self.C is None:
            raise ValueError("penalty='l2' needs a C")
        if self.penalty is None and self.C is not None:
            raise ValueError('an unpenalised fit takes no C; pass C=None')
        if self.scaler not in SCALERS:
            raise ValueError(f'scaler must be one of {SCALERS}, got {self.scaler!r}')

    def estimator(self):
        """A fresh, unfitted estimator for this spec."""
        if self.penalty == 'l2':
            model = LogisticRegression(max_iter=self.max_iter, C=self.C, l1_ratio=0.0)
        else:
            model = LogisticRegression(max_iter=self.max_iter, C=np.inf)
        if self.scaler == 'standard':
            return make_pipeline(StandardScaler(), model)
        return model

    def fit(self, rows: pd.DataFrame):
        """Fit on every row with all features and an outcome."""
        rows = rows.dropna(subset=list(self.features) + ['home_win'])
        model = self.estimator()
        model.fit(rows[list(self.features)].values, rows['home_win'].values)
        return model


MODEL_SPECS = {
    'model_a': ModelSpec(MODEL_A_FEATURES),
    'model_b': ModelSpec(MODEL_B_FEATURES),
    'market': ModelSpec(MARKET_FEATURES),
}


def walk_forward(spec: ModelSpec, hist: pd.DataFrame, test_seasons, refit_every_n_weeks=1,
                 min_train=MIN_TRAIN):
    """The published walk-forward evaluation of one spec.

    For each test season, each week is predicted by a model fitted on every
    complete game strictly before it (from the first season in `hist`).
    refit_every_n_weeks=None fits once per season on earlier seasons only,
    the pre-Stage-9 behaviour, kept for comparison. Only rows with every
    feature and an outcome are trained on or scored, so two specs with the
    same features score the same games.

    Returns (scored, prob): the scored rows of `hist`, in the order scored,
    and the predicted home-win probability for each."""
    features = list(spec.features)
    hist = hist.sort_values(['season', 'week'])
    scored, probs = [], []
    for test_season in test_seasons:
        d2 = hist.dropna(subset=features + ['home_win'])
        season_weeks = sorted(d2[d2['season'] == test_season]['week'].unique())
        if not season_weeks:
            continue
        if refit_every_n_weeks is None:
            train = d2[d2['season'] < test_season]
            test = d2[d2['season'] == test_season]
            if len(train) < min_train or len(test) == 0:
                continue
            m = spec.fit(train)
            scored.append(test)
            probs.append(m.predict_proba(test[features].values)[:, 1])
        else:
            last_refit_week = None
            model = None
            for w in season_weeks:
                if last_refit_week is None or (w - last_refit_week) >= refit_every_n_weeks:
                    train = d2[(d2['season'] < test_season) | ((d2['season'] == test_season) & (d2['week'] < w))]
                    if len(train) < min_train:
                        continue
                    model = spec.fit(train)
                    last_refit_week = w
                if model is None:
                    continue
                test_w = d2[(d2['season'] == test_season) & (d2['week'] == w)]
                if len(test_w) == 0:
                    continue
                scored.append(test_w)
                probs.append(model.predict_proba(test_w[features].values)[:, 1])
    if not scored:
        return hist.iloc[0:0], np.array([])
    return pd.concat(scored), np.concatenate(probs)
