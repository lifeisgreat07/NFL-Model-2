"""The test workflow runs where the tests can fail (Stage 24).

The 2026-09-28 audit, confirmed: `run-tests.yml` ran only on pull requests
touching src/** or tests/**. Documentation goes straight to main in this
project, and many tests read the documentation and the workflow files, so a
change that broke them reached main with nothing running them. The job also
installed an unpinned pytest beside requirements-dev.txt's pinned one, and
never installed node, so every test that runs template code in node skipped.

Read as text: PyYAML is not a dependency here, and each rule is one line.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'run-tests.yml'


def text():
    return WORKFLOW.read_text(encoding='utf-8').replace('\r\n', '\n')


def on_block():
    m = re.search(r'\non:\n(.*?)\n(?=\S)', text(), re.S)
    assert m, 'the on: block is not findable -- re-anchor this guard'
    return m.group(1)


def test_it_runs_on_every_pull_request_with_no_path_filter():
    on = on_block()
    assert re.search(r'^  pull_request:', on, re.M), 'no pull_request trigger'
    assert 'paths' not in on, (
        'a path filter is back: a documentation or workflow change would skip '
        'the tests that read it')


def test_it_runs_on_every_push_to_main():
    assert re.search(r'^  push:\n    branches: \[main\]', on_block(), re.M), (
        'no push trigger on main: documentation committed straight to main is '
        'never tested')


def test_it_installs_the_pinned_test_requirements():
    t = text()
    assert 'pip install -r requirements.txt -r requirements-dev.txt' in t
    assert not re.search(r'pip install pytest\b', t), (
        'an unpinned pytest is installed beside requirements-dev.txt')


def test_it_installs_node():
    t = text()
    assert 'uses: actions/setup-node@' in t, (
        'no node: the tests that run template code in node skip here')


def test_it_has_a_timeout():
    m = re.search(r'timeout-minutes:\s*(\d+)', text())
    assert m and int(m.group(1)) > 0, 'no timeout-minutes on the test job'
