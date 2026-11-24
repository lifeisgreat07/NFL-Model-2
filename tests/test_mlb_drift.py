"""MLB's drift check (Stage 101 item 3): five looks, each at 99% against its own baseline from a season's first n
games, resampling whole days, and not run at all until the confirmation gives the baselines.

Run with: pytest tests/test_mlb_drift.py -v
"""
import json
import math
from pathlib import Path

import pandas as pd
import pytest

from src.sports.mlb import drift

ROOT = Path(__file__).resolve().parents[1]
REG = json.loads((ROOT / 'experiments/mlb/stage101/registry.json').read_text(encoding='utf-8'))['drift']


def confirmation(per_season=1700, p_first=0.6, p_rest=0.5):
    """Two seasons. The first 100 games of each are forecast at p_first and all won; the rest at p_rest, half won."""
    rows = []
    for season in (2025, 2026):
        for i in range(per_season):
            day = f'{season}-04-{1 + i // 15:02d}' if i < 450 else f'{season}-0{5 + (i - 450) // 450}-{1 + i % 28:02d}'
            rows.append({'game_id': f'{season}{i:05d}', 'season': season, 'day': day, 'start_utc': f'{i:05d}',
                         'home_win': 1 if i < 100 else i % 2, 'model_a': p_first if i < 100 else p_rest,
                         'model_b': None})
    return pd.DataFrame(rows)


def test_each_look_is_held_to_a_seasons_first_n_games_pooled():
    b = drift.baselines_from(confirmation())
    assert b['100'] == pytest.approx(-math.log(0.6))
    assert b['200'] == pytest.approx((100 * -math.log(0.6) + 100 * -math.log(0.5)) / 200)
    assert set(b) == {'100', '200', '400', '800', '1600'}


def test_the_baselines_are_written_once(tmp_path):
    src = tmp_path / 'confirmation_games.csv'
    confirmation().to_csv(src, index=False)
    out = tmp_path / 'drift_baseline.json'
    spec = drift.write_baseline(src, out)
    assert spec['seasons'] == [2025, 2026] and spec['rule']['checkpoints'] == [100, 200, 400, 800, 1600]
    assert json.loads(out.read_text(encoding='utf-8'))['baseline_by_look'] == drift.baselines_from(confirmation())
    with pytest.raises(SystemExit, match='written once'):
        drift.write_baseline(src, out)


def test_with_no_baseline_the_check_does_not_run_and_says_why(tmp_path):
    report = drift.check([(0.6, 1, '2027-04-01')] * 200, tmp_path / 'none.json')
    assert report['running'] is False and 'confirmation' in report['why'] and report['flagged'] is False


def spec_file(tmp_path, base):
    path = tmp_path / 'drift_baseline.json'
    path.write_text(json.dumps({'baseline_by_look': {str(n): base for n in drift.CHECKPOINTS}}), encoding='utf-8')
    return path


def test_a_look_flags_when_its_lower_bound_is_above_its_baseline(tmp_path):
    # 200 picks forecast at 0.9 that all lost: log loss 2.30 a game, far above a 0.69 baseline.
    rows = [(0.9, 0, f'2027-04-{1 + i // 15:02d}') for i in range(200)]
    report = drift.check(rows, spec_file(tmp_path, 0.69))
    assert report['running'] and [look['games'] for look in report['looks']] == [100, 200]
    assert report['flagged'] and report['next_look'] == 400
    calm = drift.check(rows, spec_file(tmp_path, 2.5))
    assert not calm['flagged']


def test_only_the_registered_looks_are_taken():
    assert drift.CHECKPOINTS == (100, 200, 400, 800, 1600) and drift.LEVEL == 0.99
    assert '100, 200, 400, 800 and 1,600' in REG['looks'] and '99%' in REG['looks']
    assert 'whole game days' in REG['rule'] and drift.RULE['resample'] == 'whole game days'


def test_a_look_resamples_whole_days(monkeypatch):
    seen = {}

    def fake(losses, rule, level, days):
        seen.update(level=level, days=days, n=len(losses))
        return 0.0
    monkeypatch.setattr(drift, 'lower_bound', fake)
    drift.looks([0.5] * 120, [f'd{i // 10}' for i in range(120)], {'baseline_by_look': {'100': 1.0}})
    assert seen['n'] == 100 and seen['level'] == 0.99 and seen['days'] == [f'd{i // 10}' for i in range(100)]


def test_a_pick_without_a_result_or_probability_decides_nothing(tmp_path):
    rows = [(0.9, 0, 'd')] * 99 + [(None, 0, 'd'), (0.9, None, 'd')]
    assert drift.check(rows, spec_file(tmp_path, 0.69))['looks'] == []
