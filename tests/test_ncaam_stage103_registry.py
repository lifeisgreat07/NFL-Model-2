"""The March Madness registration (Stage 103 item 2), held to itself before any NCAAM model has a result.

`experiments/ncaam/stage103/registry.json` fixes the tournaments, the models, the tuning grid, the budget and
each question's decision rule before a rating is fitted. These tests stop it drifting quietly once results exist:
a change has to be an amendment, which this file then names. The figures it argues from are counted from the
stored history.

Run with: pytest tests/test_ncaam_stage103_registry.py -v
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'experiments' / 'ncaam' / 'stage103'
HISTORY = ROOT / 'data' / 'ncaam' / 'history'


def registry():
    return json.loads((FOLDER / 'registry.json').read_text(encoding='utf-8'))


def entry(hid):
    return next(h for h in registry()['hypotheses'] if h['id'] == hid)


def rows(name):
    with (HISTORY / name).open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def test_it_asks_two_questions_and_takes_two_measurements():
    assert [h['id'] for h in registry()['hypotheses']] == ['H1', 'H2', 'M1', 'M2']


def test_two_slots_and_the_level_they_set():
    p = registry()['protocol']
    assert (p['alpha'], p['budget_m']) == (0.05, 2)
    slots = [h['id'] for h in registry()['hypotheses'] if h['spends_slot'] is True]
    assert slots == ['H1', 'H2']
    assert '97.5%' in p['budget_rule'] and round(1 - p['alpha'] / p['budget_m'], 4) == 0.975
    for hid in slots:
        rule = entry(hid)['decision_rule']
        assert '97.5%' in rule and '2021 to 2026 tournaments' in rule and 'log loss' in rule


def test_the_tournaments_and_what_decides():
    p = registry()['protocol']
    assert p['validation_tournaments'] == [2015, 2016, 2017, 2018, 2019]
    assert p['confirmation_tournaments'] == [2021, 2022, 2023, 2024, 2025, 2026]
    assert (p['forward_tournament'], p['training_from_season']) == (2027, 2014)
    assert p['primary_metric'] == 'log_loss' and p['accuracy'] == 'Reported, never decides.'


def test_every_registered_tournament_has_its_seeds_and_the_counts_argued_from_are_the_files():
    p = registry()['protocol']
    games = {t: len(rows(f'seeds_{t - 1}.csv')) for t in p['validation_tournaments'] + p['confirmation_tournaments']}
    assert all(n in (66, 67) for n in games.values()), games
    assert rows('seeds_2019.csv') == [], '2020 had no tournament'
    confirmation = sum(games[t] for t in p['confirmation_tournaments'])
    assert f'{confirmation} games' in entry('H1')['expected']
    assert any(f'{confirmation} confirmation games' in d for d in registry()['disclosures'])
    short = len(rows('games_2020.csv'))
    assert any(f'({short:,} finals)' in d for d in registry()['disclosures'])


def test_a_tournament_is_forecast_from_before_its_first_game():
    lock = registry()['protocol']['lock']
    assert 'frozen before its first game' in lock and "the First Four's first day" in lock
    assert "A later round is never forecast with an earlier round's result." in lock
    assert 'never rewritten' in registry()['forward_test']['lock']


def test_a_forecast_does_not_depend_on_which_club_is_listed_home():
    r = registry()
    assert 'one minus itself when the two clubs are swapped' in r['protocol']['outcome']
    assert 'no intercept and no scaling' in r['models']['model_a']['estimator']
    assert 'no intercept' in r['models']['seed_model']['estimator']
    assert 'forecast as neutral whatever the flag says' in r['protocol']['neutral_site']
    assert 'zero for a neutral game' in r['models']['model_a']['expected_margin']


def test_only_tournament_games_are_scored():
    scored = registry()['protocol']['scored_games']
    assert 'No regular-season or conference-tournament game is ever a scored row' in scored
    assert 'A game declared a no-contest is never scored' in scored


def test_the_bootstrap_resamples_whole_game_days():
    b = registry()['protocol']['bootstrap']
    assert 'whole game days' in b and '5,000' in b and '20261115' in b


def test_tuning_touches_only_the_validation_seasons():
    p = registry()['protocol']
    assert 'validation seasons only (2014-15 to 2018-19)' in p['tuning']
    assert 'strictly before that day' in p['tuning']
    assert registry()['models']['model_a']['grid'] == {'H_days': [30, 60, 120, None],
                                                       'lambda': [1.0, 3.0, 10.0, 30.0]}


def test_the_ratings_read_only_the_seasons_earlier_games():
    m = registry()['models']['model_a']
    assert "the same season's games strictly before the day being forecast" in m['expected_margin']
    assert 'A club with no earlier game that season is rated 0' in m['expected_margin']
    assert 'from 1 January on' in m['curve_rows'] and "before the tournament's first game" in m['curve_rows']


def test_the_seed_model_learns_only_from_earlier_tournaments_in_the_history():
    s = registry()['models']['seed_model']
    assert 'strictly before the tournament being forecast' in s['rows']
    assert 'Nothing from outside the stored history is used' in s['rows']
    assert 'forecast at exactly 0.5' in s['seed_difference']
    assert 'the smaller seed number' in registry()['data']['seeds']


def test_the_market_is_books_only_and_never_a_live_price():
    d = registry()['data']
    assert "A provider whose name contains 'live' is never used" in d['market']
    assert 'sum outside 1.00-1.20 is not used' in d['market'] and 'the median of the books' in d['market']
    assert 'not used until an amendment says which it is' in d['market']
    assert {'accuscore', 'consensus', 'numberfire', 'teamrankings', 'Opening'} <= set(d['not_books'])
    assert not set(d['books']) & set(d['not_books'])
    assert not [b for b in d['books'] + d['not_books'] if 'live' in b.lower()]


def test_no_model_reads_the_market():
    r = registry()
    assert set(r['models']) == {'model_a', 'seed_model', 'higher_seed', 'market'}
    assert r['models']['model_a']['features'] == ['expected_margin']
    assert r['models']['seed_model']['features'] == ['seed_difference']
    assert any('A model that reads the market' in line for line in r['not_in_this_registration'])


def test_the_fallback_is_checked_before_a_season_is_used():
    f = registry()['data']['fallback_check']
    assert 'Before a season is used' in f and 'at least 99% of the stored finals' in f
    assert 'every NCAA tournament game that is missing there or differs is named' in f
    assert 'hoopR mirrors ESPN' in f


def test_losing_to_the_seeds_changes_what_makes_the_bracket():
    assert "REJECT: the bracket's forecasts come from the seed model" in entry('H1')['consequence']
    assert 'It changes no forecast' in entry('H2')['consequence']


def test_it_was_registered_before_any_result_exists():
    """Results land in experiments/ncaam/stage103/results/. Until they do, nothing in the registry may claim an
    outcome, and nothing has amended it."""
    reg = registry()
    if not (FOLDER / 'results').exists():
        assert all('result' not in h and 'label' not in h for h in reg['hypotheses'])
    assert reg['registered'] == '2026-11-15'
    # Two amendments. The first, written with the tuning code and before it ran on a stored season: the first
    # curve day. The second, after the tuning's scores, which says so: lambda 0.1 and 0.3 added.
    first, second = reg['amendments']
    assert (first['entry'], first['date'], first['before_any_result']) == ('protocol.tuning', '2026-11-16', True)
    assert 'not forecast and not scored in the tuning' in first['change']
    assert 'before it had run on any stored season' in first['seen']
    assert (second['entry'], second['before_any_result']) == ('models.model_a.grid', False)
    assert 'No confirmation tournament had been scored' in second['seen']
    assert 'second look at the validation seasons' in second['change']


def test_the_grid_extension_adds_only_smaller_lambdas_and_keeps_a_tie_with_the_registered_entry():
    m = registry()['models']['model_a']
    assert m['grid_extension']['lambda'] == [0.1, 0.3]
    assert not set(m['grid_extension']['lambda']) & set(m['grid']['lambda'])
    assert 'ties to the earlier entry, so a tie keeps the registered one' in m['grid_extension']['rule']
    assert 'the grid is not widened again' in m['grid_extension']['rule']
