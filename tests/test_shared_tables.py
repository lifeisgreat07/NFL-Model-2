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
