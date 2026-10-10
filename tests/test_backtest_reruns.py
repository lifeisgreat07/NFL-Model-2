"""The NHL's and NBA's backtests can be re-run where anyone can see (Stage 68 item 28, E27).

Each sport's workflow re-runs its registered backtest from the committed
data and fails when the results differ from the committed ones beyond float
noise; it never commits them, as the NFL's run backtest never does.

Run with: pytest tests/test_backtest_reruns.py -v
"""
import json
import re
from pathlib import Path

import pytest

from src.core.compare_results import compare_dirs, differences, main

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github' / 'workflows'
STAGE = {'nhl': 'stage56', 'nba': 'stage61'}


def text(sport):
    return (WF / f'{sport}-run-backtest.yml').read_text(encoding='utf-8').replace('\r\n', '\n')


def step(t, name):
    start = t.index(f'      - name: {name}')
    nxt = t.find('\n      - name:', start + 1)
    return t[start:nxt if nxt != -1 else None]


@pytest.mark.parametrize('sport', STAGE)
def test_it_runs_only_when_asked_and_cannot_write(sport):
    t = text(sport)
    on = t[t.index('\non:\n'):t.index('\npermissions:')]
    assert 'workflow_dispatch:' in on and not re.search(r'^  (push|pull_request|schedule|workflow_run)', on, re.M)
    assert re.search(r'^permissions:\n  contents: read\n\n', t, re.M)
    assert 'contents: write' not in t and 'git push' not in t and 'git commit' not in t


@pytest.mark.parametrize('sport', STAGE)
def test_it_reruns_the_registered_backtest_and_compares_with_what_was_committed(sport):
    t = text(sport)
    folder = f'experiments/{sport}/{STAGE[sport]}/results'
    keep, rerun, compare = (step(t, n) for n in ('Keep the committed results', 'Re-run the backtest',
                                                 'Compare with the committed results'))
    assert t.index('Keep the committed results') < t.index('Re-run the backtest') < t.index('Compare with')
    assert f'cp {folder}/*.json "$RUNNER_TEMP/committed/"' in keep
    assert f'python -m src.sports.{sport}.backtest 2>&1 | tee' in rerun
    assert f'python -m src.core.compare_results "$RUNNER_TEMP/committed" {folder}' in compare
    assert 'shell: bash' in compare, 'pipefail, so the comparison failing fails the step through tee'
    assert (ROOT / folder / 'confirmation.json').exists()


@pytest.mark.parametrize('sport', STAGE)
def test_the_notes_reach_the_shell_through_env(sport):
    s = step(text(sport), 'Re-run the backtest')
    assert 'NOTES: ${{ inputs.notes }}' in s
    assert s[s.index('run: |'):].count('${{') == 0


def test_float_noise_agrees_and_anything_else_does_not():
    a = {'chosen': {'H_days': 120}, 'log_loss': 0.6613274023739324, 'label': 'ACCEPT', 'games': 2800}
    assert differences(a, dict(a, log_loss=0.6613274023739323)) == []
    assert differences(a, dict(a, log_loss=0.6613284)) != []
    assert differences(a, dict(a, label='REJECT')) != []
    assert differences(a, dict(a, games=2801)) != []
    assert differences(a, dict(a, chosen={'H_days': 60})) != []
    assert differences([1, 2], [1, 2, 3]) != [] and differences({'a': 1}, {'b': 1}) != []
    assert differences(True, 1) != []


def test_a_folder_that_differs_fails(tmp_path, capsys):
    (tmp_path / 'c').mkdir()
    (tmp_path / 'r').mkdir()
    (tmp_path / 'c' / 'x.json').write_text(json.dumps({'diff': 0.0011763720549788186}), encoding='utf-8')
    (tmp_path / 'r' / 'x.json').write_text(json.dumps({'diff': 0.0011763720549788227}), encoding='utf-8')
    assert main([str(tmp_path / 'c'), str(tmp_path / 'r')]) == 0
    (tmp_path / 'r' / 'x.json').write_text(json.dumps({'diff': 0.0012}), encoding='utf-8')
    assert main([str(tmp_path / 'c'), str(tmp_path / 'r')]) == 1
    (tmp_path / 'r' / 'y.json').write_text('{}', encoding='utf-8')
    assert any('only in the re-run' in d for d in compare_dirs(tmp_path / 'c', tmp_path / 'r'))
