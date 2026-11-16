"""The March Madness tuning and the fallback check (Stage 103 item 2), on tables built by hand.

Run with: pytest tests/test_ncaam_backtest.py -v
"""
import io
import json

import numpy as np
import pandas as pd
import pytest

from src.sports.ncaam import backtest as b
from src.sports.ncaam import fallback as f
from src.sports.ncaam.collector import CollectorError


def curve_table(days=6, per_day=30, seed=1):
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(days):
        for i in range(per_day):
            x = float(rng.normal(0, 9))
            rows.append({'game_id': f'{d}-{i}', 'day': pd.Timestamp('2021-01-01') + pd.Timedelta(days=d), 'walk': x,
                         'home_win': int(rng.random() < 1 / (1 + np.exp(-0.15 * x)))})
    return pd.DataFrame(rows)


def test_the_first_day_has_no_earlier_row_and_is_not_forecast():
    t = curve_table()
    p = b.walk_forward(t)
    assert not [g for g in p.index if g.startswith('0-')]
    assert len(p) == len(t) - 30 and p.between(0, 1).all()


def test_a_days_curve_is_fitted_only_on_earlier_days():
    t = curve_table()
    flipped = t.copy()
    last = flipped['day'] == flipped['day'].max()
    flipped.loc[last, 'home_win'] = 1 - flipped.loc[last, 'home_win']
    assert b.walk_forward(t).equals(b.walk_forward(flipped))
    early = t.copy()
    first = early['day'] == early['day'].min()
    early.loc[first, 'home_win'] = 1 - early.loc[first, 'home_win']
    assert not b.walk_forward(t).equals(b.walk_forward(early)), 'an earlier day does move it'


def test_tuning_searches_the_whole_grid_and_a_tie_goes_to_the_earlier_entry(monkeypatch):
    reg = b.registry()
    seen = []
    monkeypatch.setattr(b.ratings, 'margins', lambda games, h, lam: seen.append((h, lam)) or (h, lam))
    monkeypatch.setattr(b, 'walk_forward', lambda table: table)
    loss = {(60, 3.0): 0.5, (120, 10.0): 0.5}
    monkeypatch.setattr(b, 'scores', lambda p, table: {'games': 1, 'log_loss': loss.get(p, 0.6)})
    out = b.tune(pd.DataFrame({'season': [2014, 2015]}), reg)
    grid = reg['models']['model_a']['grid']
    assert seen == [(h, lam) for h in grid['H_days'] for lam in grid['lambda']] and len(out['grid']) == 16
    assert out['chosen'] == {'H_days': 60, 'lambda': 3.0} and out['seasons'] == [2014, 2015]


def test_the_validation_seasons_are_the_registered_tournaments_seasons():
    assert b.validation_seasons(b.registry()) == [2014, 2015, 2016, 2017, 2018]


def test_a_season_that_has_not_passed_the_fallback_check_is_not_used(tmp_path):
    assert b.checked_seasons(tmp_path) == set()
    (tmp_path / 'checks.json').write_text(json.dumps({'2014': {'checked': True}, '2015': {'checked': False}}),
                                          encoding='utf-8')
    assert b.checked_seasons(tmp_path) == {2014}
    with pytest.raises(CollectorError, match=r'not used: \[2015\]'):
        b.load_history(2014, 2015, tmp_path)


def test_every_registered_season_has_passed_the_check_and_each_entry_counts_its_own_file():
    p = b.registry()['protocol']
    doc = json.loads((b.HISTORY / 'checks.json').read_text(encoding='utf-8'))
    for t in p['validation_tournaments'] + p['confirmation_tournaments']:
        entry = doc[str(t - 1)]
        stored_rows = len(pd.read_csv(b.HISTORY / f'games_{t - 1}.csv', dtype=str))
        assert entry['checked'] is True and entry['stored'] == stored_rows, t
        assert entry['scores_equal'] / entry['stored'] >= 0.99 and entry['needed'] == 0.99
    assert doc['2019']['checked'] is True, '2019-20 has no tournament but its games fit the curve'


