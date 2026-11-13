"""MLB's first registration (Stage 98 item 1), held to itself before any MLB
model has a result.

`experiments/mlb/stage98/registry.json` fixes the seasons, the models, the
tuning grid, the budget and each question's decision rule before anything
is fitted. These tests stop it drifting quietly once results exist: a
change has to be an amendment, which this file then names.

Run with: pytest tests/test_mlb_stage98_registry.py -v
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'experiments' / 'mlb' / 'stage98'
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
        assert '98.33%' in rule and '2025-2026' in rule and 'log loss' in rule


def test_the_seasons_and_what_decides():
    p = registry()['protocol']
    assert (p['validation_seasons'], p['confirmation_seasons'], p['forward_holdout_season']) == (
        [2023, 2024], [2025, 2026], 2027)
    assert p['training_from_season'] == 2010
    assert p['primary_metric'] == 'log_loss' and p['accuracy'] == 'Reported, never decides.'


def test_the_bootstrap_resamples_whole_game_days():
    p = registry()['protocol']
    assert 'whole game days' in p['bootstrap'] and '5,000' in p['bootstrap'] and '20261112' in p['bootstrap']


def test_spring_training_exhibition_and_all_star_games_are_never_used():
    games = registry()['protocol']['games']
    assert 'Spring training, exhibition and All-Star games are never used' in games
    assert 'A postponed or cancelled game is never scored' in games


def test_a_game_is_its_gamepk_and_a_relisted_game_counts_once():
    key = registry()['protocol']['game_key']
    assert "The Stats API's gamePk" in key and 'one row per gamePk, the last listing wins' in key


def test_a_neutral_site_game_gets_no_home_edge():
    p = registry()['protocol']
    assert 'gets no fitted home edge' in p['neutral_site']
    assert "home club's own venue for that season" in p['neutral_site']
    assert 'zero for a neutral game' in registry()['models']['model_a']['run_matchup']


def test_tuning_touches_only_the_validation_seasons():
    p = registry()['protocol']
    assert 'validation seasons only' in p['tuning']
    grid = registry()['models']['model_a']['grid']
    assert grid == {'H_days': [60, 120, 240, 480], 'lambda': [1.0, 3.0, 10.0, 30.0, 100.0],
                    'K_outs': [150.0, 300.0, 600.0, 1200.0, 2400.0]}


def test_model_b_is_model_a_plus_the_market_and_nothing_else():
    m = registry()['models']
    assert m['model_b']['features'] == m['model_a']['features'] + ['market_logit']
    assert m['model_a']['features'] == ['run_matchup', 'starter_matchup']


def test_the_starter_term_reads_only_earlier_appearances_and_is_shrunk():
    s = registry()['models']['model_a']['starter_matchup']
    assert 'over his earlier appearances' in s and 'K_outs' in s and '150 as first registered' in s
    assert "every pitcher's appearances" in s and 'as a starter or in relief' in s
    assert "(weighted runs + K_outs x the league's runs per out) / (weighted outs + K_outs) x 27" in s
    assert 'A starter with no earlier appearance gets the league rate' in s
    assert "live it is the Stats API's probable pitcher" in s


def test_a_live_price_is_never_used():
    assert 'A price from a provider marked live is never used' in registry()['data']['market']


def test_the_fallback_is_checked_before_a_season_is_used():
    f = registry()['data']['fallback_check']
    assert 'Before a season is used' in f and 'at least 99% must agree' in f
    assert 'Every disagreement is listed' in f
    assert 'not used until it has' in f


def test_clubs_are_keyed_on_the_stats_api_id():
    c = registry()['data']['club_identity']
    assert "The Stats API's club id" in c and 'never typed by hand' in c


def test_it_was_registered_before_any_result_exists():
    """Results land in experiments/mlb/stage98/results/. Until they do,
    nothing in the registry may claim an outcome."""
    reg = registry()
    if not (FOLDER / 'results').exists():
        assert all('result' not in h and 'label' not in h for h in reg['hypotheses'])
    assert reg['registered'] == '2026-11-12'
    assert [a['entry'] for a in reg['amendments']] == ['models.model_a.grid', 'models.model_a.starter_matchup',
                                                       'protocol.games']
    assert all(a['before_any_result'] and a['date'] == '2026-11-12' for a in reg['amendments'])
