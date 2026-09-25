"""
src/reproducibility_audit.py: the pass mark, checked on synthetic numbers,
and the committed record held to the published file.

The audit itself needs nflverse and six seasons of play-by-play, so it is
not run here. What is run: every comparison rule on inputs built to sit
just inside and just outside it, and a check that data/reproducibility_audit.json
still describes the data/calibration.json the page is built from.

Run with: pytest tests/test_reproducibility_audit.py -v
"""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / 'src'))

import reproducibility_audit as ra  # noqa: E402

N = 1087
PUB = {'n': N, 'accuracy': 0.6274, 'log_loss': 0.649812, 'brier': 0.228603, 'auc': 0.670119}


def rows_for(**changes):
    return {r['metric']: r['ok'] for r in ra.compare('model_a', PUB, {**PUB, **changes})}


def test_an_exact_reproduction_passes_every_row():
    assert all(rows_for().values())


@pytest.mark.parametrize('metric', ra.PROPER_SCORES)
def test_proper_scores_must_match_to_four_decimals(metric):
    assert rows_for(**{metric: PUB[metric] + 0.00004})[metric] is True
    assert rows_for(**{metric: PUB[metric] + 0.00006})[metric] is False


def test_accuracy_may_move_two_games_and_no_more():
    assert rows_for(accuracy=PUB['accuracy'] + 2 / N)['accuracy'] is True
    assert rows_for(accuracy=PUB['accuracy'] + 3 / N)['accuracy'] is False


def test_a_different_game_count_fails_every_row():
    """A different n is a different set of games; a metric that happens to
    agree over different games proves nothing."""
    rows = rows_for(n=N - 1)
    assert not any(rows.values())


def test_the_stored_baseline_allows_rounding_plus_two_games():
    ok = ra.compare_baseline('model_a', 0.628, 0.628 - 0.0005 - 2 / N, N)
    bad = ra.compare_baseline('model_a', 0.628, 0.628 - 0.0005 - 3 / N, N)
    assert ok['ok'] and not bad['ok']


def test_two_runs_that_differ_are_not_reproduced():
    runs = iter([({**PUB}, [1, 0], [0.6, 0.4]), ({**PUB}, [1, 0], [0.6, 0.41])])
    rows, det = ra.audit({'model_a': {'metrics': PUB}}, lambda _m: next(runs), {})
    assert det == {'model_a': False}
    assert ra.verdict(rows, det) == 'NOT REPRODUCED'


def test_identical_runs_that_match_are_reproduced():
    rows, det = ra.audit({'model_a': {'metrics': PUB}},
                         lambda _m: ({**PUB}, [1, 0], [0.6, 0.4]), {'model_a': 0.627})
    assert det == {'model_a': True} and ra.verdict(rows, det) == 'REPRODUCED'
    assert any(r['metric'] == 'config.BACKTEST_ACCURACY' for r in rows)


# --- the committed record ----------------------------------------------------

RECORD = REPO / 'data' / 'reproducibility_audit.json'
CALIBRATION = REPO / 'data' / 'calibration.json'


def test_the_committed_record_says_reproduced():
    rec = json.loads(RECORD.read_text(encoding='utf-8'))
    assert rec['verdict'] == 'REPRODUCED'
    assert all(rec['determinism'].values())
    assert all(r['ok'] for r in rec['comparisons'])
    assert rec['provenance']['commit'], 'the record does not say which commit it ran'


def test_the_committed_record_is_about_the_published_file_as_it_is_now():
    """Regenerating data/calibration.json without re-running the audit would
    leave a record vouching for numbers that are no longer on the page."""
    rec = json.loads(RECORD.read_text(encoding='utf-8'))
    cal = json.loads(CALIBRATION.read_text(encoding='utf-8'))
    assert rec['published_generated_at'] == cal['generated_at']
    for row in rec['comparisons']:
        if row['metric'] == 'config.BACKTEST_ACCURACY':
            continue
        assert row['published'] == cal['models'][row['model']]['metrics'][row['metric']], row
    assert {r['model'] for r in rec['comparisons']} == set(cal['models'])
