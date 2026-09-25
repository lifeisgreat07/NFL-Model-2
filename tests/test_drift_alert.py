"""
src/drift_alert.py and its step in the Weekly update workflow.

The drift check itself is replaced by a stub returning a chosen exit code,
and the alert by a recorder, so nothing here reads results/ or reaches
GitHub.

Run with: pytest tests/test_drift_alert.py -v
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / 'src'))

import drift_alert  # noqa: E402

WEEKLY = REPO / '.github' / 'workflows' / 'weekly-update.yml'


def stub(code, text='Model A:\n  z-score: -2.40\n'):
    def check():
        print(text, end='')
        return code
    return check


def recorder():
    raised = []
    return raised, lambda title, body: raised.append((title, body)) or ('opened', 12)


def test_a_flag_opens_the_drift_issue_with_the_output_and_the_caution():
    raised, alert = recorder()
    assert drift_alert.main([], check=stub(1), raise_alert=alert) == 0
    [(title, body)] = raised
    assert title == 'Model drift detected'
    assert 'z-score: -2.40' in body
    assert drift_alert.CAUTION in body


def test_no_flag_raises_nothing():
    raised, alert = recorder()
    assert drift_alert.main([], check=stub(0), raise_alert=alert) == 0
    assert raised == []


def test_a_flag_never_fails_the_weekly_run():
    """Stopping the run would cost the week its picks and answer nothing."""
    _, alert = recorder()
    assert drift_alert.main([], check=stub(1), raise_alert=alert) == 0


def test_the_report_file_carries_the_output(tmp_path):
    out = tmp_path / 'drift.txt'
    drift_alert.main(['--report', str(out)], check=stub(0, 'DRIFT CHECK: OK\n'),
                     raise_alert=recorder()[1])
    assert out.read_text(encoding='utf-8') == 'DRIFT CHECK: OK\n'


def test_the_real_check_runs_through_it(capsys):
    """Against the committed results: whatever it concludes, it must run to
    an exit code this wrapper understands, and print its verdict line."""
    raised, alert = recorder()
    assert drift_alert.main([], raise_alert=alert) == 0
    assert 'DRIFT CHECK:' in capsys.readouterr().out


# --- the workflow step ---------------------------------------------------------

def _text():
    return WEEKLY.read_text(encoding='utf-8')


def test_the_weekly_run_checks_drift_after_grading_and_before_committing():
    text = _text()
    grade = text.index('python src/grade_predictions.py')
    drift = text.index('run: python src/drift_alert.py')
    commit = text.index('- name: Commit and push changes')
    assert grade < drift < commit


def test_the_drift_step_survives_a_failed_lock_like_the_grading_does():
    """The lock step fails the job on purpose when a whole week kicked off
    unlocked; grading still runs after it, and drift must too."""
    text = _text()
    # Exactly this step: up to the next step, not up to the commit. A wider
    # slice lets a later step's `if:` satisfy this assertion, which is how
    # its mutation first survived once another step was added after it.
    start = text.index('- name: Check for model drift')
    step = text[start:text.index('\n      - name:', start)]
    assert re.search(r"if:\s*\$\{\{\s*!cancelled\(\)\s*\}\}", step)
    assert 'GH_TOKEN' in step


def test_the_workflow_may_open_issues():
    block = re.search(r'^permissions:\s*\n((?:[ \t]+.+\n)+)', _text(), re.M).group(1)
    granted = dict(re.findall(r'^\s+(\w+):\s*(\S+)', block, re.M))
    assert granted == {'contents': 'write', 'issues': 'write'}
