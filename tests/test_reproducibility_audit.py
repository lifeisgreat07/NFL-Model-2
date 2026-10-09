"""
src/sports/nfl/research/reproducibility_audit.py: the pass mark, checked on synthetic numbers,
and the committed record held to the published file.

The audit itself needs nflverse and six seasons of play-by-play, so it is
not run here. What is run: every comparison rule on inputs built to sit
just inside and just outside it, and a check that data/nfl/reproducibility_audit.json
still describes the data/nfl/calibration.json the page is built from.

Run with: pytest tests/test_reproducibility_audit.py -v
"""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent

from src.sports.nfl.research import reproducibility_audit as ra

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


def test_two_runs_that_differ_are_not_reproduced():
    runs = iter([({**PUB}, [1, 0], [0.6, 0.4]), ({**PUB}, [1, 0], [0.6, 0.41])])
    rows, det = ra.audit({'model_a': {'metrics': PUB}}, lambda _m: next(runs))
    assert det == {'model_a': False}
    assert ra.verdict(rows, det) == 'NOT REPRODUCED'


def test_identical_runs_that_match_are_reproduced():
    rows, det = ra.audit({'model_a': {'metrics': PUB}},
                         lambda _m: ({**PUB}, [1, 0], [0.6, 0.4]))
    assert det == {'model_a': True} and ra.verdict(rows, det) == 'REPRODUCED'
    assert {r['metric'] for r in rows} == {'n', 'accuracy', *ra.PROPER_SCORES}, (
        'the audit compares something other than the published file again')


# --- the committed record ----------------------------------------------------

RECORD = REPO / 'data' / 'nfl' / 'reproducibility_audit.json'
CALIBRATION = REPO / 'data' / 'nfl' / 'calibration.json'


def test_the_committed_record_says_reproduced():
    rec = json.loads(RECORD.read_text(encoding='utf-8'))
    assert rec['verdict'] == 'REPRODUCED'
    assert all(rec['determinism'].values())
    assert all(r['ok'] for r in rec['comparisons'])
    assert rec['provenance']['commit'], 'the record does not say which commit it ran'


def test_the_committed_record_is_about_the_published_file_as_it_is_now():
    """Regenerating data/nfl/calibration.json without re-running the audit would
    leave a record vouching for numbers that are no longer on the page."""
    rec = json.loads(RECORD.read_text(encoding='utf-8'))
    cal = json.loads(CALIBRATION.read_text(encoding='utf-8'))
    assert rec['published_generated_at'] == cal['generated_at']
    for row in rec['comparisons']:
        # Written by the audit before Stage 35, which also compared the
        # drift check's old stored baseline; the next run writes none.
        # The record stays as that run wrote it.
        if row['metric'] == 'config.BACKTEST_ACCURACY':
            continue
        assert row['published'] == cal['models'][row['model']]['metrics'][row['metric']], row
    assert {r['model'] for r in rec['comparisons']} == set(cal['models'])


# --- provenance: which CPU ran it --------------------------------------------

def test_the_cpu_is_read_by_name_from_cpuinfo(tmp_path):
    """GitHub's Linux runners report only "x86_64" through platform; the model
    name is in /proc/cpuinfo, and it is what tells two runners apart."""
    info = tmp_path / 'cpuinfo'
    info.write_text('processor\t: 0\nvendor_id\t: AuthenticAMD\n'
                    'model name\t: AMD EPYC 7763 64-Core Processor\nflags\t\t: fpu\n', encoding='utf-8')
    assert ra.cpu_model(info) == 'AMD EPYC 7763 64-Core Processor'


def test_without_cpuinfo_the_cpu_falls_back_to_platform(tmp_path, monkeypatch):
    monkeypatch.setattr(ra.platform, 'processor', lambda: 'Intel64 Family 6 Model 85')
    assert ra.cpu_model(tmp_path / 'absent') == 'Intel64 Family 6 Model 85'


def test_every_audit_record_says_which_cpu_ran_it():
    prov = ra._provenance()
    assert prov.get('cpu'), 'an audit record that cannot tie a flip to the hardware it ran on'
