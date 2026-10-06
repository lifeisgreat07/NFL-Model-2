"""The nightly dependency audit (Stage 45 item 3,
.github/workflows/nightly-dependency-audit.yml).

Held here: it audits requirements.txt with a pinned pip-audit installed in
that job only; it is report-only (the audit step never fails the run, and no
other workflow installs or runs it); a finding and an audit that could not
run each raise their own alert; it writes nothing to the repository and
holds only the permissions that needs.

Run with: pytest tests/test_dependency_audit.py -v
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / '.github' / 'workflows'
WF = WORKFLOWS / 'nightly-dependency-audit.yml'


def text():
    return WF.read_text(encoding='utf-8').replace('\r\n', '\n')


def test_it_audits_requirements_txt_with_a_pinned_pip_audit():
    t = text()
    assert re.search(r'^\s+run: pip install pip-audit==\d+\.\d+\.\d+$', t, re.M), 'pip-audit must be pinned'
    assert 'pip-audit -r requirements.txt ' in t


def test_it_runs_every_night_and_by_hand():
    t = text()
    assert re.search(r"^on:\n  schedule:\n    - cron: '\d+ \d+ \* \* \*'\n  workflow_dispatch: \{\}", t, re.M)


def test_the_audit_never_fails_the_run():
    t = text()
    step = t[t.index('- name: Audit requirements.txt'):t.index('- name: Raise an alert')]
    assert 'set +e' in step and 'code=$?' in step, 'a finding (exit 1) must not fail the step'
    assert 'echo "code=$code" >> "$GITHUB_OUTPUT"' in step


def test_a_finding_and_a_failed_audit_raise_different_alerts():
    t = text()
    alert = t[t.index('- name: Raise an alert'):]
    assert "if: ${{ steps.audit.outputs.code != '0' }}" in alert
    assert 'if [ "$CODE" = "1" ]; then' in alert
    assert 'title="Dependency audit found known vulnerabilities"' in alert
    assert 'title="Dependency audit could not run"' in alert
    assert 'python -m src.core.alerts --title "$title" --body-file audit-report.md' in alert


def test_it_writes_nothing_and_holds_only_what_it_uses():
    t = text()
    assert re.search(r'^permissions:\n  contents: read\n  issues: write\n\n', t, re.M)
    assert 'git push' not in t and 'git-auto-commit-action' not in t


def test_no_other_workflow_installs_or_runs_it():
    """Report-only means no pull request, deploy or data run waits on it."""
    others = [p.name for p in WORKFLOWS.glob('*.yml') if p != WF and 'pip-audit' in p.read_text(encoding='utf-8')]
    assert not others, others
    for req in ('requirements.txt', 'requirements-dev.txt'):
        assert 'pip-audit' not in (ROOT / req).read_text(encoding='utf-8'), req
