"""Every workflow declares what its token may do, and holds nothing it does
not use (Stage 45 item 4, proposed 2026-10-04).

A workflow with no `permissions:` key runs with the repository's default
token, which an account setting can widen without anything in this
repository changing. So each one states its own. And a scope it holds but
never uses is reach an attacker inherits for free if a step is compromised,
so every scope beyond `contents: read` must name the thing in the workflow
that needs it. SECURITY.md points here.

The usage table is deliberately literal: a scope is justified by text that
appears in the workflow -- the action or command that spends it. A new
use of a scope that this table does not know fails until someone adds it,
with the reason, here.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / '.github' / 'workflows'

#: (scope, level) -> text in the workflow that shows the scope is spent.
USES = {
    ('contents', 'write'): ('stefanzweifel/git-auto-commit-action', 'git push', 'gh release'),
    ('issues', 'write'): ('src.pipeline.alerts', 'src.core.alerts', 'src.site.alert_failed', 'src.pipeline.drift_alert', 'booth_alert', 'gh issue'),
    ('issues', 'read'): ('/issues', 'gh issue'),
    ('pull-requests', 'write'): ('anthropics/claude-code-action', 'gh pr comment'),
    # /issues/comments is how collect-agent-log reads Booth's reports, which
    # are PULL REQUEST conversation comments served through the issues API.
    # Kept rather than tested away: whether issues: read alone still returns
    # comments on pull requests was not verified, and a log that silently
    # lost every Booth report would be worse than one read scope.
    ('pull-requests', 'read'): ('gh pr', '/pulls', '/issues/comments'),
    ('pages', 'write'): ('actions/deploy-pages',),
    ('id-token', 'write'): ('actions/deploy-pages',),
    ('actions', 'read'): ('src.pipeline.recent_runs',),
}
#: Needed by actions/checkout in every job, and grants nothing beyond reading
#: a public repository.
FREE = {('contents', 'read')}

PERMISSIONS_RE = re.compile(r'^([ \t]*)permissions:[ \t]*([^\s#][^\n]*)?$', re.M)
SCOPE_RE = re.compile(r'^([ \t]*)([a-z-]+):[ \t]*(read|write|none)[ \t]*(?:#.*)?$')


def text(path):
    return path.read_text(encoding='utf-8').replace('\r\n', '\n')


def held(t):
    """Every (scope, level) a workflow's permissions blocks grant, top level
    and per job. A one-line form (`permissions: write-all`) comes back as
    ('*', value)."""
    out = set()
    for m in PERMISSIONS_RE.finditer(t):
        if m.group(2):
            out.add(('*', m.group(2).strip()))
            continue
        indent = len(m.group(1))
        for line in t[m.end():].split('\n')[1:]:
            if not line.strip() or line.strip().startswith('#'):
                continue
            s = SCOPE_RE.match(line)
            if not s or len(s.group(1)) <= indent:
                break
            out.add((s.group(2), s.group(3)))
    return out


def declares_everywhere(t):
    """A top-level `permissions:`, or one in every job."""
    if re.search(r'^permissions:', t, re.M):
        return True
    jobs = re.findall(r'^  [A-Za-z0-9_-]+:\n((?:    .*\n|\n)*)', t.split('\njobs:\n', 1)[-1], re.M)
    return bool(jobs) and all(re.search(r'^    permissions:', j, re.M) for j in jobs)


ALL = sorted(WORKFLOWS.glob('*.yml'))


def test_the_scan_finds_the_workflows():
    assert len(ALL) >= 15, [p.name for p in ALL]


@pytest.mark.parametrize('path', ALL, ids=lambda p: p.name)
def test_every_workflow_declares_its_permissions(path):
    assert declares_everywhere(text(path)), (
        f'{path.name} has no permissions: block for some job, so that job runs with the '
        f"repository's default token, whatever the settings make it")


@pytest.mark.parametrize('path', ALL, ids=lambda p: p.name)
def test_no_workflow_takes_everything(path):
    wide = {v for s, v in held(text(path)) if s == '*'}
    assert not wide, f'{path.name} grants {wide}; name the scopes it needs instead'


@pytest.mark.parametrize('path', ALL, ids=lambda p: p.name)
def test_every_scope_held_is_used(path):
    t = text(path)
    unused = []
    for grant in sorted(held(t) - FREE):
        if grant[1] == 'none':
            continue
        needles = USES.get(grant)
        if not needles or not any(n in t for n in needles):
            unused.append(f'{grant[0]}: {grant[1]}')
    assert not unused, (
        f'{path.name} holds {unused} and nothing in it uses them by any route this '
        f"test knows (USES). Drop the scope, or add the step that spends it to USES "
        f'with the reason.')


def test_the_parser_reads_both_forms():
    """held() must see per-job blocks and the one-line form, or every test
    above passes on nothing."""
    t = ('on: push\npermissions:\n  contents: read\n  # why\n  issues: write\njobs:\n'
         '  a:\n    permissions:\n      pages: write\n    steps: []\n'
         '  b:\n    permissions: write-all\n')
    assert held(t) == {('contents', 'read'), ('issues', 'write'), ('pages', 'write'),
                       ('*', 'write-all')}


def test_an_unused_scope_is_caught():
    t = 'on: push\npermissions:\n  contents: read\n  issues: write\njobs:\n  a:\n    steps: []\n'
    grants = held(t) - FREE
    assert grants == {('issues', 'write')}
    assert not any(n in t for n in USES[('issues', 'write')])


def test_a_job_without_permissions_is_caught():
    t = ('on: push\njobs:\n  a:\n    permissions:\n      contents: read\n    steps: []\n'
         '  b:\n    steps: []\n')
    assert not declares_everywhere(t)


@pytest.mark.parametrize('path', ALL, ids=lambda p: p.name)
def test_no_workflow_runs_a_strangers_code_with_this_repositorys_token(path):
    """pull_request_target runs with the base repository's token while
    checking out whatever the pull request says; SECURITY.md promises none."""
    assert not re.search(r'^\s*pull_request_target\s*:', text(path), re.M), path.name


PR_TEXT_RE = re.compile(r'\$\{\{\s*github\.event\.(?:pull_request|issue|comment)\.(?:body|title)\s*\}\}')


@pytest.mark.parametrize('path', ALL, ids=lambda p: p.name)
def test_pull_request_text_reaches_a_shell_only_through_the_environment(path):
    """A description or title is text anyone can write, with backticks and
    $(...) in it. Interpolated into a run: block, it executes. Every use must
    be an env: assignment (`NAME: ${{ ... }}` on its own line)."""
    for line in text(path).split('\n'):
        if PR_TEXT_RE.search(line):
            assert re.match(r'^\s*[A-Z_][A-Z0-9_]*:\s*\$\{\{[^}]*\}\}\s*$', line), (
                f'{path.name}: pull request text used outside an env: assignment: {line.strip()}')


def test_security_md_points_here():
    sec = (ROOT / 'SECURITY.md').read_text(encoding='utf-8')
    assert 'tests/test_workflow_permissions.py' in sec
    assert '## How to report a vulnerability' in sec, 'SECURITY.md no longer says how to report one'
