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
