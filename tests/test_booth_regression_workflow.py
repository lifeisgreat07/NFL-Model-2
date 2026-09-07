"""
The regression workflow must stay manual, and Booth must stay unable to write.

Two properties this file exists to protect, both invisible from reading the
workflow casually and both expensive to lose:

MANUAL ONLY. Booth authenticates with the subscription rather than a metered
key, so a run costs no money -- but it costs usage, and usage is the real
constraint. A `pull_request` or `schedule` trigger added later would spend an
audit per fixture per event, silently, and the first sign would be a usage
limit rather than a failure.

BOOTH CANNOT WRITE. The audit job runs with `contents: read` so the model
physically cannot commit, and a separate job with `contents: write` records the
baseline without running a model. Collapsing those into one job would hand
Booth the ability to commit its own verdict -- the failure the whole
Scout/Booth separation exists to prevent. booth-pr-audit.yml protects the same
property, with a comment saying so.

Parsed by line position rather than with PyYAML, matching
test_workflow_churn_guard.py: yaml is not installed on the machine this suite
runs on, and these assertions are about which text is present in which block.

Run with: pytest tests/test_booth_regression_workflow.py -v
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
WORKFLOW = REPO / '.github' / 'workflows' / 'booth-regression.yml'


def _text():
    if not WORKFLOW.is_file():
        pytest.skip('booth-regression.yml not present in this checkout')
    return WORKFLOW.read_text(encoding='utf-8')


def _job_block(name):
    """The lines of one job, by indentation rather than by parsing YAML."""
    lines = _text().splitlines()
    start = next(
        (i for i, l in enumerate(lines) if re.match(r'^  {}:\s*$'.format(name), l)),
        None,
    )
    if start is None:
        return None
    out = []
    for line in lines[start + 1:]:
        if line.strip() and not line.startswith('    '):
            break
        out.append(line)
    return '\n'.join(out)


def test_there_is_something_to_check():
    assert _job_block('audit'), 'no `audit:` job found; every check below is vacuous'
    assert _job_block('record'), 'no `record:` job found'


def test_it_is_dispatch_only():
    """An automatic trigger would spend an audit per event, silently."""
    text = _text()
    on_block = text.split('\non:', 1)[1].split('\njobs:', 1)[0]
    assert 'workflow_dispatch' in on_block
    for forbidden in ('pull_request', 'push:', 'schedule'):
        assert forbidden not in on_block, (
            'booth-regression.yml triggers on {!r}. Every fixture run costs '
            'subscription usage, so this workflow is manual by design; an '
            'automatic trigger would spend it per event and the first symptom '
            'would be a usage limit, not a failure.'.format(forbidden)
        )


def test_it_runs_one_fixture_at_a_time():
    """No 'all' switch -- the cost of a run is one audit, and it should stay
    legible as one audit."""
    on_block = _text().split('\non:', 1)[1].split('\njobs:', 1)[0]
    assert 'fixture:' in on_block, 'no `fixture` input; the job cannot be aimed'
    assert 'required: true' in on_block


def test_the_auditing_job_cannot_write_to_the_repository():
    """The property that keeps Booth from committing its own verdict."""
    audit = _job_block('audit')
    assert 'contents: read' in audit, (
        'the audit job does not declare `contents: read`. Booth runs in this '
        'job; without a read-only grant it could commit the very baseline it '
        'is producing, which is the failure the Scout/Booth separation exists '
        'to prevent.'
    )
    assert 'contents: write' not in audit


def test_the_recording_job_never_runs_a_model():
    """Write access and model execution must not meet in one job."""
    record = _job_block('record')
    assert 'contents: write' in record, (
        'the record job cannot commit the baseline without write access'
    )
    assert 'claude-code-action' not in record, (
        'the record job runs a model AND holds write access. Those must stay '
        'in separate jobs; together they let Booth commit its own verdict.'
    )


def test_only_the_audit_job_runs_the_model():
    text = _text()
    assert text.count('claude-code-action') == 1, (
        'the model action appears {} times; it belongs only in the read-only '
        'audit job'.format(text.count('claude-code-action'))
    )
    assert 'claude-code-action' in _job_block('audit')


def test_the_prompt_is_generated_not_restated():
    """One source of truth, the same choice booth-pr-audit.yml makes.

    A prompt copied into YAML drifts from src/booth_fixture_runner.py without
    anything failing, and the drift is invisible until a fixture starts
    behaving differently for no apparent reason.
    """
    text = _text()
    assert 'booth_fixture_runner.py prompt' in text, (
        'the workflow does not generate the prompt from the runner'
    )
    # A distinctive line from the runner's PROMPT constant. If it appears
    # here, someone has pasted the prompt into the workflow.
    assert 'This is a REGRESSION FIXTURE' not in text, (
        "the runner's prompt text has been copied into the workflow; generate "
        'it instead, or the two will drift'
    )


def test_a_missing_report_fails_the_run():
    """A skipped or silent audit must not read as a pass.

    This project has been bitten twice by a workflow reporting success while
    doing nothing.
    """
    audit = _job_block('audit')
    assert 'booth-report.md' in audit
    assert re.search(r'test -s booth-report\.md', audit), (
        'nothing checks that Booth actually produced a report; an empty run '
        'would look exactly like a clean one'
    )


def test_a_missed_fixture_is_still_recorded():
    """The most important result must reach the repository.

    `record` exits non-zero when Booth missed the seeded defect. If that
    aborted the job, the miss would never be committed and would stay
    invisible until someone spent another audit rediscovering it.
    """
    record = _job_block('record')
    assert 'continue-on-error: true' in record, (
        'a fixture Booth missed would abort before the baseline is committed, '
        'so the miss would never reach the repository'
    )
    assert 'git commit' in record
