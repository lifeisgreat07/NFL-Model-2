"""The sample week the browser checks build the NHL's page from
(`tests/browser/build_nhl.py`): it must carry every kind of card, or a rule
that only a rarer card breaks is never checked.

Run with: pytest tests/test_nhl_browser_sample.py -v
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js'


def _builder():
    spec = importlib.util.spec_from_file_location('build_nhl', ROOT / 'tests' / 'browser' / 'build_nhl.py')
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def built(tmp_path_factory: pytest.TempPathFactory) -> dict:
    out = tmp_path_factory.mktemp('nhl') / 'nhl.html'
    builder = _builder()
    real_paths = builder.site.PATHS
    try:
        assert builder.main(['--out', str(out)]) == 0
    finally:
        builder.site.PATHS = real_paths
    html = out.read_text(encoding='utf-8')
    block = re.search(r'<script id="nhl-data" type="application/json">(.*?)</script>', html, re.S)
    assert block is not None
    return json.loads(block.group(1))


def test_the_sample_has_final_postponed_and_unsaved_games_and_every_way_a_final_ends(built: dict) -> None:
    games = built['games']
    assert {g['status'] for g in games} >= {'final', 'postponed', 'scheduled'}
    assert {g['lp'] for g in games if g['status'] == 'final'} == {'REG', 'OT', 'SO'}
    assert any(g['id'] not in built['picks'] for g in games if g['status'] == 'scheduled')


def test_the_sample_has_picks_by_each_model_graded_both_ways_and_one_too_close(built: dict) -> None:
    picks = built['picks'].values()
    assert {p['by'] for p in picks} == {'model_a', 'model_b'}
    assert {p['result'] for p in picks} >= {'correct', 'wrong', 'pending'}
    assert any('market' in p for p in picks) and any('market' not in p for p in picks)
    assert any(abs((p['b'] if p['b'] is not None else p['a']) - 0.5) < 0.02 for p in picks)


def test_the_sample_has_every_goalie_status(built: dict) -> None:
    seen = {(g['status'], g['basis']) for p in built['picks'].values() for g in p['goalies'].values()}
    assert {s for s, _ in seen} >= {'Confirmed', 'Likely', None}
    assert any(b == 'last_start' for _, b in seen)


def test_the_sample_fills_every_page(built: dict) -> None:
    assert len(built['standings']['teams']) == 32 and len(built['ratings']['teams']) == 32
    assert built['backtest'] and built['drift_rule'] and built['changes']


def test_the_checker_can_open_each_page_as_it_opens_the_nfls() -> None:
    """tests/browser/check_page.py opens a page with setActivePage(<section id
    without its page- prefix>); without it the check stops at the first page."""
    assert 'window.setActivePage = ' in JS.read_text(encoding='utf-8')
