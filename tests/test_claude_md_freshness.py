"""
CLAUDE.md must not reference things that no longer exist.

This file is read cold at the start of every session and again after every
compaction. A wrong path or a dead test name in it does not fail anything --
it just quietly sends the next session looking for a file that moved, or
trusting a guard that was deleted. That is the most expensive kind of rot,
because a reader cannot tell a stale reference from a live one.

ONE THING THIS HAD TO LEARN. A handoff file legitimately contains two kinds of
statement: what exists now, and what is planned. `tests/test_plain_language.py`
is named in Stage 7.5 as work to do -- it SHOULD NOT exist yet, and an earlier
version of this file failed on it. Checking a plan the same way you check a
description is wrong. So the stage sections, which are forward-looking by
definition, are excluded; everything else -- Current state, Findings,
Environment, Traps -- describes the present and is checked.

Bare filenames are resolved by basename rather than exact path, because the
prose reasonably says `prune_build_churn.py` rather than
`src/prune_build_churn.py`. A moved file still fails, which is the point.

What this deliberately does NOT check is the suite count: a test that runs the
suite from inside the suite cannot terminate. That lives in
src/session_wrapup.py, which runs once at the end of a session.

Run with: pytest tests/test_claude_md_freshness.py -v
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
DOC = REPO / 'CLAUDE.md'

#: Referenced but not part of this repository.
EXTERNAL = {
    'scripts/validate_palette.js',   # ships with the dataviz skill
}

#: Illustrative names in format specs and examples, never real files.
ILLUSTRATIVE = {
    'path/to/file.py', 'src/thing.py', 'a.py', 'b.py',
    'test_guard.py',                 # a fixture's file, inside booth_fixtures
}


def _text():
    if not DOC.is_file():
        pytest.skip('CLAUDE.md not present in this checkout')
    return DOC.read_text(encoding='utf-8')


def _present_tense_only(text):
    """Drop the stage sections -- they describe work that does not exist yet."""
    out, skipping = [], False
    for line in text.splitlines():
        if re.match(r'^### Stage [0-9]', line):
            skipping = True
        elif line.startswith('## ') and not line.startswith('## The visual'):
            skipping = False
        if not skipping:
            out.append(line)
    return '\n'.join(out)


def _backticked(text):
    return [t.strip() for t in re.findall(r'`([^`\n]+)`', text)]


def test_the_document_exists_and_is_substantial():
    """Guard against every check below passing vacuously on an empty file."""
    t = _text()
    assert len(t) > 5000, (
        'CLAUDE.md is {} chars -- too short to be the real handoff, so every '
        'assertion below would pass while checking nothing'.format(len(t))
    )


def test_the_present_tense_sections_are_not_empty():
    """If the stage-stripping ever eats the whole file, say so loudly."""
    stripped = _present_tense_only(_text())
    assert len(stripped) > 2000, (
        'after removing stage sections only {} chars remain; the section '
        'boundaries have moved and this file is no longer checking '
        'anything'.format(len(stripped))
    )


def test_every_repository_path_it_names_exists():
    """A moved file leaves a silently wrong pointer for the next session."""
    text = _present_tense_only(_text())
    basenames = {p.name for p in REPO.rglob('*') if p.is_file()}

    missing = []
    for token in _backticked(text):
        if any(c in token for c in ' *<>|$()') or token.endswith('/'):
            continue
        if token in EXTERNAL or token in ILLUSTRATIVE:
            continue
        if '/' in token:
            # NOT lstrip('./') -- that strips a character SET, so it eats the
            # leading dot of `.github/workflows` and reports a real directory
            # as missing.
            rel = token[2:] if token.startswith('./') else token
            if not (REPO / rel).exists():
                missing.append(token)
        elif token.endswith(('.py', '.yml', '.json')):
            if token not in basenames:
                missing.append(token)

    assert not missing, (
        'CLAUDE.md names {} path(s) that do not exist:\n  {}\n'
        'Either the file moved and this document still points at the old '
        'place, or the reference was wrong when written. Both mislead the '
        'next session silently.'.format(len(missing), '\n  '.join(sorted(set(missing))))
    )


def test_every_test_name_it_names_exists():
    """A referenced guard that was deleted reads as protection that is present.

    This project has a permanent entry about that exact shape. A guard named
    in the handoff and absent from the suite is the same failure, with the
    documentation carrying it instead of the code.
    """
    named = set(re.findall(r'\btest_[a-z0-9_]+\b', _present_tense_only(_text())))
    if not named:
        pytest.skip('CLAUDE.md names no tests outside the stage plan')

    # Filenames as well as contents. A module named tests/test_x.py rarely
    # contains the string "test_x" anywhere inside it, so citing a whole guard
    # file by path -- which is how CLAUDE.md refers to most of them -- read as
    # a missing test. The ones that passed only did so because some other
    # file's docstring happened to mention them.
    haystack = '\n'.join(
        [p.stem for p in (REPO / 'tests').rglob('*.py')] +
        [p.read_text(encoding='utf-8', errors='ignore')
         for p in (REPO / 'tests').rglob('*.py')]
    )
    missing = sorted(n for n in named if n not in haystack)
    assert not missing, (
        'CLAUDE.md names {} test(s) that exist nowhere under tests/:\n  {}\n'
        'A guard named in the handoff and absent from the suite reads as '
        'protection that is present.'.format(len(missing), '\n  '.join(missing))
    )


def test_internal_section_references_name_a_real_heading():
    """A `See "X" above` pointing at a renamed heading wastes a session.

    This is not hypothetical. The 2026-09-07 prune renamed "Finished, and why
    it matters" to "Findings that still constrain the work" and left Stage 2
    pointing at the old title. Nothing failed; a reader just goes looking for
    a heading that is not there, and cannot tell whether the section was
    renamed or deleted.

    The path and test-name checks above did not catch it, because a section
    title is neither. Reading the file caught it, which is why the wrap-up
    procedure ends with reading it -- but a check is cheaper than a read.
    """
    text = _text()
    headings = {
        h.strip().strip('*`')
        for h in re.findall(r'^#{2,4}\s+(.+?)\s*$', text, re.M)
    }
    # Tolerate a heading carrying a trailing status marker like "<- COMPLETE".
    headings |= {h.split('  <-')[0].strip() for h in headings}

    referenced = re.findall(r'See "([^"]+)"\s+(?:above|below)', text)
    missing = sorted({r for r in referenced if r not in headings})
    assert not missing, (
        'CLAUDE.md points at {} section(s) that do not exist:\n  {}\n'
        'Headings present: {}\n'
        'A renamed heading leaves a reader unable to tell whether the section '
        'moved or was deleted.'.format(
            len(missing), '\n  '.join(missing), sorted(headings))
    )


def test_the_stage_list_is_ordered_and_unique():
    """Numbers are frozen, but they must still read in order.

    Catches a stage heading added out of order or a number reused -- the
    confusion the freeze exists to prevent.
    """
    heads = re.findall(r'^### Stage ([0-9]+(?:\.[0-9]+)?)\b', _text(), re.M)
    nums = [float(h) for h in heads]
    assert nums, 'CLAUDE.md has no "### Stage N" headings'
    dupes = sorted({n for n in nums if nums.count(n) > 1})
    assert not dupes, 'a stage number appears twice: {}'.format(dupes)
    assert nums == sorted(nums), (
        'stage headings are out of reading order: {}\nNumbers are frozen, but '
        'they must still appear in ascending order.'.format(nums)
    )
