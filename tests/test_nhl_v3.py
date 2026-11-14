"""The NHL's v3 (Stage 105): v2 plus the back-to-back flag, as a shadow.

Run with: pytest tests/test_nhl_v3.py -v
"""
import numpy as np
import pandas as pd
import pytest

from src.core.day_backtest import estimator
from src.sports.nhl import v3, v3_shadow


def g(day, home, away):
    return {'day': pd.Timestamp(day), 'home': home, 'away': away}


def test_the_flag_is_the_away_clubs_back_to_back_minus_the_home_clubs():
    played = v3.played_days(pd.DataFrame([g('2026-11-10', 'TOR', 'MTL'), g('2026-11-10', 'BOS', 'NYR')]))
    rows = pd.DataFrame([g('2026-11-11', 'BOS', 'TOR'),   # both played yesterday: 1 - 1
                         g('2026-11-11', 'DET', 'MTL'),   # only the away club: 1 - 0
                         g('2026-11-11', 'NYR', 'CHI'),   # only the home club: 0 - 1
                         g('2026-11-12', 'TOR', 'MTL')])  # two days later: 0
    assert list(v3.b2b_matchup(rows, played)) == [0.0, 1.0, -1.0, 0.0]


def test_a_clubs_first_game_of_a_season_is_not_a_back_to_back():
    played = v3.played_days(pd.DataFrame([g('2026-04-16', 'TOR', 'MTL')]))
    assert list(v3.b2b_matchup(pd.DataFrame([g('2026-10-07', 'TOR', 'MTL')]), played)) == [0.0]


def test_the_flag_is_read_from_the_schedules_dates_not_the_clock():
    played = v3.played_days(pd.DataFrame([{'day': '2026-11-10T00:00:00', 'home': 'TOR', 'away': 'MTL'}]))
    rows = pd.DataFrame([{'day': '2026-11-11', 'home': 'BUF', 'away': 'TOR'}])
    assert list(v3.b2b_matchup(rows, played)) == [1.0]


def test_model_a_adds_the_flag_to_v2s_columns():
    assert v3.model_a_columns(['goal_matchup', 'shot_matchup']) == ['goal_matchup', 'shot_matchup', 'b2b_matchup']


def test_on_a_neutral_site_model_a_loses_the_intercept_and_model_b_keeps_it():
    rng = np.random.default_rng(4)
    x = pd.DataFrame({'a': rng.normal(size=300)})
    y = (rng.random(300) < 1 / (1 + np.exp(-(0.4 + x['a'])))).astype(int)
    model = estimator().fit(x, y)
    one = x.iloc[[0]]
    z, b = float(model.decision_function(one)[0]), float(model[-1].intercept_[0])
    assert v3_shadow.forecast(model, one, True, drop_intercept=True) == pytest.approx(1 / (1 + np.exp(-(z - b))))
    assert v3_shadow.forecast(model, one, True, drop_intercept=False) == pytest.approx(1 / (1 + np.exp(-z)))
    assert v3_shadow.forecast(model, one, False, drop_intercept=True) == pytest.approx(1 / (1 + np.exp(-z)))


def test_the_record_names_v3s_own_registry_and_code():
    import inspect
    src = inspect.getsource(v3_shadow.save)
    assert "'registry': 'experiments/nhl/stage105_v3/registry.json'" in src
    assert v3_shadow.CODE == 'nhl-day-sport-v3' and v3.REGISTRY.exists()
