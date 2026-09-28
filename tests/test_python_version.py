"""The Python version is written down once and every workflow uses it
(Stage 25 item 7).

The 2026-09-28 audit: nothing in the repository said which Python to use,
though by its reading the pins decide it (scikit-learn 1.9.0 needs 3.11 or
newer; pandas 1.5.3 has no wheels for 3.12). Every workflow already set up
3.11 by hand, and markys runs 3.11. `.python-version` now states it for pyenv, uv and anyone
reading the repo, and this test holds every workflow to it.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_repo_names_one_python_version():
    text = (ROOT / '.python-version').read_text(encoding='utf-8').strip()
    assert re.fullmatch(r'3\.\d+', text), text


def test_every_workflow_sets_up_that_version():
    want = (ROOT / '.python-version').read_text(encoding='utf-8').strip()
    found = []
    for p in sorted((ROOT / '.github' / 'workflows').glob('*.yml')):
        for v in re.findall(r"python-version:\s*'?([\d.]+)'?", p.read_text(encoding='utf-8')):
            found.append((p.name, v))
    assert len(found) >= 10, f'the scan found only {found} -- re-anchor it'
    wrong = [(f, v) for f, v in found if v != want]
    assert not wrong, f'workflows set up a different Python from .python-version ({want}): {wrong}'
