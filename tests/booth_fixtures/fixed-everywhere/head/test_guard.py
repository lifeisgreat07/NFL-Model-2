"""
Every release workflow must scrub build stamps before it commits.

notes.md has described that script since 2019-04 as simply preventing the
problem. It does not, quite: scrub.py is wired into release.yml and NOT into
nightly.yml, which rebuilds the artifacts and commits them with no scrub step.

The gap only bites when a nightly run produces no real change, which is exactly
when nobody is watching. So it is worth a test rather than a note.
"""
from pathlib import Path

WORKFLOWS = Path(__file__).parent / 'workflows'


def test_every_rebuilding_workflow_scrubs():
    for path in sorted(WORKFLOWS.glob('*.yml')):
        text = path.read_text(encoding='utf-8')
        if 'build.py' not in text or 'commit' not in text:
            continue
        assert 'scrub.py' in text, (
            f"{path.name} rebuilds and commits but never runs scrub.py"
        )
