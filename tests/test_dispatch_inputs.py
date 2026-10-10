"""No free-text dispatch input reaches a shell line (Stage 68 item 30).

`${{ inputs.x }}` is pasted into a run: block before bash reads it, so a
free-text input with `$(...)` in it executes. Mark declined routing
dispatch inputs through env: in September, because only he could dispatch;
the cron-job.org token (Actions read and write, decision 0005) can now
dispatch too, and on 2026-10-09 he reopened it. So: an input of type string
appears only on an env: assignment line; choice, boolean and number inputs
can only be what the workflow lists. Booth regression's fixture is a choice
whose options are the fixture folders.

Run with: pytest tests/test_dispatch_inputs.py -v
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github' / 'workflows'
ALL = sorted(WF.glob('*.yml'))
INPUT = re.compile(r'^      ([a-z_][a-z0-9_]*):\n(?:        .*\n)*?        type: (\w+)\n', re.M)
USE = re.compile(r'\$\{\{[^}]*\binputs\.([a-z_][a-z0-9_]*)')
ENV_LINE = re.compile(r'^\s*[A-Z_][A-Z0-9_]*:\s*\$\{\{[^}]*\}\}\s*$')


def text(p):
    return p.read_text(encoding='utf-8').replace('\r\n', '\n')


def inputs(t):
    block = re.search(r'^  workflow_dispatch:\n    inputs:\n((?:      .*\n|\n)+)', t, re.M)
    return dict(INPUT.findall(block.group(1))) if block else {}


def test_the_scan_reads_the_inputs_it_must():
    assert inputs(text(WF / 'booth-regression.yml'))['fixture'] == 'choice'
    assert inputs(text(WF / 'nfl-run-backtest.yml'))['notes'] == 'string'
    assert inputs(text(WF / 'booth-pr-audit.yml'))['pr_number'] in ('number', 'string')


@pytest.mark.parametrize('path', ALL, ids=lambda p: p.name)
def test_a_free_text_input_reaches_the_shell_only_through_env(path):
    t = text(path)
    free = {k for k, v in inputs(t).items() if v == 'string'}
    for line in t.split('\n'):
        for name in USE.findall(line):
            if name in free:
                assert ENV_LINE.match(line), f'{path.name}: free-text input {name} used outside env: {line.strip()}'


def test_the_fixture_choices_are_the_fixture_folders():
    t = text(WF / 'booth-regression.yml')
    opts = re.search(r"        type: choice\n        options:\n((?:          - .*\n)+)", t)
    assert opts, 'fixture is not a choice'
    listed = [ln.strip()[2:] for ln in opts.group(1).splitlines()]
    folders = sorted(p.name for p in (ROOT / 'tests' / 'booth_fixtures').iterdir()
                     if p.is_dir() and not p.name.startswith(('_', '.')))
    assert listed == folders
