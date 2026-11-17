"""The March Madness confirmation's code (Stage 103 item 2), on tables built by hand. Nothing here reads a stored
tournament's result: the confirmation itself has not been run.

Run with: pytest tests/test_ncaam_confirm.py -v
"""
import copy
import json

import numpy as np
import pandas as pd
import pytest

from src.sports.ncaam import backtest as b
from src.sports.ncaam.collector import CollectorError

SEEDS = {0: (1, 16), 1: (4, 13), 2: (9, 8), 3: (11, 11)}


def table():
    """Three seasons (2019 to 2021): forty days of curve rows from 1 January, then a tournament of three days and
    four games a day. The 2021 tournament's `walk` is nonsense on purpose: only `lock` may forecast its games.
    (An earlier tournament's `walk` is a curve row for a later one, as registered.)"""
    rng = np.random.default_rng(11)
    rows = []
    for season in (2019, 2020, 2021):
        for d in range(40):
            for i in range(6):
                x = float(rng.normal(0, 9))
                rows.append({'game_id': f'{season}-c{d}-{i}', 'season': season, 'tournament': False,
                             'day': pd.Timestamp(year=season + 1, month=1, day=1) + pd.Timedelta(days=d),
                             'walk': x, 'lock': np.nan, 'home_win': int(rng.random() < 1 / (1 + np.exp(-0.15 * x)))})
        for r in range(3):
            for i in range(4):
                x = float(rng.normal(3, 8))
                rows.append({'game_id': f'{season}-t{r}-{i}', 'season': season, 'tournament': True,
                             'day': pd.Timestamp(year=season + 1, month=3, day=16 + 2 * r),
                             'walk': x + (50 if season == 2020 else 0), 'lock': x,
                             'home_win': int(rng.random() < 1 / (1 + np.exp(-0.15 * x)))})
    return pd.DataFrame(rows)


def seeded(t):
    games = t[t['tournament']]
    pairs = [SEEDS[int(g[-1])] for g in games['game_id']]
    return pd.DataFrame({'game_id': games['game_id'].to_numpy(), 'home_seed': [p[0] for p in pairs],
                         'away_seed': [p[1] for p in pairs],
                         'seed_difference': [float(p[1] - p[0]) for p in pairs]})


def flipped(t, mask):
    out = t.copy()
    out.loc[mask, 'home_win'] = 1 - out.loc[mask, 'home_win']
    return out


def test_a_tournament_game_is_forecast_from_its_locked_margin_never_its_walk():
    t = table()
    base = b.lock_forecasts(t, seeded(t), [2021])['model_a']
    assert len(base) == 12 and base.between(0.01, 0.99).all(), 'a walk of fifty points would be a certainty'
    other = t.copy()
    other.loc[other['tournament'] & (other['season'] == 2020), 'walk'] = 0.0
    assert b.lock_forecasts(other, seeded(t), [2021])['model_a'].equals(base)
    moved = t.copy()
    moved.loc[moved['game_id'] == '2020-t2-0', 'lock'] += 5
    assert b.lock_forecasts(moved, seeded(t), [2021])['model_a']['2020-t2-0'] > base['2020-t2-0']


def test_a_tournaments_curve_and_seed_model_never_see_its_own_games():
    t = table()
    base = b.lock_forecasts(t, seeded(t), [2021])
    own = flipped(t, (t['season'] == 2020) & t['tournament'])
    after = b.lock_forecasts(own, seeded(t), [2021])
    assert after['model_a'].equals(base['model_a']) and after['seed_model'].equals(base['seed_model'])
    earlier_curve = flipped(t, (t['season'] == 2020) & ~t['tournament'] & (t['day'] < '2021-01-20'))
    assert not b.lock_forecasts(earlier_curve, seeded(t), [2021])['model_a'].equals(base['model_a'])
    earlier_tournament = flipped(t, (t['season'] == 2019) & t['tournament'])
    assert not b.lock_forecasts(earlier_tournament, seeded(t), [2021])['seed_model'].equals(base['seed_model'])


def test_equal_seeds_are_a_coin_flip_and_a_better_seed_is_favoured_by_what_earlier_tournaments_showed():
    t = table()
    t.loc[t['tournament'], 'home_win'] = [int(g[-1] in '01') for g in t.loc[t['tournament'], 'game_id']]
    p = b.lock_forecasts(t, seeded(t), [2022])['seed_model']
    assert p['2021-t0-3'] == 0.5
    assert p['2021-t0-0'] > p['2021-t0-1'] > 0.5 > p['2021-t0-2'], 'a 1 over a 16, a 4 over a 13, a 9 under an 8'


