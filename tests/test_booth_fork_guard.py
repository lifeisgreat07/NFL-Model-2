"""Booth's dispatch never runs a fork's code with this repository's tokens (Stage 68 item 7).

A pull_request run from a fork gets no secrets from GitHub. A
workflow_dispatch of Booth names the PR by number and checks out
refs/pull/N/head, which works for a fork too, and the steps after it
install that branch's requirements and run its tests with
CLAUDE_CODE_OAUTH_TOKEN and a pull-requests: write token in reach. The
dispatch now stops first unless GitHub says the PR's head is in this
repository.

Run with: pytest tests/test_booth_fork_guard.py -v
"""
import re
from pathlib import Path

WF = (Path(__file__).resolve().parents[1] / '.github' / 'workflows' / 'booth-pr-audit.yml')
TEXT = WF.read_text(encoding='utf-8').replace('\r\n', '\n')


def steps():
    body = TEXT[TEXT.index('    steps:\n'):]
    return re.split(r'\n(?=      - (?:name|uses):)', body)[1:]


def test_the_fork_guard_is_the_first_step_and_runs_on_a_dispatch():
    first = steps()[0]
    assert first.startswith('      - name: Refuse a pull request from a fork\n')
    assert "if: github.event_name == 'workflow_dispatch'" in first


def test_it_fails_unless_github_says_same_repository():
    first = steps()[0]
    assert '--json isCrossRepository --jq .isCrossRepository' in first
    assert 'if [ "$cross" != "false" ]; then' in first and 'exit 1' in first
    assert 'PR: ${{ inputs.pr_number }}' in first, 'the number reaches the shell through env:'


def test_nothing_of_the_pr_runs_before_it():
    names = [s.split('\n', 1)[0] for s in steps()]
    assert names.index('      - name: Refuse a pull request from a fork') < names.index('      - name: Check out the PR branch')


def test_the_dispatch_input_is_a_number():
    assert re.search(r"pr_number:\n\s+description: 'PR number to audit'\n\s+required: true\n\s+type: number\n", TEXT)
