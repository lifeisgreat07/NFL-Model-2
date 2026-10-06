"""The NHL's Stage 56 results, held to the registration that came before them.

`experiments/nhl/stage56/results/` is written by `src/sports/nhl/backtest.py`.
Every figure a page or a document quotes from it must be in these files,
and every label must follow from its interval by the registered rule, so a
label cannot be edited by hand into something the numbers do not say.

Run with: pytest tests/test_nhl_stage56_results.py -v
"""
import json
from pathlib import Path

import pytest

from src.sports.nhl import backtest

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'experiments' / 'nhl' / 'stage56' / 'results'


def load(name):
    return json.loads((RESULTS / name).read_text(encoding='utf-8'))


REG = backtest.registry()
TUNING = load('tuning.json')
CONFIRM = load('confirmation.json')


def test_tuning_searched_the_whole_registered_grid_on_validation_only():
    grid = REG['models']['model_a']['grid']
    searched = {(r['H_days'], r['K_shots']) for r in TUNING['grid']}
    assert searched == {(h, k) for h in grid['H_days'] for k in grid['K_shots']}
    assert TUNING['seasons'] == REG['protocol']['validation_seasons']


def test_the_chosen_values_are_the_lowest_validation_log_loss():
    best = min(TUNING['grid'], key=lambda r: r['log_loss'])
    assert TUNING['chosen'] == {'H_days': best['H_days'], 'K_shots': best['K_shots']}
    assert (CONFIRM['H_days'], CONFIRM['K_shots']) == (best['H_days'], best['K_shots'])


def test_confirmation_is_on_the_registered_seasons_at_the_registered_level():
    p = REG['protocol']
    assert CONFIRM['seasons'] == p['confirmation_seasons']
    for q in CONFIRM['questions'].values():
        assert q['level'] == round(1 - p['alpha'] / p['budget_m'], 4) == 0.9833


def test_each_question_compares_what_its_registration_names():
    expect = {'H1': ('model_a', 'base_rate'), 'H2': ('model_b', 'model_a'), 'H3': ('model_b', 'market'),
              'M1': ('model_a', 'model_a_no_goalie')}
    got = {k: (q['candidate'], q['incumbent']) for k, q in CONFIRM['questions'].items()}
    assert got == expect


@pytest.mark.parametrize('hid', ['H1', 'H2', 'H3'])
def test_every_label_follows_from_its_interval(hid):
    q = CONFIRM['questions'][hid]
    assert q['low'] <= q['diff'] <= q['high']
    assert q['label'] == backtest.label(q)


def test_the_measurement_carries_no_label():
    assert 'label' not in CONFIRM['questions']['M1']


def test_the_market_and_model_b_score_the_same_priced_games():
    s = CONFIRM['scores']
    assert s['market']['games'] == s['model_b']['games'] <= s['model_a']['games'] == s['base_rate']['games']