def test_the_first_tournament_in_the_history_and_an_unseeded_game_stop_the_run():
    t = table()
    with pytest.raises(CollectorError, match='the 2020 tournament needs'):
        b.lock_forecasts(t, seeded(t), [2020])
    with pytest.raises(CollectorError, match='2021-t1-2'):
        b.lock_forecasts(t, seeded(t)[lambda s: s['game_id'] != '2021-t1-2'], [2021, 2022])


def confirmed(monkeypatch, prices=None):
    t = table()
    monkeypatch.setattr(b.ratings, 'margins', lambda games, h, lam: t)
    reg = copy.deepcopy(b.registry())
    reg['protocol']['confirmation_tournaments'] = [2021, 2022]
    if prices is None:
        priced = t[t['tournament'] & (t['season'] >= 2020)].iloc[::2]
        prices = pd.DataFrame({'game_id': priced['game_id'].to_numpy(), 'home_prob': 0.6, 'books': 3})
    return t, b.confirm(t, prices, seeded(t), reg, {'H_days': None, 'lambda': 1.0})


def test_the_confirmation_answers_the_registered_questions_at_the_registered_level(monkeypatch):
    t, out = confirmed(monkeypatch)
    q = out['questions']
    assert list(q) == ['H1', 'H2', 'M1', 'M2'] and out['tournaments'] == [2021, 2022]
    assert (q['H1']['candidate'], q['H1']['incumbent']) == ('model_a', 'seed_model')
    assert (q['H2']['candidate'], q['H2']['incumbent']) == ('model_a', 'market')
    assert (q['M1']['candidate'], q['M1']['incumbent']) == ('market', 'seed_model')
    assert q['H1']['label'] in ('ACCEPT', 'REJECT', 'INCONCLUSIVE') and 'label' in q['H2'] and 'label' not in q['M1']
    assert {q[h]['level'] for h in ('H1', 'H2', 'M1')} == {0.975}
    assert (q['H1']['games'], q['H1']['days']) == (24, 6), 'every game of both tournaments, in whole game days'
    assert q['H2']['games'] == q['M1']['games'] == 12, 'only the priced games'
    assert set(out['scores']) == {'model_a', 'seed_model', 'market'} and out['scores']['market']['games'] == 12


def test_the_interval_is_the_registered_bootstrap(monkeypatch):
    p = b.registry()['protocol']
    assert str(b.SEED) in p['bootstrap'] and 'whole game days' in p['bootstrap']
    seen = {}
    real = b.interval
    monkeypatch.setattr(b, 'interval', lambda diff, days, seed, level: seen.update(seed=seed, n=len(diff)) or
                        real(diff, days, seed, level))
    confirmed(monkeypatch)
    assert seen['seed'] == 20261115


def test_m2_counts_winners_only_on_games_between_different_seeds(monkeypatch):
    t, out = confirmed(monkeypatch)
    m2 = out['questions']['M2']
    games = t[t['tournament'] & (t['season'] >= 2020) & ~t['game_id'].str.endswith('-3')]
    better_home = games['game_id'].str[-1].isin(['0', '1'])
    # Every other tournament game is priced, which are the 1 v 16 and 9 v 8 games: none of them equal seeds.
    assert m2['games'] == 18 and m2['model_a_games'] == 18 and m2['market_games'] == 12
    assert m2['higher_seed'] == pytest.approx((better_home == (games['home_win'] == 1)).mean())
    assert 'label' not in m2


def run_confirm(monkeypatch, tmp_path, chosen=None, load=None):
    monkeypatch.setattr(b, 'RESULTS', tmp_path)
    (tmp_path / 'tuning.json').write_text(json.dumps({'chosen': chosen or {'H_days': None, 'lambda': 1.0}}),
                                          encoding='utf-8')
    monkeypatch.setattr(b.market, 'load', load or (lambda seasons, books, not_books: (pd.DataFrame(), [])))
    monkeypatch.setattr(b, 'load_history', lambda first, last: pytest.fail('the history was read'))
    return b.main(['confirm'])


def test_the_confirmation_is_written_once(monkeypatch, tmp_path):
    (tmp_path / 'confirmation.json').write_text('{}', encoding='utf-8')
    with pytest.raises(SystemExit, match='run once and never rewritten'):
        run_confirm(monkeypatch, tmp_path)


