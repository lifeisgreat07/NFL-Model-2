"""One week control, used by two pages.

The Week Board had a stepper -- two arrows and a label, backed by a hidden
<select> that owns the selection -- and My Picks had a bare visible <select>.
The same job therefore looked like two different controls depending on which
tab you were on, and on a phone one of them was the iOS system wheel while the
other was a pair of arrows.

The fix is one implementation driven twice, not a second copy. That distinction
is the whole point: a copied stepper is the `.game-card` story again, where the
same markup existed in two render paths, one edit landed on one of them, and
the diff looked complete either way. So these tests check that the behaviour is
SHARED, not merely that both pages have something that looks like a stepper.

`-webkit-appearance: none` is not an alternative. It restyles the closed
control and does not touch what iOS opens when you tap it; the only way to stop
the system wheel is to stop using a native select as the visible control.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'src' / 'dashboard_template.html'

PREFIXES = ('week', 'picks-week')


@pytest.fixture(scope='module')
def source():
    return TEMPLATE.read_text(encoding='utf-8')


@pytest.mark.parametrize('prefix', PREFIXES)
def test_both_pages_have_the_whole_stepper(prefix, source):
    """All four elements, because three of them is a broken control.

    A label with no arrows renders fine and does nothing; arrows with no label
    leave the reader guessing which week they are on. Enumerated rather than
    spot-checked for the reason this repo keeps relearning: prose naming a
    protection without naming its coverage is how a gap survives.
    """
    for element, pattern in (
            ('select', rf'id="{prefix}-select"'),
            ('label', rf'id="{prefix}-step-label"'),
            ('previous arrow', rf'id="{prefix}-prev"'),
            ('next arrow', rf'id="{prefix}-next"')):
        assert re.search(pattern, source), (
            f'the {prefix!r} stepper has no {element}. Three of the four is a '
            'control that renders and misleads rather than one that fails.')


@pytest.mark.parametrize('prefix', PREFIXES)
def test_the_visible_control_is_never_the_native_select(prefix, source):
    """The actual user-visible fix, and the thing most likely to be undone.

    A native <select> is what iOS renders as the system wheel. Both pages keep
    one -- it owns the selection and is the no-script fallback -- but it must
    stay visually-hidden, with the arrows as the control anyone sees. Dropping
    `visually-hidden` in a tidy-up gives the page two week controls side by
    side, and puts the wheel back on the phone.
    """
    m = re.search(rf'<select id="{prefix}-select"[^>]*>', source)
    assert m, f'the {prefix!r} select is gone entirely'
    assert 'visually-hidden' in m.group(0), (
        f'the {prefix!r} select is visible again: {m.group(0)}. That is the '
        'iOS wheel back, beside a stepper that does the same job.')


def test_the_stepper_is_one_implementation_taking_a_prefix(source):
    """Shared behaviour, not two copies that happen to look alike.

    If either function hardcodes an element id, it can only ever drive one
    page, and the second page needs its own copy -- at which point the two
    controls are free to drift exactly as the two game-card render paths did.
    """
    for fn in ('syncWeekStepper', 'wireWeekStepper'):
        assert re.search(rf'function {fn}\(prefix\)', source), (
            f'{fn} no longer takes a prefix, so it can only serve one page')

    block = re.search(r'function syncWeekStepper\(.*?const OVERFLOW_PAGES',
                      source, re.S)
    assert block, 'the stepper block is no longer findable'
    code = re.sub(r'/\*.*?\*/', '', block.group(0), flags=re.S)
    code = re.sub(r'//.*', '', code)
    for hardcoded in ("'week-select'", "'week-prev'", "'week-next'",
                      "'week-step-label'"):
        assert hardcoded not in code, (
            f'the stepper hardcodes {hardcoded}, so it drives one page and the '
            'other needs a copy. That is the duplication this change removes.')


@pytest.mark.parametrize('prefix', PREFIXES)
def test_both_pages_actually_wire_their_stepper(prefix, source):
    """A stepper nobody wires is markup: arrows that render and do nothing.

    This repository has shipped the written-tested-never-called shape before --
    src/collect_agent_log.py ran nowhere for weeks with a full suite behind it
    -- so the call sites are enumerated rather than assumed to follow from the
    markup existing.
    """
    assert re.search(rf"wireWeekStepper\('{prefix}'\)", source), (
        f'nothing calls wireWeekStepper for {prefix!r}, so its arrows are '
        'decoration')


def test_the_shared_link_view_moves_the_stepper_with_it(source):
    """The one path that sets the week WITHOUT emitting a change event.

    showSharedPicks() assigns the select's value directly, and it has to: the
    change handler ends the shared view, so dispatching one there would close
    the thing it is opening. That makes it the single place where the
    "everyone listens to the select" rule cannot apply, and therefore the
    single place where the label can be left showing the previous week while
    the grid shows the shared one.

    Two controls disagreeing about the same state is the exact failure a shared
    stepper exists to prevent, so it would be a poor way to introduce one.
    """
    block = re.search(r'function showSharedPicks\(.*?\n\}', source, re.S)
    assert block, 'showSharedPicks is no longer findable'
    assert "syncWeekStepper('picks-week')" in block.group(0), (
        'showSharedPicks moves the week select without telling the stepper, so '
        'opening a share link leaves the arrows and their label on the '
        'previous week while the grid shows the shared one')
