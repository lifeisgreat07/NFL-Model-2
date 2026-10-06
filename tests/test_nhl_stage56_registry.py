"""The NHL's first registration (Stage 56 item 1), held to itself before any
NHL model has a result.

`experiments/nhl/stage56/registry.json` fixes the seasons, the models, the
tuning grid, the budget and each question's decision rule before anything
is fitted. These tests stop it drifting quietly once results exist: a
change has to be an amendment, which this file then names.

Run with: pytest tests/test_nhl_stage56_registry.py -v
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'experiments' / 'nhl' / 'stage56'
REGISTRY = FOLDER / 'registry.json'


def registry():
    return json.loads(REGISTRY.read_text(encoding='utf-8'))


def entry(hid):
    return next(h for h in registry()['hypotheses'] if h['id'] == hid)


def test_it_asks_three_questions_and_takes_two_measurements():
    assert [h['id'] for h in registry()['hypotheses']] == ['H1', 'H2', 'H3', 'M1', 'M2']


def test_three_slots_and_the_level_they_set():
    p = registry()['protocol']
    assert (p['alpha'], p['budget_m']) == (0.05, 3)
    slots = [h['id'] for h in registry()['hypotheses'] if h['spends_slot'] is True]
    assert slots == ['H1', 'H2', 'H3']
    assert '98.33%' in p['budget_rule'] and round(1 - p['alpha'] / p['budget_m'], 4) == 0.9833
    for hid in slots:
        rule = entry(hid)['decision_rule']
        assert '98.33%' in rule and '2024-2025' in rule and 'log loss' in rule


def test_the_seasons_match_the_nfl_split_and_training_starts_with_three_on_three():
    p = registry()['protocol']
    assert (p['validation_seasons'], p['confirmation_seasons'], p['forward_holdout_season']) == (
        [2022, 2023], [2024, 2025], 2026)
    assert p['training_from_season'] == 2015
    assert p['primary_metric'] == 'log_loss' and p['accuracy'] == 'Reported, never decides.'


def test_the_bootstrap_resamples_whole_game_days():
    p = registry()['protocol']
    assert 'game days' in p['bootstrap'] and '5,000' in p['bootstrap'] and '20261005' in p['bootstrap']


def test_tuning_touches_only_the_validation_seasons():
    p = registry()['protocol']
    assert 'validation seasons only' in p['tuning']
    grid = registry()['models']['model_a']['grid']
    assert grid == {'H_days': [30, 60, 120, 240], 'K_shots': [250, 500, 1000, 2000]}


def test_model_b_is_model_a_plus_the_market_and_nothing_else():
    m = registry()['models']
    assert m['model_b']['features'] == m['model_a']['features'] + ['market_logit']
    assert m['model_a']['features'] == ['goal_matchup', 'shot_matchup', 'goalie_matchup']


def test_utah_carries_arizonas_history_by_registration():
    ident = registry()['data']['team_identity']
    for pair in ("Atlanta's history continues as Winnipeg's", "Arizona's as Utah's"):
        assert pair in ident


def test_it_was_registered_before_any_result_exists():
    """Results land in experiments/nhl/stage56/results/. Until they do,
    nothing in the registry may claim an outcome."""
    reg = registry()
    if not (FOLDER / 'results').exists():
        assert all('result' not in h and 'label' not in h for h in reg['hypotheses'])
    assert reg['registered'] == '2026-10-05'
    assert reg['amendments'] == []
