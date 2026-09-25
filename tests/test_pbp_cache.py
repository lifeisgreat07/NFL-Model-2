"""
The play-by-play cache in src/data_loader.py.

Three properties, each one a way a cache goes wrong quietly:

  OFF BY DEFAULT. Without NFL_PBP_CACHE set, load_plays makes the single
  multi-season call it always made. A cache that switched itself on would
  change what every local run and every test reads.

  NEVER THE CURRENT SEASON. The season in progress changes every week. A
  cached copy of it would freeze the ratings at whatever week was cached
  first, and nothing would fail -- the picks would just stop learning.

  SAME FRAME EITHER WAY. The cached path fetches seasons one at a time and
  stacks them. If that stacking differs from what nflreadpy returns for one
  multi-season call, the cache changes the ratings -- a reproducibility bug
  wearing a performance feature's clothes.

nflreadpy is stubbed via sys.modules (as tests/test_data_loader.py does) so
this runs offline; polars is real, because the cache writes real parquet.

Run with: pytest tests/test_pbp_cache.py -v
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pl = pytest.importorskip('polars')

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import data_loader  # noqa: E402


def _season_frame(season):
    # A column that only one season has, and one whose type differs between
    # seasons: the two ways separately fetched seasons fail to stack.
    data = {'season': [season] * 3, 'week': [1, 2, 3],
            'epa': [0.1, -0.2, 0.3]}
    if season == 2024:
        data['only_2024'] = ['x', 'y', 'z']
        data['mixed'] = [1, 2, 3]
    else:
        data['mixed'] = [1.5, 2.5, 3.5]
    return pl.DataFrame(data)


def _install(monkeypatch, current, calls):
    def load_pbp(seasons):
        calls.append(list(seasons))
        return pl.concat([_season_frame(s) for s in seasons], how='diagonal_relaxed')

    monkeypatch.setitem(sys.modules, 'nflreadpy', SimpleNamespace(
        get_current_season=lambda: current, load_pbp=load_pbp))


def test_without_the_variable_nothing_is_cached(monkeypatch, tmp_path):
    monkeypatch.delenv(data_loader.PBP_CACHE_ENV, raising=False)
    calls = []
    _install(monkeypatch, 2026, calls)
    data_loader.load_plays([2024, 2025, 2026])
    assert calls == [[2024, 2025, 2026]], 'the uncached path must be the one call it always was'


def test_finished_seasons_are_cached_and_reused(monkeypatch, tmp_path):
    monkeypatch.setenv(data_loader.PBP_CACHE_ENV, str(tmp_path))
    calls = []
    _install(monkeypatch, 2026, calls)
    data_loader.load_plays([2024, 2025, 2026])
    assert sorted(p.name for p in tmp_path.iterdir()) == ['pbp_2024.parquet', 'pbp_2025.parquet']

    calls.clear()
    data_loader.load_plays([2024, 2025, 2026])
    assert calls == [[2026]], (
        f'second load fetched {calls}; finished seasons should come from the cache '
        f'and only the current season from nflverse')


def test_the_current_season_is_never_cached(monkeypatch, tmp_path):
    monkeypatch.setenv(data_loader.PBP_CACHE_ENV, str(tmp_path))
    calls = []
    _install(monkeypatch, 2026, calls)
    for _ in range(2):
        data_loader.load_plays([2026])
    assert calls == [[2026], [2026]]
    assert not (tmp_path / 'pbp_2026.parquet').exists()


def test_cached_and_uncached_give_the_same_frame(monkeypatch, tmp_path):
    calls = []
    _install(monkeypatch, 2026, calls)
    monkeypatch.delenv(data_loader.PBP_CACHE_ENV, raising=False)
    uncached = data_loader.load_plays([2024, 2025, 2026])

    monkeypatch.setenv(data_loader.PBP_CACHE_ENV, str(tmp_path))
    first = data_loader.load_plays([2024, 2025, 2026])   # fetches, writes
    second = data_loader.load_plays([2024, 2025, 2026])  # reads back
    for label, frame in (('fetching', first), ('reading the cache', second)):
        assert list(frame.columns) == list(uncached.columns), label
        assert frame.equals(uncached), f'the cached path differs from nflreadpy when {label}'


WORKFLOWS = Path(__file__).parent.parent / '.github' / 'workflows'


def test_only_the_canary_uses_the_cache():
    """The run that makes picks fetches everything fresh, so a stale or
    damaged cache can cost a canary night at worst, never a pick. The
    comment in data_loader.py says so; this is what makes it true."""
    users = sorted(p.name for p in WORKFLOWS.glob('*.yml')
                   if data_loader.PBP_CACHE_ENV in p.read_text(encoding='utf-8'))
    assert users == ['nightly-canary.yml']
    canary = (WORKFLOWS / 'nightly-canary.yml').read_text(encoding='utf-8')
    assert 'actions/cache@' in canary and 'path: .pbp-cache' in canary
    assert f'{data_loader.PBP_CACHE_ENV}: .pbp-cache' in canary


def test_a_not_yet_started_season_is_still_dropped(monkeypatch, tmp_path):
    """The PR #6 crash guard must survive the cache path too."""
    monkeypatch.setenv(data_loader.PBP_CACHE_ENV, str(tmp_path))
    calls = []
    _install(monkeypatch, 2025, calls)
    data_loader.load_plays([2024, 2025, 2026])
    assert [2026] not in calls and all(2026 not in c for c in calls)
