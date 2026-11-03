"""
Stage 88 item 2: Dependabot proposes updates to the pinned actions and Python
packages; it never merges one, and pandas and numpy keep their 1.x majors.

Run with: pytest tests/test_dependabot.py -v
"""
import re
from pathlib import Path

TEXT = (Path(__file__).resolve().parents[1] / '.github' / 'dependabot.yml').read_text(encoding='utf-8')


def block(ecosystem):
    m = re.search(rf'- package-ecosystem: {ecosystem}\n((?:    .*\n|\n(?=    ))+)', TEXT)
    assert m, f'no {ecosystem} entry in .github/dependabot.yml'
    return m.group(1)


def test_actions_and_pip_are_both_watched():
    assert 'interval: weekly' in block('github-actions')
    assert 'interval: monthly' in block('pip')


def test_pandas_and_numpy_keep_their_majors():
    pip = block('pip')
    for name in ('pandas', 'numpy'):
        assert re.search(rf"- dependency-name: {name}\n\s+update-types: \['version-update:semver-major'\]", pip), (
            f'{name} major updates are not ignored; the 1.x pin is deliberate (CLAUDE.md)')


def test_nothing_merges_itself():
    assert 'auto-merge' not in TEXT and 'automerge' not in TEXT.lower()
