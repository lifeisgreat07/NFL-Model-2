"""The NHL's day-sport v2 (experiments/nhl/stage95_v2/registry.json): each registered change on small games, then
the committed run (python -m src.sports.nhl.v2) held to the registration.

Run with: pytest tests/test_nhl_v2.py -v
"""
import json

import numpy as np
import pandas as pd
import pytest

from src.core.day_backtest import estimator
from src.sports.nhl import v2


def test_item_29_prices_are_judged_by_their_own_lines_band():
    m = pd.DataFrame({'game_id': ['a', 'b', 'c', 'd'],
                      'home_price': [-150.0, -150.0, 120.0, 300.0], 'away_price': [130.0, 400.0, 250.0, 300.0],
                      'converted': [False, False, True, True]})
    kept, dropped = v2.drop_bad_prices(m)
    # a: 0.600 + 0.435 = 1.03, two-way, kept; b: 0.600 + 0.200 = 0.80, two-way, dropped;
    # c: 0.455 + 0.286 = 0.74, three-way, dropped; d: 0.25 + 0.25 = 0.50, three-way, dropped.
    assert list(kept['game_id']) == ['a'] and dropped == ['b', 'c', 'd']
    three = pd.DataFrame({'game_id': ['e'], 'home_price': [120.0], 'away_price': [160.0], 'converted': [True]})
    assert list(v2.drop_bad_prices(three)[0]['game_id']) == ['e'], '0.455 + 0.385 = 0.84, inside the three-way band'


def test_item_29_a_box_without_both_shot_counts_is_not_used():
    box = pd.DataFrame({'game_id': ['1', '2', '3'], 'home_sog': [30, np.nan, 28], 'away_sog': [25, 31, np.nan]})
    assert v2.unusable_boxes(box) == {'2', '3'}


def games(n=160):
    rng = np.random.default_rng(3)
    teams = ['AAA', 'BBB', 'CCC', 'DDD']
    rows = []
    for i in range(n):
        h, a = rng.choice(teams, 2, replace=False)
        hs, as_ = int(rng.integers(0, 6)), int(rng.integers(0, 6))
        if hs == as_:
            hs += 1
        day = str(pd.Timestamp('2020-01-01') + pd.Timedelta(days=i))[:10]
        rows.append({'game_id': str(i), 'season': 2020 + i // 40, 'game_date': day,
                     'game_type': 'regular', 'home': h, 'away': a, 'home_score': hs, 'away_score': as_,
                     'last_period': 'REG', 'home_sog': int(rng.integers(20, 40)),
                     'away_sog': int(rng.integers(20, 40)),
                     'home_goalie_id': 1 if h < 'C' else 2, 'home_goalie_sa': 30, 'home_goalie_ga': as_,
                     'away_goalie_id': 3, 'away_goalie_sa': 30, 'away_goalie_ga': hs})
    return pd.DataFrame(rows)


def test_item_29_an_unusable_box_never_trains_the_ratings_but_is_still_forecast():
    g = v2.ratings.prepare(games())
    base = v2.features(g, 60, [2000])
    g2 = g.copy()
    g2.loc[g2['game_id'] == '120', 'shot_margin'] = 999  # a wrecked box: if it trained anything, later rows move
    t = v2.features(g2, 60, [2000], unusable={'120'})
    clean = v2.features(g.drop(index=g.index[g['game_id'] == '120']), 60, [2000])
    later = t[t['day'] > g.loc[g['game_id'] == '120', 'day'].iloc[0]].set_index('game_id')
    ref = clean.set_index('game_id').loc[later.index]
    assert np.allclose(later['shot_matchup'], ref['shot_matchup'])
    assert '120' in set(t['game_id']) and '120' in set(base['game_id'])


def test_item_28_a_neutral_game_gets_no_home_edge():
    rng = np.random.default_rng(1)
    n = 400
    t = pd.DataFrame({'game_id': [str(i) for i in range(n)], 'season': [2024] * (n - 2) + [2025, 2025],
                      'day': list(pd.date_range('2024-01-01', periods=n - 2)) + [pd.Timestamp('2025-06-01')] * 2,
                      'x': rng.normal(size=n), 'neutral_site': [False] * (n - 1) + [True]})
    t['home_win'] = (rng.random(n) < 1 / (1 + np.exp(-(0.6 + t['x'])))).astype(int)
    t.loc[n - 1, 'x'] = t.loc[n - 2, 'x']
    p = v2.walk_forward(t, ['x'], [2025])
    model = estimator().fit(t.loc[: n - 3, ['x']], t.loc[: n - 3, 'home_win'])
    z = model.decision_function(t.loc[[n - 2], ['x']])[0]
    b = float(model[-1].intercept_[0])
    assert p[str(n - 2)] == pytest.approx(1 / (1 + np.exp(-z)))
    assert p[str(n - 1)] == pytest.approx(1 / (1 + np.exp(-(z - b)))), 'the neutral game loses exactly the intercept'


def test_item_28_neutral_games_are_the_leagues_own_flag():
    sched = {2024: pd.DataFrame({'game_id': ['1', '2'], 'neutral_site': [False, True]}),
             2025: pd.DataFrame({'game_id': ['3'], 'neutral_site': [True]})}
    assert v2.neutral_ids([2024, 2025], load=sched.__getitem__) == {'2', '3'}


def test_item_35_none_is_the_goalie_term_removed():
    assert v2.model_a_columns(None) == ['goal_matchup', 'shot_matchup']
    assert v2.model_a_columns(2000) == ['goal_matchup', 'shot_matchup', 'goalie_matchup_2000']
    reg = v2.registry()['protocol']['tuning']
    assert '{60, 120, 240}' in reg and '{1000, 2000, 4000, 8000, 16000, none}' in reg
    assert v2.GRID == {'H_days': [60, 120, 240], 'K_shots': [1000, 2000, 4000, 8000, 16000, None]}


# ---------------------------------------------------------------- the committed run (python -m src.sports.nhl.v2)

RESULTS = v2.RESULTS / 'backtest.json'


def test_the_committed_run_was_tuned_on_validation_only_over_the_whole_grid():
    doc = json.loads(RESULTS.read_text(encoding='utf-8'))
    assert doc['registry'] == 'experiments/nhl/stage95_v2/registry.json'
    p = v2.backtest.registry()['protocol']
    assert doc['tuning']['seasons'] == p['validation_seasons']
    assert {(r['H_days'], r['K_shots']) for r in doc['tuning']['grid']} == {
        (h, k) for h in v2.GRID['H_days'] for k in v2.GRID['K_shots']}
    best = min(doc['tuning']['grid'], key=lambda r: r['log_loss'])
    assert doc['tuning']['chosen'] == {'H_days': best['H_days'], 'K_shots': best['K_shots']}
    assert doc['confirmation_seasons'] == p['confirmation_seasons']


def test_the_measurements_are_reported_not_decided():
    doc = json.loads(RESULTS.read_text(encoding='utf-8'))
    assert set(doc['measurements']) == {'MV1_model_a', 'MV1_model_b'}
    for m in doc['measurements'].values():
        assert m['level'] == 0.95 and 'label' not in m
