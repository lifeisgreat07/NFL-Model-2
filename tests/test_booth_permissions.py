"""Booth runs on a token that cannot write (Stage 23 item 5).

The 2026-09-28 audit, confirmed by Mark from the app's settings the same
day: booth-pr-audit.yml granted `id-token: write` and gave the Claude Code
action no `github_token`, so the action exchanged OIDC for the Claude GitHub
App's installation token -- read AND write on code, workflows and pull
requests -- and Booth ran with it (its reports were posted by claude[bot]).
The workflow's `contents: read` limited only GITHUB_TOKEN, which Booth was
not using. README said Booth "has read-only access and cannot merge".

Now each workflow that runs the action hands it GITHUB_TOKEN and cannot mint
an OIDC token, so the workflow's own permissions are the whole of what Booth
holds. Enumerated from every workflow that uses the action, not a list of
two, so a third is held too.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / '.github' / 'workflows'
ACTION = 'anthropics/claude-code-action'


def text(path):
    return path.read_text(encoding='utf-8').replace('\r\n', '\n')


def model_workflows():
    return sorted(p for p in WORKFLOWS.glob('*.yml') if ACTION in text(p))


def action_steps(t):
    """Each `uses: anthropics/claude-code-action` step, up to the next step."""
    # `@\S+[^\n]*`: the ref, then the version comment a pinned SHA carries.
    return re.findall(rf'uses: {re.escape(ACTION)}@\S+[^\n]*\n(.*?)(?=\n      - |\Z)', t, re.S)


def test_the_scan_finds_both_booth_workflows():
    names = {p.name for p in model_workflows()}
    assert {'booth-pr-audit.yml', 'booth-regression.yml'} <= names, names


def test_no_workflow_that_runs_the_model_can_mint_an_oidc_token():
    """With id-token: write and no github_token, the action fetches the app
    token, which can write to the repository. Comment lines are skipped: the
    audit workflow's header explains the old grant by name."""
    def grants(p):
        return [l for l in text(p).splitlines()
                if not l.lstrip().startswith('#') and re.search(r'id-token:\s*write', l)]
    bad = [p.name for p in model_workflows() if grants(p)]
    assert not bad, f'{bad} grant id-token: write alongside the Claude Code action'


def test_every_model_step_is_handed_the_workflow_token():
    for p in model_workflows():
        steps = action_steps(text(p))
        assert steps, f'{p.name}: the action step is not findable -- re-anchor this guard'
        for s in steps:
            assert 'github_token: ${{ secrets.GITHUB_TOKEN }}' in s, (
                f'{p.name}: a Claude Code action step has no github_token, so the '
                'action falls back to the Claude app token')


def jobs(t):
    """{job name: its text} for a workflow, from `jobs:` on."""
    body = t.split('\njobs:\n', 1)[1]
    parts = re.split(r'^  ([\w-]+):\n', body, flags=re.M)
    return dict(zip(parts[1::2], parts[2::2]))


def code(t):
    return '\n'.join(l for l in t.splitlines() if not l.lstrip().startswith('#'))


def test_the_model_runs_in_a_job_that_cannot_write():
    """Stage 82 item 4 (the 2026-11-02 review). Booth ran with
    `pull-requests: write` in an unrestricted Bash tool, so the pull request it
    audits could ask it to edit its own description or post a second comment.
    Now the workflow grants read only; the one write grant is the post job's,
    and that job runs no model and checks out the base, not the head."""
    t = text(WORKFLOWS / 'booth-pr-audit.yml')
    top = re.search(r'\npermissions:\n((?:  .*\n)+)', t).group(1)
    assert 'write' not in top, f'the workflow-wide grant can write: {top!r}'
    found = jobs(t)
    assert set(found) == {'audit', 'post'}, sorted(found)
    audit, post = code(found['audit']), code(found['post'])
    assert ACTION in audit and 'permissions:' not in audit, 'the audit job grants itself more than the workflow does'
    assert ACTION not in post, 'the job that can write runs the model'
    grant = re.search(r'\n    permissions:\n((?:      .*\n)+)', found['post']).group(1)
    assert grant.split() == ['contents:', 'read', 'pull-requests:', 'write'], grant
    assert 'needs: audit' in post
    assert "ref: ${{ github.event.pull_request.base.sha || 'main' }}" in post, 'the post job checks out the head'
    assert 'persist-credentials: false' in post


def test_the_job_reader_is_not_blind():
    """A splitter that found one job would pass the test above for the wrong reason."""
    sample = 'on: x\njobs:\n  a:\n    steps: []\n  b-c:\n    permissions:\n      x: read\n'
    assert list(jobs(sample)) == ['a', 'b-c']


def test_the_audit_workflow_grants_contents_read_only():
    t = text(WORKFLOWS / 'booth-pr-audit.yml')
    block = re.search(r'\npermissions:\n((?:  .*\n)+)', t)
    assert block, 'no top-level permissions block'
    assert 'contents: read' in block.group(1)
    assert 'contents: write' not in t
