"""A reader with scripts off gets an explanation, not a blank page.

WHY THIS EXISTS

Queue item 1 was investigated on 2026-09-20 and refuted: two <select>
elements ship visible in the markup, and the recorded reason was that they
served a reader with JavaScript disabled. Checking that reason is what turned
up the real finding. With scripts off this dashboard renders one section --
#page-ratings, the one the markup ships active -- containing a header row and
no data. All eighteen [data-page] controls are <button> elements with no href,
there is no :target rule and no anchor targeting a page, so nothing can change
which section is showing. A stranger with a script blocker saw an empty table
and no explanation, on a page whose whole job is to be a portfolio piece.

WHAT THIS CHECKS, AND WHAT IT DOES NOT

It checks that the note EXISTS, that it comes before any page section so it
cannot inherit the unreachability it describes, and that it names the cause.
It does not check that the wording is good, and it cannot check that the note
renders -- no CI job here has a browser. Rendering was confirmed by hand on
2026-09-21 and the mechanism is what is guarded, which is the same split the
colour co-occurrence work settled on for the same reason.

WHY THE ORDER ASSERTION IS THE LOAD-BEARING ONE

A <noscript> inside a section is only seen when that section is the active
one. Since no-JS readers cannot change the active section, a note placed
inside any page but #page-ratings would be invisible to exactly the audience
it addresses -- and it would look completely correct in a diff, on a page that
renders fine with scripts on. That is the shape this repository keeps meeting:
a step that runs correctly with nothing downstream consuming it.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = REPO_ROOT / 'src' / 'dashboard_template.html'


@pytest.fixture(scope='module')
def source():
    return TEMPLATE.read_text(encoding='utf-8')


def test_the_page_explains_itself_with_scripts_off(source):
    """The note is present, and there is exactly one of it."""
    notes = re.findall(r'<noscript>.*?</noscript>', source, re.S)
    assert len(notes) == 1, (
        f'expected exactly one <noscript> block, found {len(notes)}. With '
        'scripts off this dashboard renders one section with no data in it, '
        'so a reader who arrives with a script blocker needs to be told why '
        'rather than shown an empty table.')


def test_the_note_comes_before_every_page_section(source):
    """Placement is the whole point, so it is asserted rather than assumed.

    A <noscript> inside a section is shown only when that section is active,
    and a no-JS reader cannot change which one is. Putting the note inside a
    page would hide it from the only people who can see it.
    """
    note = re.search(r'<noscript>', source)
    assert note, 'the <noscript> note is gone entirely'

    sections = list(re.finditer(r'<section class="page[^"]*"', source))
    # Vacuity guard, written before the assertion below rather than after the
    # first surprise: if this matcher finds nothing, "the note precedes every
    # section" is true over an empty set and proves nothing at all. The count
    # is not pinned to a number here -- Stage 7.5 moved it once already and
    # tests/test_nav_targets.py owns that question -- only to being non-zero.
    assert sections, (
        'found no page sections to compare against, so this test would pass '
        'over an empty set. The matcher has drifted -- re-anchor it before '
        'reading anything off it.')

    first = sections[0]
    assert note.start() < first.start(), (
        f'the <noscript> note at character {note.start()} comes after the '
        f'first page section at {first.start()}. Inside a section it is only '
        'visible when that section is active, and a reader with scripts off '
        'cannot change which section that is -- so the note would be hidden '
        'from exactly the audience it is written for, while looking correct '
        'in the diff and on the rendered page.')


def test_the_note_says_what_is_wrong_and_how_to_fix_it(source):
    """Present and well-placed is not the same as useful."""
    note = re.search(r'<noscript>.*?</noscript>', source, re.S)
    assert note, 'the <noscript> note is gone entirely'
    text = re.sub(r'<[^>]+>', ' ', note.group(0))
    text = re.sub(r'\s+', ' ', text).strip().lower()

    assert len(text) > 80, (
        f'the note is {len(text)} characters of visible text: "{text}". An '
        'empty or one-word <noscript> satisfies the existence check above and '
        'tells a reader nothing.')
    assert 'javascript' in text, (
        f'the note never names JavaScript: "{text}". A reader who does not '
        'know why the page is empty cannot act on a note that does not say.')
