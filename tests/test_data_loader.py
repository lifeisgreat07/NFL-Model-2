"""
Regression test for the "season not started yet" crash that broke the
2026 Week 1 offseason routine run (see PR #6): nflreadpy's
get_current_season() doesn't consider a season current until the
Thursday after Labor Day, and load_pbp()/load_snap_counts() hard-reject
any season past that point with ValueError. weekly_update.py always
includes the *target* season in what it asks load_plays/load_snap_counts
for, even on early "is it time to lock in yet" runs -- so requesting a
season nflreadpy doesn't think has started must be silently dropped
before hitting nflreadpy, not left to crash the whole pipeline.

These tests stub nflreadpy itself via sys.modules (rather than hitting
the network) so they run offline and fast, and assert against the real
production code in src/data_loader.py -- not a reimplementation of its
filtering logic -- by inspecting exactly what season list it passed
through to the stubbed fetch functions.

Run with: pytest tests/test_data_loader.py -v
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class _FakePolarsDF:
    """Stand-in for the polars DataFrame nflreadpy actually returns --
    data_loader.py only ever calls .to_pandas() on the result, so that's
    the only method this needs."""
    def __init__(self, rows=None):
        self._rows = rows or []

    def to_pandas(self):
        return pd.DataFrame(self._rows)


def _install_fake_nflreadpy(monkeypatch, current_season, calls):
    """Stubs sys.modules['nflreadpy'] so the `import nflreadpy as nfl`
    inside load_plays/load_snap_counts binds to fakes instead of hitting
    the network or requiring the real package. `calls` records the season
    list each fake fetch function actually received, so tests can assert
    on what production code passed through post-filtering."""
    def fake_get_current_season():
        return current_season

    def fake_load_pbp(seasons):
        calls['load_pbp'] = list(seasons)
        return _FakePolarsDF()

    def fake_load_snap_counts(seasons):
        calls['load_snap_counts'] = list(seasons)
        return _FakePolarsDF()

    fake_module = SimpleNamespace(
        get_current_season=fake_get_current_season,
        load_pbp=fake_load_pbp,
        load_snap_counts=fake_load_snap_counts,
    )
    monkeypatch.setitem(sys.modules, 'nflreadpy', fake_module)


def test_load_plays_drops_not_yet_started_season(monkeypatch, capsys):
    """The exact bug from PR #6: requesting [2024, 2025, 2026] while
    nflreadpy still considers 2025 the current season must silently drop
    2026 -- not crash -- pass only [2024, 2025] through to load_pbp, and
    log that 2026 was skipped."""
    import data_loader

    calls = {}
    _install_fake_nflreadpy(monkeypatch, current_season=2025, calls=calls)

    data_loader.load_plays([2024, 2025, 2026])

    assert calls['load_pbp'] == [2024, 2025], \
        "2026 (not yet started per nflreadpy) must be filtered out before calling load_pbp"

    out = capsys.readouterr().out
    assert '2026' in out and 'Skipping' in out, \
        "dropping a not-yet-started season must be logged, not silent"


def test_load_snap_counts_drops_not_yet_started_season(monkeypatch):
    """Same not-started-yet filtering as load_plays, for load_snap_counts
    -- this is the second call site the original crash hit."""
    import data_loader

    calls = {}
    _install_fake_nflreadpy(monkeypatch, current_season=2025, calls=calls)

    data_loader.load_snap_counts([2024, 2025, 2026])

    assert calls['load_snap_counts'] == [2024, 2025], \
        "2026 (not yet started per nflreadpy) must be filtered out before calling load_snap_counts"


def test_load_plays_passes_all_seasons_once_current(monkeypatch):
    """Once nflreadpy's current season catches up (e.g. the Thursday
    after Labor Day), nothing should be filtered out -- guards against an
    overly aggressive fix that drops seasons it shouldn't."""
    import data_loader

    calls = {}
    _install_fake_nflreadpy(monkeypatch, current_season=2026, calls=calls)

    data_loader.load_plays([2024, 2025, 2026])

    assert calls['load_pbp'] == [2024, 2025, 2026]


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
