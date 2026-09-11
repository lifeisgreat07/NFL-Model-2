"""No workflow may commit the dashboard build outputs.

This file replaces tests/test_workflow_churn_guard.py, and the swap is the
point. That test asserted every workflow which regenerated the dashboard also
ran src/prune_build_churn.py first, because seven of the first 26 runs of the
dashboard workflow committed nothing but the moment they ran, and those no-op
commits collided with any open branch that had regenerated the same artifacts.

Stage 8c phase 2 removed the condition instead of managing it. `index.html` and
`dist/` are untracked, so there is no churn to prune, and the pruner is gone.

The invariant that replaces it is stronger and simpler: **nothing in CI commits
those two paths.** Restoring either -- by adding them back to a `file_pattern`,
or by reviving a workflow that regenerates and auto-commits -- would reinstate
the conflict tax that cost five merge conflicts across three branches in a
single day, and would do it quietly, because the symptom appears on somebody
else's open branch days later rather than in the run that caused it.

Parsed by line position rather than with PyYAML, deliberately and for the same
reason as the file it replaces: yaml is not installed on the machine this suite
runs on, adding a pin for one test is a poor trade, and the assertion is about
which lines are present, which line matching captures exactly.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
WORKFLOWS = REPO_ROOT / '.github' / 'workflows'

# The two build outputs, as they appear in a git-auto-commit `file_pattern`.
FORBIDDEN_IN_COMMIT = ('index.html', 'dist/', 'dist/**')

# Deleted in Stage 8c phase 2. Named here so that reviving it fails loudly
# rather than sitting in a workflow as a step that can never do anything.
DELETED_PRUNER = 'prune_build_churn.py'


def _workflow_files():
    if not WORKFLOWS.is_dir():
        pytest.skip('.github/workflows not present in this checkout')
    return sorted(WORKFLOWS.glob('*.yml'))


def _commit_lines(path):
    """Every `file_pattern:` line in one workflow."""
    return [ln for ln in path.read_text(encoding='utf-8').splitlines()
            if 'file_pattern' in ln]


def test_there_is_something_to_check():
    """If no workflow commits anything, every assertion below passes vacuously.

    Kept verbatim in spirit from the file this replaces: that test existed
    because a guard which matches nothing reports success, and this repository
    has shipped one of those before.
    """
    committing = [p.name for p in _workflow_files() if _commit_lines(p)]
    assert committing, (
        'no workflow was found with a file_pattern, so this test is matching '
        'nothing and guarding nothing. Either the workflows changed shape or '
        'the auto-commit action was replaced.')


@pytest.mark.parametrize('path', _workflow_files(), ids=lambda p: p.name)
def test_no_workflow_commits_the_build_outputs(path):
    for line in _commit_lines(path):
        for forbidden in FORBIDDEN_IN_COMMIT:
            assert forbidden not in line, (
                f'{path.name} commits {forbidden!r}:\n    {line.strip()}\n'
                'index.html and dist/ are build outputs and are untracked '
                '(Stage 8c phase 2). Committing them restores the conflict '
                'tax: every branch touching src/dashboard_template.html then '
                'collides with whatever CI regenerated on main. The page is '
                'published by .github/workflows/deploy-pages.yml, which builds '
                'the site into an artifact and holds `contents: read` so it '
                'structurally cannot commit anything.')


@pytest.mark.parametrize('path', _workflow_files(), ids=lambda p: p.name)
def test_no_workflow_runs_the_deleted_churn_pruner(path):
    """src/prune_build_churn.py no longer exists; a step calling it would fail
    the run, and a comment naming it would describe a protection that is not
    there -- which is precisely how its predecessor's coverage gap survived."""
    text = path.read_text(encoding='utf-8')
    assert DELETED_PRUNER not in text, (
        f'{path.name} still names {DELETED_PRUNER}, which was deleted in '
        'Stage 8c phase 2 because untracking the artifacts removed the '
        'problem it solved.')


def test_the_pruner_is_really_gone():
    """Guards the deletion itself, so the tests above cannot quietly become
    assertions about a file that was restored."""
    assert not (REPO_ROOT / 'src' / DELETED_PRUNER).exists(), (
        f'src/{DELETED_PRUNER} is back. If build churn is a problem again, '
        'the cause is that something re-tracked index.html or dist/ -- fix '
        'that rather than reinstating the pruner.')


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
