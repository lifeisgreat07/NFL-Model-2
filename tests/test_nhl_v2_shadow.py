"""The NHL's v2 shadow in the daily run (Stage 95 item 36): v2's forecasts beside each saved pick, as
experiments/nhl/stage95_v2/registry.json's forward_test.shadow says, and never a pick.

The whole run is in tests/test_daily_end_to_end.py; these hold the pieces.

Run with: pytest tests/test_nhl_v2_shadow.py -v
"""
import numpy as np
import pandas as pd
import pytest

from src.core.day_backtest import estimator
from src.sports.nhl import v2_shadow


def test_the_season_market_is_each_games_last_read_before_its_start_and_two_way():
    lines = [
        {'game_id': '1', 'start_utc': '2026-10-20T23:00:00Z', 'read_utc': '2026-10-20T14:00:00Z',
         'home_price': -150.0, 'away_price': 130.0, 'home_prob': 0.58},
        {'game_id': '1', 'start_utc': '2026-10-20T23:00:00Z', 'read_utc': '2026-10-20T21:00:00Z',
         'home_price': -160.0, 'away_price': 140.0, 'home_prob': 0.6},
        {'game_id': '1', 'start_utc': '2026-10-20T23:00:00Z', 'read_utc': '2026-10-20T23:30:00Z',
         'home_price': -900.0, 'away_price': 600.0, 'home_prob': 0.88},
    ]
    assert v2_shadow.season_market(lines).to_dict('records') == [
        {'game_id': '1', 'home_price': -160.0, 'away_price': 140.0, 'home_prob': 0.6, 'converted': False}]


def test_item_29_holds_a_live_price_to_the_two_way_band():
    assert v2_shadow.price_ok({'home_price': -150.0, 'away_price': 130.0, 'home_prob': 0.58})
    assert not v2_shadow.price_ok({'home_price': -150.0, 'away_price': 400.0, 'home_prob': 0.7})
    assert not v2_shadow.price_ok(None)


def test_a_neutral_site_forecast_loses_exactly_the_intercept():
    rng = np.random.default_rng(4)
    x = pd.DataFrame({'a': rng.normal(size=300)})
    y = (rng.random(300) < 1 / (1 + np.exp(-(0.4 + x['a'])))).astype(int)
    model = estimator().fit(x, y)
    one = x.iloc[[0]]
    z, b = float(model.decision_function(one)[0]), float(model[-1].intercept_[0])
    assert v2_shadow.forecast(model, one, False) == pytest.approx(1 / (1 + np.exp(-z)))
    assert v2_shadow.forecast(model, one, True) == pytest.approx(1 / (1 + np.exp(-(z - b))))


def test_the_shadow_uses_what_its_backtest_chose_goalie_term_removed_included():
    doc = v2_shadow.backtest_doc()
    h, k = v2_shadow.chosen(doc)
    assert h == float(doc['tuning']['chosen']['H_days'])
    assert k is None if doc['tuning']['chosen']['K_shots'] is None else k == float(doc['tuning']['chosen']['K_shots'])
    assert v2_shadow.chosen({'tuning': {'chosen': {'H_days': 60, 'K_shots': None}}}) == (60.0, None)
