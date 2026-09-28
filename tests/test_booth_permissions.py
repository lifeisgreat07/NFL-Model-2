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
    return re.findall(rf'uses: {re.escape(ACTION)}@\S+\n(.*?)(?=\n      - |\Z)', t, re.S)


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


def test_the_audit_workflow_grants_contents_read_only():
    t = text(WORKFLOWS / 'booth-pr-audit.yml')
    block = re.search(r'\npermissions:\n((?:  .*\n)+)', t)
    assert block, 'no top-level permissions block'
    assert 'contents: read' in block.group(1)
    assert 'contents: write' not in t