def test_the_tuning_on_file_is_the_registered_grid_on_the_registered_games_and_chose_its_lowest_log_loss():
    reg = b.registry()
    doc = json.loads((b.FOLDER / 'results' / 'tuning.json').read_text(encoding='utf-8'))
    grid = reg['models']['model_a']['grid']
    assert [(r['H_days'], r['lambda']) for r in doc['grid']] == [(h, lam) for h in grid['H_days']
                                                                 for lam in grid['lambda']]
    assert doc['seasons'] == b.validation_seasons(reg)
    best = min(doc['grid'], key=lambda r: r['log_loss'])  # min keeps the first of equals
    assert doc['chosen'] == {'H_days': best['H_days'], 'lambda': best['lambda']}
    # Every entry scored the validation seasons' games from 1 January on, less the first curve day (the amendment).
    games = b.ratings.load(min(doc['seasons']), max(doc['seasons']))
    rows = games[games['day'] >= games['season'].map(b.ratings.curve_start)]
    scored = int((rows['day'] > rows['day'].min()).sum())
    assert {r['games'] for r in doc['grid']} == {scored}
    assert all(0.4 < r['log_loss'] < 0.7 and 0.5 < r['accuracy'] < 0.9 for r in doc['grid'])


def test_the_tuning_is_written_once(tmp_path, monkeypatch):
    monkeypatch.setattr(b, 'RESULTS', tmp_path)
    monkeypatch.setattr(b, 'load_history', lambda first, last: None)
    monkeypatch.setattr(b, 'tune', lambda games, reg: pytest.fail('the tuning ran over a result already on file'))
    (tmp_path / 'tuning.json').write_text('{}', encoding='utf-8')
    with pytest.raises(SystemExit, match='run once and never rewritten'):
        b.main([])


def test_the_extension_scores_only_the_added_entries_and_a_tie_keeps_the_registered_one(monkeypatch):
    reg = b.registry()
    seen = []
    monkeypatch.setattr(b.ratings, 'margins', lambda games, h, lam: seen.append((h, lam)) or (h, lam))
    monkeypatch.setattr(b, 'walk_forward', lambda table: table)
    monkeypatch.setattr(b, 'scores', lambda p, table: {'games': 1, 'log_loss': 0.5 if p == (None, 0.3) else 0.7})
    done = {'seasons': [2014], 'grid': [{'H_days': h, 'lambda': lam, 'games': 1, 'log_loss': 0.6}
                                        for h, lam in b.grid_entries(reg)]}
    out = b.extend(pd.DataFrame({'season': [2014]}), reg, done)
    assert seen == [(h, lam) for h in [30, 60, 120, None] for lam in [0.1, 0.3]], 'only the eight new entries run'
    assert out['grid'][:16] == done['grid'] and len(out['grid']) == 24
    assert out['chosen'] == {'H_days': None, 'lambda': 0.3}
    # A new entry that only ties the registered best does not displace it.
    done['grid'][5]['log_loss'] = 0.55
    monkeypatch.setattr(b, 'scores', lambda p, table: {'games': 1, 'log_loss': 0.55})
    tied = b.extend(pd.DataFrame({'season': [2014]}), reg, done)
    assert tied['chosen'] == {'H_days': done['grid'][5]['H_days'], 'lambda': done['grid'][5]['lambda']}


def test_the_extension_on_file_keeps_the_tuning_and_adds_only_the_amendments_entries():
    reg = b.registry()
    tuning = json.loads((b.FOLDER / 'results' / 'tuning.json').read_text(encoding='utf-8'))
    doc = json.loads((b.FOLDER / 'results' / b.EXTENSION).read_text(encoding='utf-8'))
    assert doc['grid'][:16] == tuning['grid'], 'the registered sixteen are copied unchanged'
    assert [(r['H_days'], r['lambda']) for r in doc['grid'][16:]] == b.extension_entries(reg)
    assert doc['seasons'] == tuning['seasons'] == b.validation_seasons(reg)
    assert {r['games'] for r in doc['grid']} == {tuning['grid'][0]['games']}
    best = min(doc['grid'], key=lambda r: r['log_loss'])  # min keeps the first of equals
    assert doc['chosen'] == {'H_days': best['H_days'], 'lambda': best['lambda']} == b.chosen()
    assert all(0.4 < r['log_loss'] < 0.7 and 0.5 < r['accuracy'] < 0.9 for r in doc['grid'])


