"""Stage 38's neutral-site rule N1, registered before it ships (Mark's yes,
2026-10-09): held to itself, to the back-check it quotes, and to the
function the back-check used.

Run with: pytest tests/test_stage38_n1_registry.py -v
"""
import json
from pathlib import Path

import numpy as np

from src.sports.nfl.research import neutral_site_backcheck as bc

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'experiments' / 'nfl' / 'stage38'
REG = json.loads((FOLDER / 'n1_registry.json').read_text(encoding='utf-8'))
BACK = json.loads((FOLDER / 'backcheck' / 'n1_backcheck.json').read_text(encoding='utf-8'))


def test_it_covers_both_models_and_ships_as_its_own_version():
    rule = REG['rule']
    assert rule['models'] == ['model_a', 'model_b']
    assert 'MODEL_VERSION 2.6' in rule['ships_as'] and 'its own pull request' in rule['ships_as']
    assert 'never rewritten' in rule['applies_to'] and 'published backtest is unchanged' in rule['applies_to']
    assert REG['amendments'] == []


def test_an_unplaced_game_keeps_the_home_edge():
    assert 'site_is_neutral None) keeps the home edge' in REG['rule']['statement']


def test_the_quoted_figures_are_the_backchecks_own():
    """Every figure the registration argues from must be in the file it came from."""
    a, b = BACK['summary']['model_a'], BACK['summary']['model_b']
    reading = REG['backcheck']['reading']
    assert f"Model A {a['diff_mean']:+.4f}, 95% {a['diff_ci95'][0]:+.4f} to {a['diff_ci95'][1]:+.4f}" in reading
    assert f"Model B {b['diff_mean']:+.4f}, {b['diff_ci95'][0]:+.4f} to {b['diff_ci95'][1]:+.4f}" in reading
    assert a['n'] == b['n'] and f"on {a['n']} games" in reading
    assert a['diff_ci95'][0] < 0 < a['diff_ci95'][1] and b['diff_ci95'][0] < 0 < b['diff_ci95'][1], \
        'an interval now excludes zero: the reading "neither decides anything" is no longer true'
    assert b['mean_intercept'] < 0 < a['mean_intercept']
    assert 'intercept is negative' in REG['why_a_rule_not_a_test']


def test_the_summary_is_what_its_games_add_up_to():
    for name in ('model_a', 'model_b'):
        rows = [g for g in BACK['games'] if g['model'] == name]
        s = BACK['summary'][name]
        assert len(rows) == s['n'] and sum(g['home_win'] for g in rows) == s['home_won']
        ll = np.mean([bc.log_loss(g['p_neutral_rule'], g['home_win']) - bc.log_loss(g['p_incumbent'], g['home_win'])
                      for g in rows])
        assert round(float(ll), 4) == s['diff_mean']


def test_each_game_had_its_intercept_taken_out_of_the_logit():
    for g in BACK['games']:
        assert abs(float(bc.without_home_edge(np.array([g['p_incumbent']]), g['intercept'])[0])
                   - g['p_neutral_rule']) < 1e-12


def test_taking_the_intercept_out_is_exactly_a_shift_of_the_logit():
    p = np.array([0.2, 0.5, 0.73])
    out = bc.without_home_edge(p, 0.3)
    assert np.allclose(np.log(out / (1 - out)), np.log(p / (1 - p)) - 0.3)
    assert np.allclose(bc.without_home_edge(p, 0.0), p)
