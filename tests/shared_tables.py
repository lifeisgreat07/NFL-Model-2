"""
One NHL feature table for the tests that drive the whole daily run.

Stage 86 item 2 (the 2026-11-02 review). Four NHL end-to-end tests (three in
tests/test_nhl_sources_down.py, and the daily run in
tests/test_daily_end_to_end.py, which runs it twice) each built the
feature table over every game since 2015, about 40 of the 45 seconds a
run takes, and all over the same committed history. `share_nhl_features`
makes `ratings.features` remember its answer for the run of tests, keyed on
the full content of its input and its settings, so an identical call is
answered from memory and any different call is computed as before. Each
caller gets its own copy.

Stage 96 item 49 (audit 7, T12) adds the NBA half: its four tests that drive
the whole daily run (the end-to-end run, the two sources-down runs and the
after-save run) each built the availability table and the feature table over
every game since 2019, about 40 of the 45 seconds a run took. `share_nba_tables`
remembers `ratings.availability_table` and `ratings.features` the same way,
keyed on the content of every frame argument and the value of every other.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any

import pandas as pd

_TABLES: dict[tuple[Any, ...], pd.DataFrame] = {}


def content_key(games: pd.DataFrame) -> str:
    """A digest of the frame's values, index, column names and dtypes."""
    h = hashlib.sha256()
    h.update(pd.util.hash_pandas_object(games, index=True).values.tobytes())
    h.update(repr([(str(c), str(t)) for c, t in games.dtypes.items()]).encode())
    return h.hexdigest()


def remembering(features: Callable[..., pd.DataFrame]) -> Callable[..., pd.DataFrame]:
    def wrapped(games: pd.DataFrame, half_life: float, ks: Any, first_day: str | None = None) -> pd.DataFrame:
        ks = tuple(ks)
        key = (content_key(games), float(half_life), ks, first_day)
        if key not in _TABLES:
            _TABLES[key] = features(games, half_life, ks, first_day)
        return _TABLES[key].copy()
    wrapped.__wrapped__ = features  # type: ignore[attr-defined]
    return wrapped


def share_nhl_features(monkeypatch) -> None:
    """Patch the NHL's ratings.features for this test with the remembering version."""
    from src.sports.nhl import ratings
    original = getattr(ratings.features, '__wrapped__', ratings.features)
    monkeypatch.setattr(ratings, 'features', remembering(original))


def _part(x: Any) -> Any:
    if isinstance(x, pd.DataFrame):
        return ('frame', content_key(x))
    if isinstance(x, pd.Series):
        h = hashlib.sha256(pd.util.hash_pandas_object(x, index=True).values.tobytes())
        h.update(repr((str(x.name), str(x.dtype))).encode())
        return ('series', h.hexdigest())
    if isinstance(x, (list, tuple)):
        return ('seq', tuple(_part(i) for i in x))
    return ('value', repr(x))


def remembering_any(fn: Callable[..., Any]) -> Callable[..., Any]:
    """`fn` remembered on the content of every argument; each caller gets its own copy."""
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        key = (fn.__module__, fn.__qualname__, tuple(_part(a) for a in args),
               tuple(sorted((k, _part(v)) for k, v in kwargs.items())))
        if key not in _TABLES:
            _TABLES[key] = fn(*args, **kwargs)
        return _TABLES[key].copy(deep=True)
    wrapped.__wrapped__ = fn  # type: ignore[attr-defined]
    return wrapped


def share_nba_tables(monkeypatch) -> None:
    """Patch the NBA's ratings.availability_table and ratings.features for this test with remembering versions."""
    from src.sports.nba import ratings
    for name in ('availability_table', 'features'):
        original = getattr(getattr(ratings, name), '__wrapped__', getattr(ratings, name))
        monkeypatch.setattr(ratings, name, remembering_any(original))
