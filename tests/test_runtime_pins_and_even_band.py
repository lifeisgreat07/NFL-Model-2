"""
Two of audit 7's suite items (docs/history/11-audit7-2026-11-04.md, Stage 96).

Item 42 (T3): the suite asserts at run time that the pandas and numpy it runs
on are the ones requirements.txt pins. Every published figure depends on
pandas' aggregation (data/nfl/pandas_version_experiment.json: a newer pandas
moves the EPA-built models in the third and fourth decimal), so a suite that
passed on another pandas would vouch for figures it did not reproduce.

Item 45 (T2): the even band, behaviourally. A chance within EVEN_BAND points
of 50 picks nobody: 0.53, 0.47 and 0.56 are each outside the 2-point band
and favour a side; 0.51 and 0.49 are inside it.

Run with: pytest tests/test_runtime_pins_and_even_band.py -v
"""
import re
from pathlib import Path

import numpy
import pandas
import pytest

from src.core.template_parts import APP_SCRIPT
from src.site import home

ROOT = Path(__file__).resolve().parents[1]


def pin(name):
    m = re.search(rf'^{name}==(\S+)$', (ROOT / 'requirements.txt').read_text(encoding='utf-8'), re.M)
    assert m, f'requirements.txt does not pin {name}'
    return m.group(1)


@pytest.mark.parametrize('module, name', [(pandas, 'pandas'), (numpy, 'numpy')])
def test_the_suite_runs_on_the_pinned_version(module, name):
    assert module.__version__ == pin(name), (
        f'{name} {module.__version__} is installed; requirements.txt pins {pin(name)}. Every published '
        'figure was made on the pin, and docs/pandas-2-plan.md is how it moves.')


@pytest.mark.parametrize('home_prob, side, pct, even', [
    (0.53, 'HOME', 53, False),
    (0.47, 'AWAY', 53, False),
    (0.56, 'HOME', 56, False),
    (0.51, 'HOME', 51, True),
    (0.49, 'AWAY', 51, True),
    (0.50, 'HOME', 50, True),
])
def test_the_even_band_picks_nobody_only_within_two_points(home_prob, side, pct, even):
    got = home._side(home_prob, 'HOME', 'AWAY')
    assert (got['p'], got['c'], got['e']) == (side, pct, even)


def test_the_band_is_two_points_as_on_every_board():
    assert home.EVEN_BAND == 2
    for rel in ('src/sports/nhl/pages/nhl.js', 'src/sports/nba/pages/nba.js'):
        assert 'const EVEN_BAND = 2,' in (ROOT / rel).read_text(encoding='utf-8'), rel
    app = APP_SCRIPT.read_text(encoding='utf-8')
    assert 'const CARD_EVEN_BAND = 2;' in app and 'const EVEN_BAND = 2;' in app
