"""CONTRIBUTING.md and the pull request template (Stage 29, from the
2026-09-28 audit).

Both are instructions a stranger will follow literally, so they are held to
the repository like README.md is: every path they name exists, the set-up
commands are the README's own, and the "Human review required:" line they
tell an author to write is the exact prefix Scout pre-flight looks for.

Run with: pytest tests/test_contributing.py -v
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONTRIBUTING = REPO / 'CONTRIBUTING.md'
TEMPLATE = REPO / '.github' / 'pull_request_template.md'
sys.path.insert(0, str(REPO / 'src'))


def text(p):
    return p.read_text(encoding='utf-8')


def test_every_path_contributing_names_exists():
    named = re.findall(r'`([\w./-]+/[\w./-]*|[\w-]+\.(?:md|py|yml|txt))`', text(CONTRIBUTING))
    named += re.findall(r'\]\(([\w./-]+)\)', text(CONTRIBUTING))
    assert named, 'found no paths in CONTRIBUTING.md -- re-anchor this guard'
    missing = sorted({n for n in named if not (REPO / n).exists()})
    assert not missing, f'CONTRIBUTING.md names paths that do not exist: {missing}'


def test_the_setup_commands_are_the_readmes():
    block = re.search(r'```bash\n(.*?)```', text(CONTRIBUTING), re.S).group(1)
    readme = text(REPO / 'README.md')
    for line in filter(None, (l.strip() for l in block.splitlines())):
        assert line in readme, f'CONTRIBUTING.md runs {line!r}, which README.md does not'


def test_the_human_review_line_is_the_one_preflight_checks():
    src = text(REPO / 'src' / 'scout_preflight.py')
    assert 'Human review required:' in src, 'scout_preflight no longer looks for the line -- re-anchor'
    assert '"Human review required:"' in text(CONTRIBUTING)
    assert '"Human review required:"' in text(TEMPLATE)


def test_the_template_asks_for_the_command_beside_every_number():
    t = text(TEMPLATE)
    assert 'For every number, the command that produced it' in t
    assert 'python -B -m pytest -q -p no:cacheprovider' in t
    assert '**Not checked.**' in t
