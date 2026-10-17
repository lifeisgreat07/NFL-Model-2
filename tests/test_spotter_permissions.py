"""Spotter reads pictures and cannot write (Stage 43 item 1; decision record 0007).

Spotter's workflow does not exist yet; this file holds the design it must be
built to, before it is built. Two halves:

* the decision record is written, linked, and says the things the later
  items rely on (what holds the model, what holds write, what is advisory);
* `violations()` is the rule every workflow named `spotter*.yml` is held to
  from the day it appears, shown here to pass a right workflow and to catch
  each wrong one. With no such workflow the scan finds none, and
  `test_the_scan_holds_every_spotter_workflow` is what makes the later one
  count.

Run with: pytest tests/test_spotter_permissions.py -v
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / '.github' / 'workflows'
ADR = ROOT / 'docs' / 'decisions' / '0007-spotter-reads-renders.md'
ACTION = 'anthropics/claude-code-action'


def text(path):
    return path.read_text(encoding='utf-8').replace('\r\n', '\n')


def jobs(wf):
    """{job name: its text}, for the top-level jobs of a workflow's text."""
    body = wf.split('\njobs:\n', 1)[1] if '\njobs:\n' in wf else ''
    parts = re.split(r'\n(?=  [A-Za-z][\w-]*:[ ]*\n)', '\n' + body)
    return {re.match(r'\n?  ([\w-]+):', p).group(1): p for p in parts if re.match(r'\n?  ([\w-]+):', p)}


def top_level(wf):
    """The workflow's text before its jobs."""
    return wf.split('\njobs:\n', 1)[0]


def violations(wf):
    """What is wrong with a Spotter workflow's text, one line each."""
    out = []
    head = top_level(wf)
    if re.search(r'^\s*pull_request_target\s*:', head, re.M):
        out.append('triggered by pull_request_target, which runs with secrets on a pull request')
    if re.search(r'^permissions:\n(?:  .*\n)*?  \w[\w-]*: write', head + '\n', re.M):
        out.append('grants write at the workflow level: write belongs to one job')
    writers = []
    for name, job in jobs(wf).items():
        uses_model = ACTION in job
        writes = bool(re.search(r'^      contents: write', job, re.M))
        if re.search(r'id-token:\s*write', job) or re.search(r'id-token:\s*write', head):
            out.append(f'{name}: can mint an OIDC token')
        if uses_model and writes:
            out.append(f'{name}: holds the model and contents: write')
        if uses_model:
            steps = re.findall(rf'uses: {re.escape(ACTION)}@\S+[^\n]*\n(.*?)(?=\n      - |\Z)', job, re.S)
            for s in steps:
                if 'github_token: ${{ secrets.GITHUB_TOKEN }}' not in s:
                    out.append(f'{name}: the model step is not handed the workflow token')
        if writes:
            writers.append(name)
            if re.search(r'run:.*\b(python|pip|npm|npx|node|make|pytest)\b', job):
                out.append(f'{name}: holds contents: write and runs repository code')
            if 'actions/checkout' in job and re.search(r'ref:\s*\$\{\{\s*github\.event\.pull_request', job):
                out.append(f'{name}: holds contents: write and checks out the pull request')
    if len(writers) > 1:
        out.append(f'more than one job holds contents: write: {sorted(writers)}')
    return out


GOOD = '''name: Spotter
on:
  pull_request:
    paths: ['src/**']
permissions:
  contents: read
jobs:
  render:
    runs-on: ubuntu-24.04
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@abc # v4
      - run: python -m src.sports.nfl.generate_dashboard
  publish:
    needs: [render]
    runs-on: ubuntu-24.04
    permissions:
      contents: write
    steps:
      - uses: actions/download-artifact@abc # v4
      - run: git push origin HEAD:spotter-renders
  read:
    needs: [publish]
    runs-on: ubuntu-24.04
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: anthropics/claude-code-action@abc # v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
'''


def bad(old, new):
    assert old in GOOD, old
    return GOOD.replace(old, new)


def test_the_decision_record_is_written_and_linked():
    assert ADR.exists(), 'decision record 0007 is missing'
    index = text(ROOT / 'docs' / 'decisions' / 'README.md')
    assert '[0007](0007-spotter-reads-renders.md)' in index


@pytest.mark.parametrize('phrase', [
    'cannot push',
    '`spotter-renders`',
    'orphan branch',
    '390x844 and 1440x900',

    'it is the only job with `contents: write`',
    'runs none of the pull request\'s code',
    'cannot mint an OIDC token',
    'never carries a verdict word',
    'decision record 0004',
], ids=['cannot-push', 'branch-name', 'orphan', 'viewports', 'one-writer', 'no-repo-code', 'no-oidc', 'advisory', 'booth-stays'])
def test_the_decision_record_says_what_the_later_items_rely_on(phrase):
    assert phrase in ' '.join(text(ADR).split()), phrase


def test_a_right_workflow_has_no_violation():
    assert violations(GOOD) == []


@pytest.mark.parametrize('wf, needle', [
    (bad('on:\n  pull_request:', 'on:\n  pull_request_target:'), 'pull_request_target'),
    (bad('permissions:\n  contents: read\njobs:', 'permissions:\n  contents: write\njobs:'), 'workflow level'),
    (bad('  read:\n    needs: [publish]\n    runs-on: ubuntu-24.04\n    permissions:\n      contents: read\n',
         '  read:\n    needs: [publish]\n    runs-on: ubuntu-24.04\n    permissions:\n      contents: write\n'),
     'holds the model and contents: write'),
    (bad('      pull-requests: write\n', '      pull-requests: write\n      id-token: write\n'), 'OIDC'),
    (bad('          github_token: ${{ secrets.GITHUB_TOKEN }}\n', ''), 'not handed the workflow token'),
    (bad('      - run: git push origin HEAD:spotter-renders\n',
         '      - run: python -m src.sports.nfl.generate_dashboard && git push origin HEAD:spotter-renders\n'),
     'runs repository code'),
    (bad('  render:\n    runs-on: ubuntu-24.04\n    permissions:\n      contents: read\n',
         '  render:\n    runs-on: ubuntu-24.04\n    permissions:\n      contents: write\n'),
     'more than one job'),
], ids=['target-trigger', 'workflow-write', 'model-and-write', 'oidc', 'no-token', 'writer-runs-code', 'two-writers'])
def test_each_wrong_workflow_is_caught(wf, needle):
    found = violations(wf)
    assert any(needle in v for v in found), found


def test_the_scan_holds_every_spotter_workflow():
    """Empty today; from the day a Spotter workflow lands it is held to the rule."""
    found = {p.name: violations(text(p)) for p in sorted(WORKFLOWS.glob('spotter*.yml'))}
    assert all(not v for v in found.values()), found
