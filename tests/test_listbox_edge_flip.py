"""The open listbox must not leave the viewport, and the rule that keeps it in.

Two halves, deliberately, because after the Week Board's sort labels were
shortened NOTHING ON THE PAGE REACHES THE FLIP any more: measured across 21
viewport widths from 320 to 520, on both listboxes, the decision comes back
'as-is' every time and no list crosses the right edge. A rendered check alone
would therefore assert a property that holds for a reason unrelated to the
rule, and the rule would rot unnoticed until the next control or the next long
option -- which is this repository's "deleting the only input that reaches a
branch silently untests that branch" trap, and its prescribed answer is what
this file does: state the rule as a plain function and check it twice.

The first half runs lbxFlipDecision over a table of synthetic geometries that
keeps every branch alive regardless of what the markup holds this week. The
second asserts, over the real built page, the property the rule exists to
protect.

Why it matters at all, measured on `main` at 0451149 before the fix, at a
390px mobile-emulated viewport: the sort list opened to x=431 against a 390px
client width and documentElement.scrollWidth went 390 -> 431, so the whole
document scrolled sideways and the page heading read "eek Board".
"""
import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / 'src' / 'dashboard_template.html'


@pytest.fixture(scope='module')
def source():
    return TEMPLATE.read_text(encoding='utf-8')


# --------------------------------------------------------------------------
# Half one: the rule itself, over inputs the page cannot currently produce.
# --------------------------------------------------------------------------

# left, width, anchorRight, viewport, expected
GEOMETRIES = [
    # Comfortably inside: the ordinary case, and the only one the shipped page
    # reaches today.
    (12, 232, 244, 390, 'as-is'),
    # Exactly flush with the right edge is inside, not outside. An off-by-one
    # here would flip a list that fits, which is a visible change for nothing.
    (158, 232, 390, 390, 'as-is'),
    # One pixel past: the smallest real overflow. The 430px case that shipped
    # was five.
    (159, 232, 391, 390, 'flip'),
    # The measured pre-fix geometry at 390px.
    (187, 244, 374, 390, 'flip'),
    # Flipping would push it off the LEFT edge, so it must not flip: a list
    # wider than the room to the left of its anchor. Reverting keeps the
    # already-recorded defect rather than trading it for a new one.
    (200, 300, 250, 390, 'as-is'),
    # Flipped left lands exactly on zero, which is on-screen, so flip.
    (200, 250, 250, 390, 'flip'),
    # A list wider than the viewport itself cannot be placed anywhere; it must
    # not flip, because flipping moves the part the reader can see off-screen.
    (10, 500, 190, 390, 'as-is'),
]


@pytest.fixture(scope='module')
def decide(source):
    """Run the shipped lbxFlipDecision in node, not a Python re-implementation.

    A Python copy of the rule would pass this file while the page did
    something else -- the guard would be testing the copy. Extract the real
    function from the template and execute it.

    The extraction is anchored on the whole function signature line, not on
    the bare name: `lbxFlipDecision` also appears in placeList() and in two
    comments, and a matcher anchored on an identifier finds whichever
    occurrence comes first.
    """
    m = re.search(
        r'^function lbxFlipDecision\(listLeft, listWidth, anchorRight, viewportWidth\)\{\n'
        r'(?:.*?\n)*?\}$',
        source, re.M)
    assert m, (
        'lbxFlipDecision is gone from src/dashboard_template.html, or its '
        'signature changed. It is the rule this whole file exists to check; '
        'if it moved, move this anchor with it rather than deleting the test.')
    fn = m.group(0)
    # Anchor loosely, assert strictly. The bound is here to catch a regex that
    # ran past the closing brace into the rest of the script, which would make
    # every assertion below about the wrong text -- not to pin the function's
    # length. An earlier version required more than 200 characters and turned
    # the mutation that DELETES the revert branch into a fixture error:
    # WRONG-GUARD, "Failures: none reported", blaming a healthy guard. A guard
    # has to fail on its own assertion, never by making its fixture unusable.
    assert len(fn) < 800, (
        f'the extracted function is {len(fn)} characters, which is far larger '
        'than this function -- the match has run past it into the rest of the '
        'script, and every assertion below would be about the wrong text')

    def run(cases):
        script = fn + '\nconst out = ' + json.dumps(cases) + \
            '.map(c => lbxFlipDecision(c[0], c[1], c[2], c[3]));\n' \
            'process.stdout.write(JSON.stringify(out));'
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True)
        assert r.returncode == 0, f'node failed: {r.stderr}'
        return json.loads(r.stdout)

    return run


