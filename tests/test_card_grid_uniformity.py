"""The Week Board cards in a row must end on a common baseline.

The owner's report, on 2026-09-11: "the third column of cards is slightly
shorter than the first 2 columns ... I want the length to be uniform", then
"there is a difference between the explanation paragraphs in columns 1 and 2
and then 3 causing the difference."

Both halves of that are right, and measuring found the larger cause first.
With the coin-flip track record on the card face, cards took six distinct
heights spanning 205px, because that block is 129px and appears on some bands
and not others. With it behind the breakdown toggle the spread is 20px -- one
line of explanation prose wrapping to two lines instead of three -- and
`align-items: stretch` absorbs that.

These are source assertions rather than a rendered measurement. Rendering
needs a browser, which is not installed on the machine this suite runs on, and
the three declarations below are what the layout actually rests on: remove any
one and the ragged edge comes back. The rendered numbers are recorded in the
PR and in the comments beside each declaration.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'src' / 'dashboard_template.html'


@pytest.fixture(scope='module')
def css():
    return TEMPLATE.read_text(encoding='utf-8')


def _rule(css_text, selector):
    """Every declaration block for a selector, joined, or None if there are none.

    ALL of them, not the first. `.game-card` is declared twice -- once for
    `container-type`, well above, and once for the visual block -- and reading
    only the first made test_the_card_is_a_column fail against a file that was
    correct. A selector appearing more than once is normal in this stylesheet
    and a guard that assumes otherwise reports the wrong thing.

    The `\\s*\\{` is what keeps `.game-card` from matching `.game-card.has-flag`
    or `.game-card > .why-toggle`: the brace has to follow the selector.
    """
    blocks = re.findall(re.escape(selector) + r'\s*\{([^}]*)\}', css_text)
    return '\n'.join(blocks) if blocks else None


def test_the_grid_stretches_cards_to_a_common_height(css):
    body = _rule(css, '.game-grid')
    assert body is not None, '.game-grid rule is gone'
    assert 'align-items:stretch' in body.replace(' ', ''), (
        "the card grid no longer stretches its cards to a common height, so "
        "the row ends on a ragged edge -- which is the defect reported on "
        "2026-09-11. It was `align-items:start` until the coin-flip track "
        "record moved off the card face; start was right while cards spanned "
        "205px and is wrong now that they span 20px.")


def test_the_grid_does_not_force_every_row_to_the_tallest_row(css):
    """The overcorrection, and it is worse than the defect.

    `grid-auto-rows: 1fr` makes every row as tall as the tallest row in the
    grid. Opening one breakdown adds ~230px to one card, which would then pad
    all sixteen to that height -- the ragged-gap problem converted into a
    uniform-waste problem, on every card at once instead of in one row.
    """
    body = _rule(css, '.game-grid')
    assert 'grid-auto-rows' not in body, (
        "grid-auto-rows on .game-grid ties every row to the tallest row in "
        "the grid; opening a single breakdown then pads all sixteen cards")


def test_the_card_is_a_column_so_the_toggle_can_reach_the_bottom(css):
    body = _rule(css, '.game-card')
    assert body is not None, '.game-card rule is gone'
    flat = body.replace(' ', '')
    assert 'display:flex' in flat and 'flex-direction:column' in flat, (
        "the card is no longer a flex column, so `margin-top:auto` on the "
        "breakdown toggle does nothing and the slack the grid creates lands "
        "after the last element as an unexplained gap")


def test_the_toggle_is_pinned_to_the_card_bottom(css):
    """What turns leftover space into structure.

    Scoped with `>` deliberately: the same button on My Picks is not inside a
    stretched grid and must keep its ordinary margin.
    """
    body = _rule(css, '.game-card > .why-toggle')
    assert body is not None, (
        "the `.game-card > .why-toggle` rule is gone, so the breakdown "
        "toggles no longer sit on a common baseline across a row")
    flat = body.replace(' ', '')
    assert 'margin-top:auto' in flat, (
        "the toggle no longer absorbs the slack, so it floats directly under "
        "the prose and the gap falls below it")
    assert 'padding-top' in flat, (
        "margin-top:auto REPLACES the 11px margin the toggle had rather than "
        "adding to it, so the padding is what keeps it off the prose above")


def test_the_coin_flip_case_is_not_back_on_the_card_face(css):
    """The height spread is downstream of this one decision.

    Guarded here as well as in tests/test_pick_track_record.py because the two
    tests fail for different reasons and a reader of either should learn the
    other exists: that one is about what a reader must meet, this one is about
    what the layout can absorb.
    """
    m = re.search(r'const notable\s*=\s*([^;]+);', css)
    assert m, 'trackRecordHtml no longer computes a `notable` case'
    assert 'coinFlip' not in m.group(1), (
        "the coin-flip band is back on the card face. It was 129px on seven "
        "of sixteen cards and is the reason card heights spanned 205px; "
        "putting it back reinstates the ragged edge this file guards against")