def test_a_setting_outside_the_registered_grid_is_refused(monkeypatch, tmp_path):
    with pytest.raises(SystemExit, match='not in the registered grid or its extension'):
        run_confirm(monkeypatch, tmp_path, chosen={'H_days': None, 'lambda': 0.05})


def test_the_extensions_choice_is_the_one_confirmed(monkeypatch, tmp_path):
    """Once results/tuning_extension.json is on file (the second amendment), its choice is confirmed, and a
    lambda the extension added is an entry like any other."""
    seen = {}
    (tmp_path / b.EXTENSION).write_text(json.dumps({'chosen': {'H_days': 120, 'lambda': 0.1}}), encoding='utf-8')
    monkeypatch.setattr(b, 'load_history', lambda first, last: pd.DataFrame())
    monkeypatch.setattr(b, 'seeds', lambda seasons: pd.DataFrame())
    monkeypatch.setattr(b, 'confirm', lambda games, prices, seeded, reg, setting: seen.update(setting) or
                        {'questions': {}})
    monkeypatch.setattr(b, 'RESULTS', tmp_path)
    (tmp_path / 'tuning.json').write_text(json.dumps({'chosen': {'H_days': None, 'lambda': 1.0}}), encoding='utf-8')
    monkeypatch.setattr(b.market, 'load', lambda seasons, books, not_books: (pd.DataFrame(), []))
    assert b.main(['confirm']) == 0
    assert seen == {'H_days': 120, 'lambda': 0.1}


def test_a_missing_market_file_and_an_unclassified_provider_are_refused(monkeypatch, tmp_path):
    def missing(seasons, books, not_books):
        raise FileNotFoundError('market_2020.csv')

    with pytest.raises(SystemExit, match='has no market file'):
        run_confirm(monkeypatch, tmp_path, load=missing)
    with pytest.raises(SystemExit, match=r"an amendment is needed: \['NewBook'\]"):
        run_confirm(monkeypatch, tmp_path, load=lambda seasons, books, not_books: (pd.DataFrame(), ['NewBook']))


def test_the_market_is_read_for_the_confirmation_tournaments_seasons_with_the_registered_lists(monkeypatch, tmp_path):
    seen = {}

    def load(seasons, books, not_books):
        seen.update(seasons=list(seasons), books=books, not_books=not_books)
        return pd.DataFrame(), ['stop here']

    with pytest.raises(SystemExit):
        run_confirm(monkeypatch, tmp_path, load=load)
    reg = b.registry()
    assert seen == {'seasons': [2020, 2021, 2022, 2023, 2024, 2025], 'books': reg['data']['books'],
                    'not_books': reg['data']['not_books']}


def test_the_seeds_are_read_as_the_away_seed_minus_the_home_seed(tmp_path):
    (tmp_path / 'seeds_2020.csv').write_text('game_id,home_seed,away_seed,filled\n7,1,16,\n8,11,11,\n',
                                             encoding='utf-8')
    s = b.seeds([2019, 2020], tmp_path)
    assert list(s['game_id']) == ['7', '8'] and list(s['seed_difference']) == [15.0, 0.0]


def test_the_confirmation_on_file_is_the_registered_run_and_its_labels_follow_their_intervals():
    """results/confirmation.json, written once by `python -m src.sports.ncaam.backtest confirm` on 2026-11-16."""
    reg = b.registry()
    doc = json.loads((b.FOLDER / 'results' / 'confirmation.json').read_text(encoding='utf-8'))
    p = reg['protocol']
    assert doc['tournaments'] == p['confirmation_tournaments']
    assert {'H_days': doc['H_days'], 'lambda': doc['lambda']} == b.chosen(), 'the setting the tuning chose'
    level = round(1 - p['alpha'] / p['budget_m'], 4)
    assert set(doc['questions']) == {'H1', 'H2', 'M1', 'M2'}
    assert {s['games'] for s in doc['scores'].values()} == {401}, 'every tournament game, forecast by all three'
    for hid in ('H1', 'H2', 'M1'):
        q = doc['questions'][hid]
        assert q['level'] == level and q['low'] <= q['diff'] <= q['high'], hid
        assert q['games'] == 401, hid
        if hid != 'M1':
            assert q['label'] == b.label({'low': q['low'], 'high': q['high'], 'diff': q['diff']}), hid
        else:
            assert 'label' not in q, 'M1 is a measurement'
    assert 'label' not in doc['questions']['M2']

