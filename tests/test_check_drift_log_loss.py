"""
Stage 33 R4: the drift check flags on log loss, as registered.

experiments/stage33/registry.json registered the rule before any 2026 log
loss was computed for it: over every graded live Model A game, flag when the
lower end of a one-sided 95% bootstrap interval of the mean per-game log loss
is above the baseline (the 2022-2025 backtest with the schedule's listed
starter), not before 30 games, with accuracy printed and demoted to
information. These tests hold the committed baseline to the registry and to
the file its number came from, and the rule to its own words.
"""
import json
import math
from pathlib import Path

import numpy as np
import pytest

from src.pipeline import check_drift as cd

ROOT = Path(__file__).parent.parent


def r4():
    reg = json.loads((ROOT / 'experiments' / 'stage33' / 'registry.json').read_text(encoding='utf-8'))
    return reg, next(h for h in reg['hypotheses'] if h['id'] == 'R4')


def rows(probs, outcomes):
    return [{'model_a_home_win_prob': p, 'actual_home_win': y,
             'model_a_correct': None if y is None else int((p >= 0.5) == bool(y)),
             'model_b_correct': None if y is None else 1}
            for p, y in zip(probs, outcomes)]


# --- the committed baseline ----------------------------------------------------

def test_the_baseline_file_is_the_registered_one():
    reg, h = r4()
    spec = cd.log_loss_baseline()
    assert spec['model'] == 'model_a' and spec['metric'] == 'log_loss'
    assert spec['baseline']['name'] == h['baseline']['chosen'] == 'schedule_starter'
    assert spec['baseline']['value'] == h['baseline']['value']
    assert spec['printed_beside']['value'] == h['baseline']['printed_beside']['value']
    rule = spec['rule']
    assert rule['min_games'] == 30 and 'Not before 30 graded games' in h['rule']
    assert rule['one_sided_level'] == 0.95 and 'one-sided 95%' in h['rule']
    assert (rule['n_resamples'], rule['seed']) == (reg['protocol']['n_resamples'], reg['protocol']['seed'])


def test_the_baseline_is_the_figure_in_its_source_file():
    src = json.loads((ROOT / 'experiments' / 'stage5' / 'residuals.json').read_text(encoding='utf-8'))
    every = src['slices']['all games']
    spec = cd.log_loss_baseline()
    assert spec['baseline']['value'] == every['log_loss_sched']
    assert spec['printed_beside']['value'] == every['log_loss_lagged']


# --- the per-game losses ---------------------------------------------------------

def test_per_game_log_loss_by_hand_and_a_tie_decides_nothing():
    got = cd.per_game_log_loss(rows([0.75, 0.75, 0.6, 0.6], [1, 0, None, 1]))
    assert got == pytest.approx([-math.log(0.75), -math.log(0.25), -math.log(0.6)])
    assert cd.per_game_log_loss([{'actual_home_win': 1}]) == [], 'a game with no probability is not scored'


def test_the_lower_bound_is_the_rule_s_own_bootstrap():
    rule = cd.log_loss_baseline()['rule']
    losses = list(np.random.default_rng(1).uniform(0.2, 1.2, size=60))
    lower = cd.log_loss_lower_bound(losses, rule)
    arr = np.asarray(losses)
    idx = np.random.default_rng(rule['seed']).integers(0, 60, size=(rule['n_resamples'], 60))
    assert lower == float(np.percentile(arr[idx].mean(axis=1), 5))
    assert lower < arr.mean(), 'the lower end of a one-sided interval sits below the mean'
    assert lower == cd.log_loss_lower_bound(losses, rule), 'a rerun must be identical'


# --- the rule ----------------------------------------------------------------------

def test_a_live_log_loss_clearly_above_the_baseline_flags(capsys):
    """40 games, every winner given 0.51: log loss 0.673 on every game, so
    the whole interval sits above 0.6518 although every pick was right."""
    assert cd.check_log_loss(rows([0.51] * 40, [1] * 40), cd.log_loss_baseline()) is True
    assert 'DRIFT WARNING: live log loss' in capsys.readouterr().out


def test_a_live_log_loss_below_the_baseline_does_not():
    assert cd.check_log_loss(rows([0.8] * 40, [1] * 40), cd.log_loss_baseline()) is False


def test_below_thirty_games_nothing_flags_however_bad(capsys):
    assert cd.check_log_loss(rows([0.1] * 29, [1] * 29), cd.log_loss_baseline()) is False
    assert 'too early to test statistically' in capsys.readouterr().out


def test_a_lower_bound_exactly_on_the_baseline_does_not_flag():
    """The registry says "above": on the line is not above."""
    records = rows([0.51] * 40, [1] * 40)
    spec = json.loads(json.dumps(cd.log_loss_baseline()))
    spec['baseline']['value'] = cd.log_loss_lower_bound(cd.per_game_log_loss(records), spec['rule'])
    assert cd.check_log_loss(records, spec) is False


def _live(tmp_path, monkeypatch, records):
    monkeypatch.setattr(cd, 'RESULTS_DIR', tmp_path)
    (tmp_path / '2026_week1_graded.json').write_text(json.dumps(records), encoding='utf-8')


def test_the_flag_follows_log_loss_even_when_every_pick_was_right(tmp_path, monkeypatch, capsys):
    _live(tmp_path, monkeypatch, rows([0.51] * 40, [1] * 40))
    assert cd.main() == 1
    out = capsys.readouterr().out
    assert 'Observed accuracy: 40/40' in out and 'DRIFT CHECK: WARNING FLAGGED' in out


def test_accuracy_below_its_baseline_no_longer_flags(tmp_path, monkeypatch, capsys):
    """Accuracy is printed, demoted to information (R4): 36 of 40 against a
    baseline of 99% is a significant accuracy gap, and log loss is fine."""
    _live(tmp_path, monkeypatch, rows([0.9] * 40, [1] * 36 + [0] * 4))
    cal = tmp_path / 'calibration.json'
    cal.write_text(json.dumps({'models': {m: {'metrics': {'accuracy': 0.99, 'n': 1087}}
                                          for m in ('model_a', 'model_b')}}), encoding='utf-8')
    monkeypatch.setattr(cd, 'CALIBRATION', cal)
    assert cd.main() == 0
    out = capsys.readouterr().out
    assert 'Information only' in out and 'DRIFT CHECK: OK' in out


def test_a_missing_log_loss_baseline_is_reported_and_does_not_fail_the_run(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cd, 'DRIFT_BASELINE', tmp_path / 'absent.json')
    monkeypatch.setattr(cd, 'RESULTS_DIR', tmp_path)
    assert cd.main() == 0
    out = capsys.readouterr().out
    assert 'DRIFT CHECK: NOT RUN (no backtest baseline)' in out and 'DRIFT CHECK: OK' not in out
