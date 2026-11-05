"""The NHL end-to-end tests share one feature table (Stage 86 item 2).

Run with: pytest tests/test_shared_tables.py -v
"""
import pandas as pd

from tests import shared_tables as st


def games(day='2026-10-10'):
    return pd.DataFrame({'game_id': ['1', '2'], 'day': [day, day], 'home_goals': [3, 1]})


def counting():
    calls = []

    def features(g, half_life, ks, first_day=None):
        calls.append((len(g), half_life, tuple(ks), first_day))
        return pd.DataFrame({'game_id': g['game_id'], 'x': [half_life] * len(g)})
    return features, calls


def test_an_identical_call_is_answered_from_memory():
    st._TABLES.clear()
    f, calls = counting()
    shared = st.remembering(f)
    a = shared(games(), 30.0, [500])
    b = shared(games(), 30.0, (500,))
    assert len(calls) == 1 and a.equals(b)


def test_any_difference_in_content_or_settings_is_computed_again():
    st._TABLES.clear()
    f, calls = counting()
    shared = st.remembering(f)
    shared(games(), 30.0, [500])
    shared(games('2026-10-11'), 30.0, [500])
    shared(games(), 31.0, [500])
    shared(games(), 30.0, [400])
    shared(games(), 30.0, [500], first_day='2026-10-01')
    changed = games()
    changed['home_goals'] = changed['home_goals'].astype(float)
    shared(changed, 30.0, [500])
    shared(games().rename(columns={'home_goals': 'away_goals'}), 30.0, [500])
    assert len(calls) == 7


def test_each_caller_gets_its_own_copy():
    st._TABLES.clear()
    f, _ = counting()
    shared = st.remembering(f)
    a = shared(games(), 30.0, [500])
    a.loc[0, 'x'] = -1.0
    assert shared(games(), 30.0, [500]).loc[0, 'x'] == 30.0


def test_the_nhl_end_to_end_tests_use_it():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for name, n in (('test_nhl_sources_down.py', 1), ('test_daily_end_to_end.py', 1)):
        assert (root / 'tests' / name).read_text(encoding='utf-8').count('    share_nhl_features(monkeypatch)\n') == n, name



def test_the_nba_tables_are_remembered_on_every_argument():
    st._TABLES.clear()
    calls = []

    def availability_table(g, m, half_life, avail=None):
        calls.append('a')
        return pd.Series([half_life] * len(g), index=g['game_id'])
    shared = st.remembering_any(availability_table)
    m = pd.DataFrame({'game_id': ['1'], 'player_id': ['p'], 'minutes': [30.0]})
    a = shared(games(), m, 20.0)
    shared(games(), m.copy(), 20.0)
    assert len(calls) == 1 and a.equals(shared(games(), m, 20.0))
    shared(games(), m.assign(minutes=[31.0]), 20.0)
    shared(games(), m, 21.0)
    avail = pd.Series([1.0], name='a')
    shared(games(), m, 20.0, avail=avail)
    shared(games(), m, 20.0, avail=avail * 2)
    assert len(calls) == 5
    a.iloc[0] = -1.0
    assert shared(games(), m, 20.0).iloc[0] == 20.0, 'each caller gets its own copy'


def test_the_nba_end_to_end_tests_use_it():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for name, n in (('test_nba_sources_down.py', 1), ('test_daily_end_to_end.py', 1), ('test_after_save.py', 1)):
        assert (root / 'tests' / name).read_text(encoding='utf-8').count('    share_nba_tables(monkeypatch)\n') == n, name
