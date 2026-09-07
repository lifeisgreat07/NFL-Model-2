"""
Every workflow that regenerates the dashboard must prune build churn first.

src/prune_build_churn.py exists because seven of the first 26 runs of the
dashboard workflow committed nothing but the moment they ran, and those no-op
commits collide with any open branch that regenerated the same artifacts --
which is how PR #13 arrived with a merge conflict whose entire content was two
timestamps disagreeing.

The script was wired into generate-dashboard.yml on 2026-09-04 and not into
weekly-update.yml, which regenerated the dashboard and committed
`index.html dist/**` with no prune step. CLAUDE.md had described the script,
from its creation on 2026-09-05, as simply preventing the problem -- and that
sentence is what stopped anyone checking which workflows actually ran it.
Found 2026-09-07 while investigating an unrelated auto-commit; both workflows
run it now.

The gap only bit when a run produced no real data change -- the offseason
state -- which is exactly when nobody is watching. Hence a test rather than a
note: prose names a protection without naming its coverage, so this file
enumerates the workflows instead of asserting the guard is present.

Parsed by line position rather than with PyYAML, deliberately: yaml is not
installed on the machine this suite runs on, adding a pin for one test is a
poor trade, and the assertion here is about which steps are PRESENT and in what
ORDER -- which line numbers capture exactly.

Run with: pytest tests/test_workflow_churn_guard.py -v
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
WORKFLOWS = REPO_ROOT / '.github' / 'workflows'

GENERATES = 'generate_dashboard.py'
PRUNES = 'prune_build_churn.py'
# The artifacts prune_build_churn.py protects. A workflow committing either of
# these after a regeneration is the risk.
GUARDED_PATTERNS = ('index.html', 'dist/')


def _workflow_files():
    if not WORKFLOWS.is_dir():
        pytest.skip(".github/workflows not present in this checkout")
    return sorted(WORKFLOWS.glob('*.yml'))


def _line_of(lines, needle):
    for i, line in enumerate(lines):
        if needle in line:
            return i
    return None


def _regenerating_workflows():
    """Workflows that both regenerate the dashboard and commit its artifacts."""
    out = []
    for path in _workflow_files():
        lines = path.read_text(encoding='utf-8').splitlines()
        gen = _line_of(lines, GENERATES)
        if gen is None:
            continue
        commit = _line_of(lines, 'file_pattern')
        if commit is None:
            continue
        pattern_line = lines[commit]
        if not any(p in pattern_line for p in GUARDED_PATTERNS):
            continue
        out.append((path.name, lines, gen, commit))
    return out


def test_there_is_something_to_check():
    """If this finds nothing, every assertion below passes vacuously."""
    found = _regenerating_workflows()
    assert found, (
        "no workflow was detected as regenerating the dashboard AND committing "
        "index.html or dist/ -- either the workflows changed shape or this "
        "test has stopped matching them, and it is now guarding nothing")


@pytest.mark.parametrize('name', [w[0] for w in _regenerating_workflows()])
def test_a_regenerating_workflow_prunes_before_it_commits(name):
    """The real gap. weekly-update.yml regenerates and commits without ever
    running the churn guard."""
    _, lines, gen, commit = next(w for w in _regenerating_workflows() if w[0] == name)
    prune = _line_of(lines, PRUNES)

    assert prune is not None, (
        f"{name} runs {GENERATES} and commits {lines[commit].strip()} but "
        f"never runs {PRUNES}. Every regeneration it makes will commit "
        f"index.html and the picks PDF even when only their build stamps "
        f"changed -- the exact no-op churn that guard exists to stop, and "
        f"which collides with any open branch that regenerated the same files.")

    assert gen < prune < commit, (
        f"{name} runs {PRUNES} at line {prune + 1}, but it must come AFTER "
        f"{GENERATES} (line {gen + 1}) and BEFORE the commit step (line "
        f"{commit + 1}). Pruning before the regeneration, or after the commit, "
        f"restores nothing the commit step will see.")


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
