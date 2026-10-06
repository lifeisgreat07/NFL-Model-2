"""The stage history, split by era (Stage 49 item 24).

docs/stage-history.md passed 2,200 lines and is now an index. Each era's
sections live under docs/history/, moved verbatim. Held here:
- the index lists every era file and names none that is missing;
- each era file and the index stay under a size a reader can take in, the
  guard docs/traps.md has;
- no section heading appears twice across the eras;
- the split lost nothing: every era file's sections, in order, are the
  sections the file had before.

Run with: pytest tests/test_stage_history_split.py -v
"""
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'docs' / 'stage-history.md'
ERAS = ROOT / 'docs' / 'history'
MAX_ERA_LINES = 600
MAX_INDEX_LINES = 60
#: The commit before the split, whose docs/stage-history.md held every section.
BEFORE_SPLIT_PATH = 'docs/stage-history.md'


def listed():
    return re.findall(r'`docs/history/([^`]+\.md)`', INDEX.read_text(encoding='utf-8'))


def test_the_index_lists_every_era_file_and_only_real_ones():
    on_disk = sorted(p.name for p in ERAS.glob('*.md'))
    assert sorted(listed()) == on_disk
    assert listed() == sorted(listed()), 'eras are listed oldest first, which is their file names\' order'


def test_each_file_stays_readable():
    n = len(INDEX.read_text(encoding='utf-8').splitlines())
    assert n <= MAX_INDEX_LINES, f'docs/stage-history.md is {n} lines; it is an index now'
    for p in ERAS.glob('*.md'):
        n = len(p.read_text(encoding='utf-8').splitlines())
        assert n <= MAX_ERA_LINES, f'{p.name} is {n} lines, over {MAX_ERA_LINES}: start a new era file'


def test_no_section_appears_twice():
    seen = {}
    for p in sorted(ERAS.glob('*.md')):
        for h in re.findall(r'^#{2,3} .+$', p.read_text(encoding='utf-8'), re.M):
            assert h not in seen, f'{h!r} is in both {seen[h]} and {p.name}'
            seen[h] = p.name


def _sections(text):
    lines = text.replace('\r\n', '\n').split('\n')
    first = next(i for i, ln in enumerate(lines) if ln.startswith('## '))
    return '\n'.join(lines[first:]).rstrip('\n')


def test_the_split_lost_nothing():
    """The sections as they stood before the split, against the era files
    joined in order. Read from git: the last commit whose stage-history.md
    still had the sections."""
    try:
        log = subprocess.run(['git', 'log', '--format=%H', '--', BEFORE_SPLIT_PATH], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        pytest.skip('git not available')
    before = None
    for sha in log:
        old = subprocess.run(['git', 'show', f'{sha}:{BEFORE_SPLIT_PATH}'], cwd=ROOT,
                             capture_output=True, text=True, encoding='utf-8').stdout
        if '## Stages 50 to 61' in old:
            before = old
            break
    if before is None:
        pytest.skip('no commit before the split in this clone')
    joined = '\n\n'.join(_sections(p.read_text(encoding='utf-8')) for p in sorted(ERAS.glob('*.md'),
                                                                                 key=lambda p: listed().index(p.name)))
    old_heads = re.findall(r'^#{2,3} .+$', _sections(before), re.M)
    new_heads = re.findall(r'^#{2,3} .+$', joined, re.M)
    assert old_heads == new_heads[:len(old_heads)], 'a section went missing or moved out of order'
    for line in _sections(before).split('\n'):
        if line.strip():
            assert line in joined, f'a line of the old history is in no era file: {line[:80]!r}'
