"""
src/booth_alert.py and .github/workflows/booth-alert.yml: a failed Booth
audit becomes an issue, and nothing else does.

Run with: pytest tests/test_booth_alert.py -v
"""
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / 'src'))

import booth_alert  # noqa: E402

WORKFLOW = REPO / '.github' / 'workflows' / 'booth-alert.yml'
AUDIT = REPO / '.github' / 'workflows' / 'booth-pr-audit.yml'


def event(conclusion, prs=({'number': 101},), sha='abcdef1234567890'):
    return {'workflow_run': {
        'conclusion': conclusion, 'pull_requests': list(prs),
        'head_sha': sha, 'head_branch': 'some-branch', 'event': 'pull_request',
        'run_attempt': 1, 'html_url': 'https://github.com/o/r/actions/runs/1'}}


@pytest.mark.parametrize('conclusion', ['failure', 'timed_out'])
def test_a_failed_audit_raises_an_alert_naming_the_pr(conclusion):
    title, body = booth_alert.alert_for(event(conclusion))
    assert title == 'Booth audit failed: PR #101'
    assert conclusion in body
    assert 'https://github.com/o/r/actions/runs/1' in body


@pytest.mark.parametrize('conclusion', ['success', 'cancelled', 'skipped', 'neutral', None])
def test_every_other_ending_is_quiet(conclusion):
    """A cancelled run is a newer push superseding an older audit, which is
    normal. Alerting on it would train everyone to ignore the issues."""
    assert booth_alert.alert_for(event(conclusion)) is None


def test_a_dispatched_run_is_named_by_its_commit():
    title, _ = booth_alert.alert_for(event('failure', prs=()))
    assert title == 'Booth audit failed: commit abcdef1'


def test_main_hands_the_alert_over_and_stays_quiet_on_success(tmp_path):
    raised = []
    path = tmp_path / 'event.json'
    path.write_text(json.dumps(event('failure')), encoding='utf-8')
    assert booth_alert.main([str(path)], raise_alert=lambda t, b: raised.append(t) or ('opened', 1)) == 0
    assert raised == ['Booth audit failed: PR #101']

    raised.clear()
    path.write_text(json.dumps(event('success')), encoding='utf-8')
    booth_alert.main([str(path)], raise_alert=lambda t, b: raised.append(t) or ('opened', 1))
    assert raised == []


# --- the workflow ------------------------------------------------------------

def _text(path):
    return path.read_text(encoding='utf-8')


def test_the_trigger_names_the_audit_workflow_exactly():
    """workflow_run matches on the other workflow's `name:`. A rename breaks
    the trigger with no run and no error, so the two are compared here."""
    audit_name = re.search(r'^name:\s*(.+?)\s*$', _text(AUDIT), re.M).group(1)
    listed = re.search(r'workflow_run:\s*\n\s*workflows:\s*\[(.*?)\]', _text(WORKFLOW), re.S)
    assert listed, 'booth-alert.yml has no workflow_run: workflows: [...] trigger'
    names = [n.strip().strip('"\'') for n in listed.group(1).split(',')]
    assert names == [audit_name]
    assert re.search(r'types:\s*\[completed\]', _text(WORKFLOW))


def test_the_job_runs_on_exactly_the_conclusions_the_script_alerts_on():
    """Two gates that must agree: the job's `if:` and ALERT_CONCLUSIONS.
    If the `if:` were narrower, a timed-out audit would never reach the
    script; if it were missing, every audit would start a job for nothing."""
    text = _text(WORKFLOW)
    gated = set(re.findall(r"workflow_run\.conclusion == '(\w+)'", text))
    assert gated == set(booth_alert.ALERT_CONCLUSIONS)


def test_it_asks_for_issue_permission_and_nothing_else():
    text = _text(WORKFLOW)
    block = re.search(r'^permissions:\s*\n((?:[ \t]+.+\n)+)', text, re.M)
    assert block, 'booth-alert.yml sets no top-level permissions'
    granted = dict(re.findall(r'(\S+):\s*(\S+)', block.group(1)))
    assert granted == {'issues': 'write'}


def test_it_runs_the_script_with_the_event_payload():
    text = _text(WORKFLOW)
    assert 'python src/booth_alert.py "$GITHUB_EVENT_PATH"' in text
    assert 'GH_TOKEN' in text
