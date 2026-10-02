"""src/research/compare_data_sources.py does its work when run, and nothing when imported.

It is the value-level half of the USE_NFLREADPY revert check (data_loader.py
checks the columns). Until Stage 31 it ran at import -- two full fetches of
a season from nflverse for anyone who imported it, and a crash for anyone
who imported it without network -- and the 2026-09-29 re-audit read it as a
dead module. Nothing here touches the network: the loaders are replaced by
functions that fail the test if they are ever called.

Run with: pytest tests/test_compare_data_sources.py -v
"""
import importlib
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / 'src'

from src.pipeline import data_loader  # noqa: E402


@pytest.fixture
def no_fetching(monkeypatch):
    def refuse(*_a, **_k):
        raise AssertionError('compare_data_sources fetched data at import')
    for name in ('load_schedule', 'load_plays', 'load_snap_counts'):
        monkeypatch.setattr(data_loader, name, refuse)
    sys.modules.pop('src.research.compare_data_sources', None)
    yield
    sys.modules.pop('src.research.compare_data_sources', None)


def test_importing_it_fetches_nothing(no_fetching):
    mod = importlib.import_module('src.research.compare_data_sources')
    assert callable(mod.main)


def test_the_loaders_it_compares_still_exist():
    """Its whole job is to call these three with the toggle both ways; a
    renamed loader would leave it failing only on the day it is needed."""
    for name in ('load_schedule', 'load_plays', 'load_snap_counts'):
        assert callable(getattr(data_loader, name)), f'data_loader.{name} is gone'
    assert isinstance(data_loader.USE_NFLREADPY, bool)
