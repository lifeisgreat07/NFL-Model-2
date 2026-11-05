"""Stage 95 item 36: the forward test's deciding file is frozen once, when the
regular season's last game is final, and carries the registered labels.

Run with: pytest tests/test_forward_freeze.py -v
"""
import json
from pathlib import Path

import pandas as pd
import pytest

from src.core import forward_test as ft
from src.sports.nba import backtest as nba_backtest

ROOT = Path(__file__).resolve().parents[1]
COMPARISONS = {
    'model_a_minus_base_rate': {'games': 900, 'days': 160, 'diff': -0.02, 'low': -0.03, 'high': -0.01},
    'model_b_minus_model_a': {'games': 700, 'days': 150, 'diff': 0.01, 'low': 0.002, 'high': 0.02},
    'model_b_minus_market': {'games': 700, 'days': 150, 'diff': 0.0, 'low': -0.01, 'high': 0.01},
}


def season(*statuses, playoff='scheduled'):
    rows = [{'game_id': str(i), 'game_type': 'regular', 'status': s} for i, s in enumerate(statuses)]
    rows.append({'game_id': '99', 'game_type': 'playoff', 'status': playoff})
    return pd.DataFrame(rows)


def forward(tmp_path, comparisons=COMPARISONS):
    path = tmp_path / 'forward_2026.json'
    path.write_text(json.dumps({'sport': 'nhl', 'season': 2026, 'graded_picks': 900,
                                'comparisons': comparisons}), encoding='utf-8')
    return path


def test_nothing_is_frozen_while_a_regular_season_game_is_left(tmp_path):
    path = forward(tmp_path)
    assert ft.freeze(path, season('final', 'scheduled'), '2027-04-15') is None
    assert not (tmp_path / 'forward_2026_regular_season_final.json').exists()


def test_the_first_file_after_the_last_game_is_frozen_with_its_labels(tmp_path):
    path = forward(tmp_path)
    frozen = ft.freeze(path, season('final', 'cancelled', 'final'), '2027-04-16')
    assert frozen == tmp_path / 'forward_2026_regular_season_final.json'
    doc = json.loads(frozen.read_text(encoding='utf-8'))
    assert doc['decision'] == {'model_a_minus_base_rate': 'ACCEPT', 'model_b_minus_model_a': 'REJECT',
                               'model_b_minus_market': 'INCONCLUSIVE'}
    assert doc['frozen']['on'] == '2027-04-16' and doc['frozen']['from'] == 'forward_2026.json'
    assert doc['comparisons'] == COMPARISONS
    assert 'decision' not in json.loads(path.read_text(encoding='utf-8')), 'labels are written to the frozen file only'


def test_a_later_run_never_rewrites_the_deciding_file(tmp_path):
    path = forward(tmp_path)
    first = ft.freeze(path, season('final'), '2027-04-16').read_bytes()
    forward(tmp_path, {k: dict(v, low=-1.0, high=-0.5) for k, v in COMPARISONS.items()})   # playoffs added
    assert ft.freeze(path, season('final', playoff='final'), '2027-05-01') is None
    assert (tmp_path / 'forward_2026_regular_season_final.json').read_bytes() == first


def test_a_comparison_too_small_to_resample_is_inconclusive():
    assert ft.label({'games': 1, 'days': 1, 'note': 'too few games to resample'}) == 'INCONCLUSIVE'


@pytest.mark.parametrize('low, high', [(-0.03, -0.01), (0.002, 0.02), (-0.01, 0.01), (-0.01, 0.0), (0.0, 0.01)])
def test_the_label_is_the_backtests_rule(low, high):
    assert ft.label({'low': low, 'high': high}) == nba_backtest.label({'low': low, 'high': high})


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_each_daily_run_freezes_after_it_writes(sport):
    src = (ROOT / 'src' / 'sports' / sport / 'daily.py').read_text(encoding='utf-8')
    write_at = src.index("fwd = forward_test.write(PATHS.results / f'forward_{season}.json'")
    freeze_at = src.index("frozen = forward_test.freeze(PATHS.results / f'forward_{season}.json', sched, str(now.date()))")
    assert write_at < freeze_at