def test_the_confirmation_uses_the_extensions_choice_once_it_is_on_file(tmp_path):
    (tmp_path / 'tuning.json').write_text(json.dumps({'chosen': {'H_days': None, 'lambda': 1.0}}), encoding='utf-8')
    assert b.chosen(tmp_path) == {'H_days': None, 'lambda': 1.0}
    (tmp_path / b.EXTENSION).write_text(json.dumps({'chosen': {'H_days': None, 'lambda': 0.3}}), encoding='utf-8')
    assert b.chosen(tmp_path) == {'H_days': None, 'lambda': 0.3}


def test_the_extension_is_written_once_and_only_after_the_tuning(tmp_path, monkeypatch):
    monkeypatch.setattr(b, 'RESULTS', tmp_path)
    monkeypatch.setattr(b, 'load_history', lambda first, last: None)
    monkeypatch.setattr(b, 'extend', lambda games, reg, done: pytest.fail('the extension ran'))
    with pytest.raises(SystemExit, match='run that first'):
        b.main(['extend'])
    (tmp_path / 'tuning.json').write_text('{}', encoding='utf-8')
    (tmp_path / b.EXTENSION).write_text('{}', encoding='utf-8')
    with pytest.raises(SystemExit, match='run once and never rewritten'):
        b.main(['extend'])


def test_the_extension_refuses_a_tuning_file_that_is_not_the_registered_grid(tmp_path, monkeypatch):
    monkeypatch.setattr(b, 'RESULTS', tmp_path)
    monkeypatch.setattr(b, 'extend', lambda games, reg, done: pytest.fail('the extension ran'))
    (tmp_path / 'tuning.json').write_text(json.dumps({'seasons': [2014, 2015, 2016, 2017, 2018],
                                                     'grid': [{'H_days': 30, 'lambda': 0.1}]}), encoding='utf-8')
    with pytest.raises(SystemExit, match='not the registered grid'):
        b.main(['extend'])


def stored(n=200, tournament=('5', '6')):
    return pd.DataFrame({'game_id': [str(i) for i in range(n)], 'home_score': '70', 'away_score': '60',
                         'tournament_id': ['22' if str(i) in tournament else '' for i in range(n)]})


def hoopr(frame, drop=(), change=()):
    out = pd.DataFrame({'id': frame['game_id'].astype(int), 'home_score': 70, 'away_score': 60})
    out.loc[out['id'].astype(str).isin(change), 'home_score'] = 71
    return out[~out['id'].astype(str).isin(drop)]


def test_the_fallback_counts_games_with_both_scores_equal_and_names_tournament_games_that_fail():
    s = stored()
    entry = f.compare(s, hoopr(s, drop=('5',), change=('6', '7')))
    assert (entry['stored'], entry['in_fallback'], entry['scores_equal']) == (200, 199, 197)
    assert entry['share'] == 0.985 and entry['checked'] is False
    assert entry['tournament_games_named'] == [{'game_id': '5', 'problem': 'missing'},
                                               {'game_id': '6', 'problem': 'scores differ'}]


def test_ninety_nine_in_a_hundred_passes_and_a_listed_twice_game_counts_once():
    s = stored()
    other = hoopr(s, drop=('0', '1'))
    entry = f.compare(s, pd.concat([other, other.iloc[:10]]))
    assert entry['scores_equal'] == 198 and entry['checked'] is True and entry['tournament_games_named'] == []


def test_the_check_reads_the_file_named_for_the_year_the_season_ends(tmp_path):
    s = stored(20)
    s.to_csv(tmp_path / 'games_2024.csv', index=False)
    asked = []

    def get(url):
        asked.append(url)
        buf = io.BytesIO()
        hoopr(s).to_parquet(buf)
        return buf.getvalue()

    entry = f.check(2024, get, tmp_path)
    assert asked == [f.HOOPR.format(year=2025)] and 'mbb_schedule_2025' in entry['source'] and entry['checked']
