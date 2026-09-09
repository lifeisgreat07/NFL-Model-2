"""The four working documents, kept honest.

`docs/context.md`, `docs/index.md`, `CLAUDE.md` and `memory/` exist because one
file was doing all four jobs and going stale in the parts that changed fastest.
Splitting them does not fix that on its own -- it creates three more files that
can go stale. These are the guards that make the split hold.

Every check here is one this repository has already been bitten by:

- a path named in a document that does not exist (CLAUDE.md, repeatedly);
- the same number stated in two places, drifting apart (the suite count read
  174 for three days, then 597 against a real 628);
- an index that silently stops covering what it indexes (the churn guard was
  wired into one of two workflows and the prose said only that it "prevents"
  the problem).
"""

import re
import sys
from datetime import date
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CONTEXT = REPO / 'docs' / 'context.md'
INDEX = REPO / 'docs' / 'index.md'
MEMORY = REPO / 'memory'
CLAUDE_MD = REPO / 'CLAUDE.md'

DOCS = {'docs/context.md': CONTEXT, 'docs/index.md': INDEX,
        'memory/README.md': MEMORY / 'README.md', 'CLAUDE.md': CLAUDE_MD}


@pytest.mark.parametrize('name', sorted(DOCS))
def test_the_document_exists(name):
    assert DOCS[name].exists(), f"{name} is gone; the reading order in docs/index.md names it"


def _backticked(text):
    return set(re.findall(r'`([^`\n]+)`', text))


@pytest.mark.parametrize('name', ['docs/context.md', 'docs/index.md'])
def test_every_path_these_documents_name_exists(name):
    """Same rule CLAUDE.md is already held to. A document that points at a file
    which is not there sends the next session looking for something that moved
    or was never written, and it does it silently."""
    text = DOCS[name].read_text(encoding='utf-8')
    missing = []
    for token in _backticked(text):
        if any(c in token for c in ' *<>|$()') or token.endswith('/'):
            continue
        if not token.endswith(('.py', '.yml', '.md', '.json', '.html')):
            continue
        if not (REPO / token).exists():
            missing.append(token)
    assert not missing, (
        f"{name} names {len(missing)} path(s) that do not exist: {sorted(missing)}")


def test_the_index_covers_every_workflow():
    """Enumerate rather than describe. A workflow added and not indexed is
    invisible to the next session, and 'the index lists the workflows' is the
    kind of sentence that stays true-sounding after it stops being true."""
    on_disk = {p.name for p in (REPO / '.github' / 'workflows').glob('*.yml')}
    listed = set(re.findall(r'\.github/workflows/([\w-]+\.yml)',
                            INDEX.read_text(encoding='utf-8')))
    assert on_disk <= listed, (
        f"docs/index.md does not list these workflows: {sorted(on_disk - listed)}")


def test_the_memory_index_matches_the_memory_files():
    """Both directions. An unlisted session file is one nobody will find; a
    listed file that does not exist is a dead link in the only place that
    records why a decision was made."""
    files = {p.name for p in MEMORY.glob('*.md') if p.name != 'README.md'}
    listed = set(re.findall(r'\]\((\d{4}-\d{2}-\d{2}(?:-\d+)?\.md)\)',
                            (MEMORY / 'README.md').read_text(encoding='utf-8')))
    assert files == listed, (
        f"memory/README.md and the files disagree. "
        f"On disk but unlisted: {sorted(files - listed)}. "
        f"Listed but missing: {sorted(listed - files)}")


def test_context_states_when_it_was_last_updated():
    m = re.search(r'Last updated:\s*(\d{4})-(\d{2})-(\d{2})',
                  CONTEXT.read_text(encoding='utf-8'))
    assert m, ("docs/context.md has no 'Last updated:' line. Without it nothing "
               "can tell a current file from one abandoned three stages ago")
    stamped = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    # One day of slack, deliberately. The agent writing this file runs on UTC
    # and the machine running the tests is on US local time; on the evening
    # this was written they read 09-09 and 09-08 respectively. A stamp one day
    # ahead is a timezone, not a lie. The repository's clock is the machine's,
    # because src/session_wrapup.py runs there.
    assert (stamped - date.today()).days <= 1, (
        f"docs/context.md claims it was updated {stamped}, more than a day in "
        f"the future — that is not a timezone, that is a wrong date")


def test_the_suite_count_is_stated_in_exactly_one_place():
    """The specific drift that started all of this. CLAUDE.md carried a suite
    count that read 174 for three days after it stopped being true, and later
    597 against a real 628. Two documents each carrying the number is two
    chances to be wrong; `src/session_wrapup.py` checks CLAUDE.md's against a
    real run, so that is the copy that stays."""
    pattern = re.compile(r'\*\*(\d[\d,]*) passing\*\*')
    ctx = pattern.findall(CONTEXT.read_text(encoding='utf-8'))
    assert not ctx, (
        f"docs/context.md states a suite count ({ctx}) in CLAUDE.md's format. "
        f"Only CLAUDE.md carries that figure, because session_wrapup.py checks "
        f"that one against a real run. State it in prose here or not at all")


def test_context_stays_short_enough_to_actually_read():
    """It is the first thing read every session. The moment it stops fitting on
    a screen it stops being read, and it becomes another CLAUDE.md -- which is
    the problem it was split out to solve."""
    lines = [l for l in CONTEXT.read_text(encoding='utf-8').splitlines() if l.strip()]
    assert len(lines) <= 70, (
        f"docs/context.md is {len(lines)} non-blank lines. Move anything "
        f"durable to CLAUDE.md and anything historical to memory/")


def test_claude_md_points_at_the_context_file():
    """The session ritual is 'read CLAUDE.md'. If that file does not send the
    reader onward, the split silently costs them the current state instead of
    organising it."""
    assert 'docs/context.md' in CLAUDE_MD.read_text(encoding='utf-8'), (
        "CLAUDE.md never mentions docs/context.md, so a session following the "
        "existing ritual would never learn where the current state lives")


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
