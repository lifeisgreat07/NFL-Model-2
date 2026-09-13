"""Changing a pick repaints one card. It does not rebuild the grid.

Reported from a phone: with every card picked, changing a pick on any card
below the first two scrolls the page to the top. The cause is that the tap
handler called `renderPicksGrid()`, which replaces the whole grid through
`innerHTML` -- destroying the button under the user's finger along with every
other card, mid-tap.

It does not reproduce in headless Chromium, which has scroll anchoring on by
default and absorbs it. That is a difference between engines, not evidence
there was nothing to fix, and it is why these tests assert the MECHANISM
rather than the scroll position: that the tapped node survives, that nothing
else is rebuilt, and that one function is the only thing that paints a card.

This is also the rule this repository already wrote down, after an open
breakdown vanished on a filter change: a wholesale innerHTML re-render
silently destroys interaction state. Focus, the active touch and the scroll
position are all interaction state.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'src' / 'dashboard_template.html'


@pytest.fixture(scope='module')
def source():
    return TEMPLATE.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def tap_handler(source):
    """The pick button's click handler, comments stripped.

    Stripped because the comment inside it quotes `renderPicksGrid()` while
    explaining why it must not be called -- the fifth-and-counting instance of
    a guard matching its own rationale.
    """
    # Anchored on text unique to THIS handler, and bounded.
    #
    # Two earlier drafts both captured the wrong block and both produced a
    # confident, wrong failure message. `group.querySelectorAll('.pick-btn')`
    # occurs first in paintPickCard; `btn.addEventListener('click', ()=>{`
    # occurs first in the Week Board's filter handler. Each ran on until it
    # found a closing brace at the right indent, somewhere else entirely.
    #
    # The lesson this repo already records, one layer up: a matcher can drift
    # onto the wrong thing and still satisfy every assertion below it. So
    # anchor on something that occurs once, and assert the capture is the size
    # you expect before reading anything off it.
    start = source.find('const clicked = btn.dataset.team;')
    assert start != -1, (
        'the pick button handler is no longer findable. Re-anchor this guard '
        'rather than deleting it -- the defect it holds shipped once.')
    end = source.find('showUndoToast();', start)
    assert end != -1, 'the pick handler no longer ends by offering Undo'
    block = source[start:end]
    assert len(block) < 2000, (
        f'the handler capture is {len(block)} characters, so it is no longer '
        'just this handler. Re-anchor it before reading anything off it.')
    code = re.sub(r'/\*.*?\*/', '', block, flags=re.S)
    return re.sub(r'//.*', '', code)


def test_changing_a_pick_does_not_rebuild_the_grid(tap_handler):
    """The fix itself, stated as the thing that must not come back.

    `renderPicksGrid()` is the obvious call to reach for here and it is what
    was there. It is correct in every respect except that it throws away the
    element being tapped, which no test and no desktop browser will tell you.
    """
    assert 'renderPicksGrid' not in tap_handler, (
        'the pick handler calls renderPicksGrid() again. That replaces the '
        'whole grid via innerHTML and destroys the button under the finger, '
        'which is the iOS scroll-to-top this change fixes.')
    assert 'paintPickCard(' in tap_handler, (
        'the pick handler no longer repaints the card it changed, so the tap '
        'updates storage and nothing visible')


def test_the_totals_are_refreshed_with_the_picks_they_describe(tap_handler, source):
    """A missing argument here throws, and the throw is invisible.

    `refreshPickTotals()` with no argument reads `undefined[pid]` and raises.
    The paint had already happened, so the card looked right; what silently
    stopped was the record badge, the streak strip, and -- because the throw
    landed before it -- the Undo toast. Found only because the browser probe
    had a `pageerror` listener attached, which is why it has one.
    """
    calls = re.findall(r'refreshPickTotals\(([^)]*)\)', source)
    assert calls, 'nothing calls refreshPickTotals'
    empty = [c for c in calls if not c.strip()]
    assert not empty, (
        f'refreshPickTotals is called with no argument {len(empty)} time(s). '
        'It indexes the object it is given, so that raises -- after the card '
        'has already been painted, which makes the tap look like it worked.')


def test_one_function_paints_a_card_and_every_path_uses_it(source):
    """Three callers, one implementation.

    The full render, the tap and Undo must all reach a card's painted state
    the same way. Two paths is the `.game-card` failure this repo has already
    paid for: the same markup in two render functions, one edit landing on
    one of them, and a diff that looked complete either way.
    """
    assert re.search(r'function paintPickCard\(', source), 'paintPickCard is gone'
    # Three call sites: the full render's loop, the tap handler, and Undo.
    assert len(re.findall(r'paintPickCard\(', source)) >= 4, (
        'paintPickCard should be defined once and called from the full '
        'render, the tap handler and Undo. Fewer call sites means some path '
        'reaches a painted card another way.')
    # Comments stripped first. The undo block's own comment explains why it
    # does not call renderPicksGrid, so a raw substring test matches the
    # rationale and fails the healthy code -- the sixth time in this repo that
    # a guard has matched the sentence describing the thing it bans.
    undo = re.search(r'document\.getElementById\(.undo-action.\)\.onclick.*?\n  \};',
                     source, re.S)
    assert undo, 'the Undo handler is no longer findable'
    undo_code = re.sub(r'//.*', '', re.sub(r'/\*.*?\*/', '', undo.group(0), flags=re.S))
    assert 'renderPicksGrid' not in undo_code, (
        'Undo rebuilds the whole grid again. It is not under the finger, but '
        'a second way to paint a card is a second thing to keep in sync.')
    assert 'paintPickCard(' in undo_code, 'Undo no longer repaints its card'


def test_the_full_render_repaints_every_card_through_the_same_function(source):
    """paintPickCard must be the LAST writer, including on first paint.

    The card template still emits `selected`, so the first frame is never
    wrong. That makes the class a second opinion -- and the whole point of a
    single authority is that when two opinions disagree, a known one wins.
    Re-deriving every card after the innerHTML assignment is what makes that
    true rather than aspirational.
    """
    m = re.search(r"grid\.innerHTML = gamesList\.map.*?paintPickCard\(group, myPicks\[group\.dataset\.pid\]\)",
                  source, re.S)
    assert m, (
        'the full render no longer repaints each card through paintPickCard '
        'after building the markup, so the template string and the paint '
        'function are two independent opinions about which button is selected')


def test_the_agrees_sentence_is_written_by_the_paint_and_not_the_template(source):
    """One sentence, one place.

    It used to be built inline in the card template AND would have had to be
    rebuilt by the paint -- two copies of a sentence whose wording changes
    with sharedPicksView. The template now leaves an empty element for the
    paint to fill.
    """
    assert '<div class="pick-agrees"></div>' in source, (
        'the card template writes the Model B sentence itself again, so the '
        'surgical paint and the full render can disagree about its wording')
    fn = re.search(r'function pickAgreesText\(', source)
    assert fn, 'pickAgreesText is gone'


def test_a_pick_button_reports_its_state_to_assistive_technology(source):
    """Selection is a colour otherwise, and a colour is not an announcement.

    The button is a control with a persistent on/off state. Before this change
    the only signal was the `selected` class; a screen reader user had no way
    to know which team was picked.
    """
    fn = re.search(r'function paintPickCard\(.*?\n\}\n', source, re.S)
    assert fn, 'paintPickCard is gone'
    assert "setAttribute('aria-pressed'" in fn.group(0), (
        'the pick button no longer reports aria-pressed, so its selected '
        'state is conveyed by colour alone')
