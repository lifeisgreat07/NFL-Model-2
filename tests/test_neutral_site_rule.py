"""Stage 38 N1 in the live run (MODEL_VERSION 2.6): at a game the schedule
calls neutral, neither model gives the listed home team a home edge; a game
it does not place keeps it; and the pick records which.

`predict_week` is executed here with stand-in models whose intercept is
known, so the shift is measured, not read.

Run with: pytest tests/test_neutral_site_rule.py -v
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.sports.nfl import config
from src.sports.nfl import weekly_update as wu

ROOT = Path(__file__).resolve().parents[1]
REG = json.loads((ROOT / 'experiments' / 'nfl' / 'stage38' / 'n1_registry.json').read_text(encoding='utf-8'))


class Model:
    """A fitted logistic model stand-in: logit = intercept + coef . x."""

    def __init__(self, intercept, coefs):
        self.intercept_ = np.array([intercept])
        self.coef_ = np.array([coefs])

    def predict_proba(self, rows):
        z = self.intercept_[0] + float(np.dot(self.coef_[0], rows[0]))
        p = 1 / (1 + np.exp(-z))
        return np.array([[1 - p, p]])


MODELS = (Model(0.30, [1.0, -1.0, 0.5, 0.2]), Model(-0.10, [0.4, -0.4, 0.2, 0.1, -0.15]))
CURRENT = wu.Current(team_ratings={'JAX': (0.10, -0.05), 'NYJ': (0.02, 0.04)}, qb_cutoff=None,
                     starters_idx=None, qb_changed={})


@pytest.fixture(autouse=True)
def no_starters(monkeypatch):
    monkeypatch.setattr(wu, 'resolve_starters',
                        lambda g, idx, changed, overrides: ({'home': (None, 0), 'away': (None, 0)}, {}, []))


def pick(location):
    week = pd.DataFrame([{'home_team': 'JAX', 'away_team': 'NYJ', 'location': location, 'stadium': 'Wembley Stadium',
                          'spread_line': 3.0, 'gameday': '2026-10-11', 'gametime': '09:30', 'weekday': 'Sunday'}])
    return wu.predict_week(week, set(), CURRENT, {}, MODELS, {}, 2026, 6)[0]


def test_the_rule_ships_as_the_version_the_registration_names():
    assert config.MODEL_VERSION == '2.6' and 'MODEL_VERSION 2.6' in REG['rule']['ships_as']
    assert config.VERSION_HISTORY[0]['version'] == '2.6'
    assert 'n1_registry.json' in config.VERSION_HISTORY[0]['detail']


def test_at_a_neutral_site_both_models_lose_exactly_their_intercept():
    home, neutral = pick('Home'), pick('Neutral')
    for key, model in (('model_a_home_win_prob', MODELS[0]), ('model_b_home_win_prob', MODELS[1])):
        p, q = home[key], neutral[key]
        shift = np.log(p / (1 - p)) - np.log(q / (1 - q))
        assert shift == pytest.approx(model.intercept_[0], abs=2e-3), key
    assert neutral['home_edge_removed'] is True and neutral['neutral_site'] is True
    assert home['home_edge_removed'] is False and home['neutral_site'] is False


def test_model_b_with_a_negative_intercept_moves_toward_the_home_side():
    """Model B corrects the market's home edge back slightly; with nothing to
    correct, its home probability rises."""
    assert pick('Neutral')['model_b_home_win_prob'] > pick('Home')['model_b_home_win_prob']
    assert pick('Neutral')['model_a_home_win_prob'] < pick('Home')['model_a_home_win_prob']


def test_a_game_the_schedule_does_not_place_keeps_the_home_edge():
    unknown = pick(None)
    assert unknown['neutral_site'] is None and unknown['home_edge_removed'] is False
    assert unknown['model_a_home_win_prob'] == pick('Home')['model_a_home_win_prob']


def test_the_pick_says_which_model_version_made_it():
    assert pick('Neutral')['model_version'] == '2.6'


def test_without_home_edge_is_the_backchecks_function():
    from src.sports.nfl.research import neutral_site_backcheck as bc
    for p, b in ((0.3, 0.25), (0.62, -0.1), (0.5, 0.0)):
        assert wu.without_home_edge(p, b) == pytest.approx(float(bc.without_home_edge(np.array([p]), b)[0]), abs=1e-12)