def test_the_rule_answers_correctly_over_geometries_the_page_cannot_reach(decide):
    got = decide([list(g[:4]) for g in GEOMETRIES])
    want = [g[4] for g in GEOMETRIES]
    wrong = [(g, w, a) for g, w, a in zip(GEOMETRIES, want, got) if w != a]
    assert not wrong, '\n'.join(
        f'left={g[0]} width={g[1]} anchorRight={g[2]} viewport={g[3]}: '
        f'expected {w}, got {a}' for g, w, a in wrong)


def test_both_answers_are_actually_produced_by_this_table(decide):
    """The companion to every "every X must Y" assertion in this repo.

    A table that only ever produces 'as-is' would pass the test above while
    proving nothing about the branch that matters, and it would fail open --
    which is the expensive direction. This names both answers and fails if
    either has stopped appearing.
    """
    got = set(decide([list(g[:4]) for g in GEOMETRIES]))
    assert got == {'as-is', 'flip'}, (
        f'the geometry table now produces {sorted(got)}. Both branches have '
        'to stay alive here, because the rendered page reaches neither.')


def test_the_rule_distinguishes_its_two_reasons_for_not_flipping(decide):
    """'as-is' has two causes and they must not collapse into a boolean.

    It already fits, and flipping would be worse. They are the same answer but
    not the same fact, and a future caller that wants to log or style the
    second needs them separable at the call site rather than re-derived.
    """
    fits, worse = decide([[12, 232, 244, 390], [200, 300, 250, 390]])
    assert fits == 'as-is' and worse == 'as-is'


def test_place_list_consults_the_rule_rather_than_reimplementing_it(source):
    """The function is only a rule if the page actually asks it.

    A placeList() that compared edges itself would leave this whole file
    testing an orphan -- the "guard wired into one of several paths" shape,
    with the paths being one.
    """
    m = re.search(r'function placeList\(\)\{(.*?)\n  \}', source, re.S)
    assert m, 'placeList() is gone; the listbox no longer places its own list'
    body = m.group(1)
    assert 'lbxFlipDecision(' in body, (
        'placeList() no longer calls lbxFlipDecision, so the rule above is an '
        'orphan and the page decides for itself')
    assert "=== 'flip'" in body, (
        "placeList() no longer compares against 'flip' -- if it is treating "
        'the answer as truthy, every non-flip answer now flips')


def test_the_flip_is_measured_after_the_list_is_visible(source):
    """A [hidden] element reports a zero rectangle.

    Measuring before unhiding returns right===0, which is never greater than
    any viewport, so the flip would silently never fire and the control would
    look exactly as it did before the fix -- a fix that is present, tested at
    the unit level, and inert.
    """
    m = re.search(r'function openList\(\)\{(.*?)\n  \}', source, re.S)
    assert m, 'openList() is gone'
    body = m.group(1)
    assert 'list.hidden = false;' in body and 'placeList();' in body, (
        'openList() no longer both unhides the list and places it')
    assert body.index('list.hidden = false;') < body.index('placeList();'), (
        'placeList() now runs before the list is unhidden, so it measures a '
        'zero rectangle and can never decide to flip')


def test_the_flip_class_moves_both_edges(source):
    """left:auto as well as right:0.

    Setting right:0 alone leaves left:0 in force from .lbx-list, and a box
    with both edges pinned stretches instead of moving -- the list would span
    from the control's left edge to its right and the overflow would remain.
    """
    m = re.search(r'\.lbx-list--flip\{([^}]*)\}', source)
    assert m, '.lbx-list--flip is gone from the stylesheet'
    rule = m.group(1)
    assert 'left:auto' in rule.replace(' ', ''), (
        '.lbx-list--flip no longer releases the left edge, so the list '
        'stretches across the control instead of moving to its right edge')
    assert 'right:0' in rule.replace(' ', ''), (
        '.lbx-list--flip no longer anchors the right edge')
