"""The NBA's v2 shadow in the daily run (Stage 95 item 36): v2's forecasts beside each saved pick, as
experiments/nba/stage95_v2/registry.json's forward_test.shadow says, and never a pick.

The whole run is in tests/test_daily_end_to_end.py; these hold the pieces.

Run with: pytest tests/test_nba_v2_shadow.py -v
"""
import json

import numpy as np
import pandas as pd
import pytest

from src.core.day_backtest import estimator
from src.sports.nba import v2_shadow


def test_the_season_market_is_each_games_last_read_before_its_start():
    lines = [
        {'game_id': '1', 'start_utc': '2026-10-20T23:00:00Z', 'read_utc': '2026-10-20T16:00:00Z',
         'home_price': -150.0, 'away_price': 130.0, 'home_prob': 0.58},
        {'game_id': '1', 'start_utc': '2026-10-20T23:00:00Z', 'read_utc': '2026-10-20T21:30:00Z',
         'home_price': -160.0, 'away_price': 140.0, 'home_prob': 0.6},
        {'game_id': '1', 'start_utc': '2026-10-20T23:00:00Z', 'read_utc': '2026-10-20T23:10:00Z',
         'home_price': -900.0, 'away_price': 600.0, 'home_prob': 0.88},
    ]
    m = v2_shadow.season_market(lines)
    assert m.to_dict('records') == [{'game_id': '1', 'home_price': -160.0, 'away_price': 140.0, 'home_prob': 0.6,
                                     'source': None}]


def test_item_29_judges_a_live_price_by_its_own_kind():
    assert v2_shadow.price_ok({'source': 'espn', 'home_price': -150.0, 'away_price': 130.0, 'home_prob': 0.58})
    assert not v2_shadow.price_ok({'source': 'espn', 'home_price': -150.0, 'away_price': 400.0, 'home_prob': 0.7})
    assert v2_shadow.price_ok({'source': 'kalshi', 'home_price': 0.55, 'away_price': 0.47, 'home_prob': 0.539})
    assert not v2_shadow.price_ok({'source': 'kalshi', 'home_price': 0.5, 'away_price': 0.45, 'home_prob': 0.526})
    assert not v2_shadow.price_ok({'source': None, 'home_prob': None})


def test_a_neutral_site_forecast_loses_exactly_the_intercept():
    rng = np.random.default_rng(2)
    x = pd.DataFrame({'a': rng.normal(size=300)})
    y = (rng.random(300) < 1 / (1 + np.exp(-(0.5 + x['a'])))).astype(int)
    model = estimator().fit(x, y)
    one = x.iloc[[0]]
    z = float(model.decision_function(one)[0])
    b = float(model[-1].intercept_[0])
    assert v2_shadow.forecast(model, one, False) == pytest.approx(1 / (1 + np.exp(-z)))
    assert v2_shadow.forecast(model, one, True) == pytest.approx(1 / (1 + np.exp(-(z - b))))


def test_a_doubled_slate_is_placed_where_the_backtest_placed_it_without_a_read():
    doc = json.loads((v2_shadow.v2.RESULTS / 'backtest.json').read_text(encoding='utf-8'))
    placed = doc['touched']['slates_placed']
    gid, day = next(iter(placed.items()))

    def refuse(url):
        raise AssertionError('read ESPN for a game the backtest already placed')
    assert v2_shadow.slate_of(doc, refuse)(gid) == day


def test_the_shadow_uses_the_half_life_and_ridge_its_backtest_chose():
    doc = v2_shadow.backtest_doc()
    assert v2_shadow.chosen(doc) == (float(doc['tuning']['chosen']['H_days']), float(doc['tuning']['chosen']['lambda']))
