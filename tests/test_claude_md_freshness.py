"""
CLAUDE.md, docs/traps.md and docs/stage-history.md must not reference things
that no longer exist.

These are read cold at the start of every session and again after every
compaction. A wrong path or a dead test name in them does not fail anything --
it just quietly sends the next session looking for a file that moved, or
trusting a guard that was deleted. That is the most expensive kind of rot,
because a reader cannot tell a stale reference from a live one.

THE SPLIT (Stage 29, 2026-09-29). Until then this was one 3,000-line file.
The rules stayed in CLAUDE.md; the traps moved to docs/traps.md and the stage
sections to docs/stage-history.md. Every check below runs over all three,
because a guard that kept reading only CLAUDE.md would have gone on passing
while 1,200 lines of traps and every stage heading sat outside it -- the
"guard wired into one of several paths" trap, created by the move itself.

ONE THING THIS HAD TO LEARN. A handoff file legitimately contains two kinds of
statement: what exists now, and what is planned. `tests/test_plain_language.py`
is named in Stage 7.5 as work to do -- it SHOULD NOT exist yet, and an earlier
version of this file failed on it. Checking a plan the same way you check a
description is wrong. So the stage sections, which are forward-looking by
definition, are excluded; everything else -- Current state, Findings,
Environment, Traps, and the notes at the top of the stage history -- describes
the present and is checked.

Bare filenames are resolved by basename rather than exact path, because the
prose reasonably says `prune_build_churn.py` rather than
`src/prune_build_churn.py`. A moved file still fails, which is the point.

What this deliberately does NOT check is the suite count: a test that runs the
suite from inside the suite cannot terminate. That lives in
src/agents/session_wrapup.py, which runs once at the end of a session.

Run with: pytest tests/test_claude_md_freshness.py -v
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
DOC = REPO / 'CLAUDE.md'
TRAPS = REPO / 'docs' / 'traps.md'
HISTORY = REPO / 'docs' / 'stage-history.md'
DOCS = {'CLAUDE.md': DOC, 'docs/traps.md': TRAPS, 'docs/stage-history.md': HISTORY}

#: CLAUDE.md is read under compaction pressure on every session. The split
#: took it from 3,079 lines to about 430; this is the line past which it is
#: turning back into the file the split replaced.
MAX_CLAUDE_MD_LINES = 450

#: Referenced but not part of this repository.
EXTERNAL = {
    'scripts/validate_palette.js',   # ships with the dataviz skill
}

#: Illustrative names in format specs and examples, never real files.
ILLUSTRATIVE = {
    'path/to/file.py', 'src/thing.py', 'a.py', 'b.py',
    'test_guard.py',                 # a fixture's file, inside booth_fixtures
}


def _text(name='CLAUDE.md'):
    path = DOCS[name]
    if not path.is_file():
        pytest.skip('{} not present in this checkout'.format(name))
    return path.read_text(encoding='utf-8')


def _all_text():
    return '\n'.join(_text(name) for name in DOCS)


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


@pytest.mark.parametrize('name', sorted(DOCS))
def test_the_document_exists_and_is_substantial(name):
    """Guard against every check below passing vacuously on an empty file."""
    t = _text(name)
    assert len(t) > 5000, (
        '{} is {} chars -- too short to be the real document, so every '
        'assertion below would pass while checking nothing'.format(name, len(t))
    )


@pytest.mark.parametrize('name', ['CLAUDE.md', 'docs/traps.md'])
def test_the_present_tense_sections_are_not_empty(name):
    """If the stage-stripping ever eats a whole file, say so loudly."""
    stripped = _present_tense_only(_text(name))
    assert len(stripped) > 2000, (
        'after removing stage sections only {} chars of {} remain; the '
        'section boundaries have moved and this file is no longer checking '
        'anything'.format(len(stripped), name)
    )


@pytest.mark.parametrize('name', sorted(DOCS))
def test_every_repository_path_it_names_exists(name):
    """A moved file leaves a silently wrong pointer for the next session."""
    text = _present_tense_only(_text(name))
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
        '{} names {} path(s) that do not exist:\n  {}\n'
        'Either the file moved and this document still points at the old '
        'place, or the reference was wrong when written. Both mislead the '
        'next session silently.'.format(
            name, len(missing), '\n  '.join(sorted(set(missing))))
    )


@pytest.mark.parametrize('name', sorted(DOCS))
def test_every_test_name_it_names_exists(name):
    """A referenced guard that was deleted reads as protection that is present.

    This project has a permanent entry about that exact shape. A guard named
    in the handoff and absent from the suite is the same failure, with the
    documentation carrying it instead of the code.
    """
    named = set(re.findall(r'\btest_[a-z0-9_]+\b', _present_tense_only(_text(name))))
    if not named:
        pytest.skip('{} names no tests outside the stage plan'.format(name))

    # Filenames as well as contents. A module named tests/test_x.py rarely
    # contains the string "test_x" anywhere inside it, so citing a whole guard
    # file by path -- which is how these documents refer to most of them --
    # read as a missing test. The ones that passed only did so because some
    # other file's docstring happened to mention them.
    haystack = '\n'.join(
        [p.stem for p in (REPO / 'tests').rglob('*.py')] +
        [p.read_text(encoding='utf-8', errors='ignore')
         for p in (REPO / 'tests').rglob('*.py')]
    )
    missing = sorted(n for n in named if n not in haystack)
    assert not missing, (
        '{} names {} test(s) that exist nowhere under tests/:\n  {}\n'
        'A guard named in the handoff and absent from the suite reads as '
        'protection that is present.'.format(name, len(missing), '\n  '.join(missing))
    )


def test_internal_section_references_name_a_real_heading():
    """A `See "X" above` pointing at a renamed heading wastes a session.

    This is not hypothetical. The 2026-09-07 prune renamed "Finished, and why
    it matters" to "Findings that still constrain the work" and left Stage 2
    pointing at the old title. Nothing failed; a reader just goes looking for
    a heading that is not there, and cannot tell whether the section was
    renamed or deleted.

    Since the split a reference can cross files -- Stage 2's pointer at the
    Findings now lives in docs/stage-history.md while the Findings stay in
    CLAUDE.md -- so the headings of all three documents count as targets, and
    the references of all three are checked.

    The path and test-name checks above did not catch it, because a section
    title is neither. Reading the file caught it, which is why the wrap-up
    procedure ends with reading it -- but a check is cheaper than a read.
    """
    text = _all_text()
    headings = {
        h.strip().strip('*`')
        for h in re.findall(r'^#{1,4}\s+(.+?)\s*$', text, re.M)
    }
    # Tolerate a heading carrying a trailing status marker like "<- COMPLETE".
    headings |= {h.split('  <-')[0].strip() for h in headings}

    referenced = re.findall(r'See "([^"]+)"\s+(?:above|below)', text)
    missing = sorted({r for r in referenced if r not in headings})
    assert not missing, (
        'These documents point at {} section(s) that do not exist:\n  {}\n'
        'Headings present: {}\n'
        'A renamed heading leaves a reader unable to tell whether the section '
        'moved or was deleted.'.format(
            len(missing), '\n  '.join(missing), sorted(headings))
    )


def test_the_stage_list_is_ordered_and_unique():
    """Numbers are frozen, but they must still read in order.

    Catches a stage heading added out of order or a number reused -- the
    confusion the freeze exists to prevent. The stage sections live in
    docs/stage-history.md since the split.
    """
    heads = re.findall(r'^### Stage ([0-9]+(?:\.[0-9]+)?)\b',
                       _text('docs/stage-history.md'), re.M)
    nums = [float(h) for h in heads]
    assert nums, 'docs/stage-history.md has no "### Stage N" headings'
    dupes = sorted({n for n in nums if nums.count(n) > 1})
    assert not dupes, 'a stage number appears twice: {}'.format(dupes)
    assert nums == sorted(nums), (
        'stage headings are out of reading order: {}\nNumbers are frozen, but '
        'they must still appear in ascending order.'.format(nums)
    )


# --- the split itself -------------------------------------------------------

def test_claude_md_holds_no_stage_sections():
    """A stage written back into CLAUDE.md is the first step of undoing the
    split, and the ordering check above would never see it, because it reads
    the stage history only."""
    stray = re.findall(r'^### Stage [0-9].*$', _text('CLAUDE.md'), re.M)
    assert not stray, (
        'CLAUDE.md has stage section(s) again: {}\nStage sections live in '
        'docs/stage-history.md; CLAUDE.md keeps a one-line index.'.format(stray)
    )


def test_claude_md_points_at_the_traps_and_the_stage_history():
    """The session ritual is 'read CLAUDE.md'. If it stops naming the two files
    the split created, the traps become a file nobody opens -- which is the
    whole of their value lost with every test still green.

    Checked in "Start here" specifically, not anywhere in the file: a passing
    mention in some other paragraph would satisfy a whole-file search while
    the one sentence a cold reader acts on had lost the pointer.
    """
    m = re.search(r'^### Start here\s*$(.*?)^##', _text('CLAUDE.md'), re.M | re.S)
    assert m, 'CLAUDE.md has no "### Start here" section to hold the pointers'
    start = m.group(1)
    for target in ('docs/traps.md', 'docs/stage-history.md'):
        assert '`{}`'.format(target) in start, (
            'CLAUDE.md\'s "Start here" never names `{}`, so a session reading '
            'it cold would not learn that file exists'.format(target))


def test_claude_md_stays_short_enough_to_read_cold():
    """What the split was for. Past this length the rules are being buried
    again; move history to docs/stage-history.md, a trap to docs/traps.md,
    and anything current to docs/context.md."""
    n = len(_text('CLAUDE.md').splitlines())
    assert n <= MAX_CLAUDE_MD_LINES, (
        'CLAUDE.md is {} lines, over {}. Move history to '
        'docs/stage-history.md, traps to docs/traps.md, and current state to '
        'docs/context.md.'.format(n, MAX_CLAUDE_MD_LINES))
