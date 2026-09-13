"""The listbox that replaces a native <select> as the visible control.

`-webkit-appearance: none` is not an alternative and this file exists partly to
stop anyone concluding otherwise: it restyles the closed box and does nothing
to the picker iOS opens on tap. The only way to stop the system wheel is to
stop using a native select as the thing anyone sees.

What these guard is the CONTRACT, not the appearance. The select still owns the
value; the listbox reads it, renders it, and writes back through
`dispatchEvent('change')`. Every consumer keeps listening to the element it
already listened to, and the listbox cannot reach a state the select could not.
Break that and the control drifts from the page it drives, silently, with every
test green -- which is the failure this repo has shipped twice (the two
.game-card render paths, and the week stepper before it was shared).

Appearance is deliberately NOT asserted here beyond the token rule. Colours and
geometry are checked by rendering, because reading your own CSS back is not
verification.
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
def body(source):
    """enhanceSelect's body with comments stripped.

    Stripped for the reason CLAUDE.md records as having bitten five times: a
    guard whose rule names a forbidden string matches its own explanation. The
    comments inside enhanceSelect quote `getElementById` and `.week-select`
    precisely because they explain why neither belongs there.
    """
    # `\([^)]*\)`, not `\(sel\)`. Anchoring on the parameter list made this
    # fixture fail at SETUP the moment a mutation changed the signature, which
    # pytest reports as an ERROR rather than a FAILURE -- so the mutation
    # runner, which reads failures, said "the suite went red, Failures: none
    # reported. Another guard fired first" and blamed a healthy guard. Same
    # family as the tools here that read one number out of a multi-number
    # summary and invent a cause for the difference: a guard must fail on its
    # own assertion, not by making its fixture unusable.
    m = re.search(r'function enhanceSelect\([^)]*\)\{.*?\n\}\n', source, re.S)
    assert m, (
        'enhanceSelect is gone or was renamed. If the listbox moved, re-anchor '
        'this file rather than deleting it.')
    code = re.sub(r'/\*.*?\*/', '', m.group(0), flags=re.S)
    return re.sub(r'//.*', '', code)


def test_it_takes_an_element_and_never_an_id(body):
    """One implementation, driven once per select -- not a copy per page.

    #teamdive-select is the next consumer and is populated at runtime. If this
    function reaches for an id, it can only ever serve the Week Board and the
    second page needs its own copy, at which point the two are free to drift
    exactly as the two game-card render paths did.
    """
    for hardcoded in ('getElementById', "'sort-select'", '"sort-select"'):
        assert hardcoded not in body, (
            f'enhanceSelect names {hardcoded}, so it drives one specific '
            'select and a second page needs a copy of it.')


def test_the_select_still_owns_the_value(body):
    """The whole contract in one assertion.

    The listbox must write back by setting sel.value and dispatching change,
    never by calling a render function itself. A listbox that calls renderGames
    directly works perfectly until something else moves the select, at which
    point two controls disagree about the same state and neither is wrong.
    """
    assert re.search(r"sel\.value\s*=", body), (
        'enhanceSelect never assigns sel.value, so the native select is no '
        'longer the element that owns the selection')
    assert "dispatchEvent(new Event('change'))" in body, (
        'enhanceSelect does not dispatch change, so every existing listener on '
        'the select stops hearing about a choice made in the listbox')
    for direct in ('renderGames(', 'renderTeamDive(', 'renderPicks('):
        assert direct not in body, (
            f'enhanceSelect calls {direct}) directly. It must go through the '
            "select's own change event so it cannot take a path the select "
            'could not.')


def test_the_native_select_is_hidden_by_script_not_by_markup(source, body):
    """Progressive enhancement, and the one place this departs from the stepper.

    The week stepper hardcodes `visually-hidden` on its select, which is safe
    there because its arrows are static markup that exist without JavaScript.
    This list is built entirely by script. Hiding the select in the markup
    would leave a no-script reader with no control at all, so the class is
    applied after the list is successfully built.
    """
    m = re.search(r'<select id="sort-select"[^>]*>', source)
    assert m, 'the sort select is gone entirely'
    assert 'visually-hidden' not in m.group(0), (
        f'{m.group(0)} hides the select in the markup. With JavaScript off '
        'that leaves no sort control on the page at all -- the listbox that '
        'replaces it does not exist until a script builds it.')
    assert "classList.add('visually-hidden')" in body, (
        'enhanceSelect no longer hides the select it replaced, so the page '
        'shows two sort controls doing the same job -- and on a phone one of '
        'them is the iOS system wheel, which is the defect being fixed.')


def test_the_listbox_is_actually_wired_and_wired_late_enough(source):
    """A control nobody calls is markup, and order decides whether it works.

    This repo has shipped the written-tested-never-called shape before:
    src/collect_agent_log.py ran nowhere for weeks behind a full suite. The
    ordering half is subtler -- enhanceSelect writes back by dispatching
    change, so building it before the change listener exists produces a
    control whose clicks reach nothing while looking perfectly correct.
    """
    call = source.find('enhanceSelect(document.getElementById(')
    assert call != -1, (
        'nothing calls enhanceSelect, so the listbox is a function nobody runs '
        'and the page still shows the native select')
    listener = source.find("document.getElementById('sort-select').addEventListener('change'")
    assert listener != -1, 'the sort change listener is gone'
    assert listener < call, (
        'enhanceSelect runs before the change listener is attached. Choosing '
        'an option would dispatch change to nothing and the board would not '
        're-sort, while the control itself looked and behaved correctly.')


@pytest.mark.parametrize('attr', [
    'aria-haspopup', 'aria-expanded', 'aria-selected', 'aria-activedescendant',
])
def test_it_speaks_listbox_to_the_accessibility_tree(attr, body):
    """A div that looks like a select and announces nothing is worse than one.

    Enumerated rather than spot-checked: the reason this repo keeps relearning
    that prose naming a protection without naming its coverage is how a gap
    survives. aria-activedescendant is in the list because it is the one that
    carries keyboard POSITION, which is a different thing from the selection
    and the piece most often dropped.

    Asserts the attribute is SET, not merely mentioned. The first draft used
    `attr in body` and SURVIVED the mutation deleting the only line that sets
    aria-activedescendant -- because closeList still REMOVES it, so the string
    was present in the file while nothing ever published it. A
    presence-of-string check is not a presence-of-behaviour check, and the
    mutation corpus is what found the difference.
    """
    assert f"setAttribute('{attr}'" in body, (
        f'the listbox no longer sets {attr}, so a screen reader is told less '
        'about this control than the native select it replaced. Note that a '
        'removeAttribute elsewhere keeps the name in the file without anything '
        'ever setting it.')


def test_role_listbox_and_role_option_are_both_set(body):
    """Either one alone is a broken widget rather than a partial one."""
    assert "'role', 'listbox'" in body or '"role", "listbox"' in body, (
        'the list no longer has role=listbox')
    assert "'role', 'option'" in body or '"role", "option"' in body, (
        'the options no longer have role=option, so the list announces as a '
        'plain list and its items are not selectable to a screen reader')


def test_space_extends_a_search_in_flight_rather_than_selecting(body):
    """The bug that only appeared by running it.

    Every option on this control begins "Sort: ", so a Space that always
    selected made type-ahead unable to reach past the first word: typing
    "sort: b" chose option 0 and closed the list instead of finding "Sort:
    Biggest Model Disagreement". Space has to be a character while a search is
    in flight and a selection otherwise. No source-reading found this and no
    accessibility checklist names it; it came out of driving the control.
    """
    m = re.search(r"case ' ':(.*?)break;", body, re.S)
    assert m, "the listbox no longer handles Space at all"
    arm = m.group(1)
    assert 'typing()' in arm, (
        'the Space arm no longer consults whether a type-ahead search is in '
        'flight, so typing a space selects instead of extending the search. '
        'Every option here starts "Sort: ".')
    assert 'choose(' in arm, (
        'Space no longer selects when no search is in flight, which is the '
        'behaviour a listbox is required to have')


def test_the_listbox_styles_use_tokens_for_spacing_type_and_radius(source):
    """Stage 8's rule, applied to the component that replaces the worst offender.

    .week-select -- the control this replaces -- carries 12px, 9px 14px, 8px
    and a 160px minimum as literals, which is precisely the 31-ad-hoc-spacing,
    21-font-size audit Stage 8 exists to answer. A new component reintroducing
    them would be Stage 8 unpicking itself.

    Scoped to padding, font-size and border-radius on purpose. Widths and
    max-heights are not on those scales and inventing token names for a 6px
    dot would be the tidier-mess failure in the other direction.
    """
    css = re.search(r'/\* ---------- Listbox ----------.*?\n\n  /\* The week stepper',
                    source, re.S)
    assert css, 'the .lbx style block is no longer findable'
    block = re.sub(r'/\*.*?\*/', '', css.group(0), flags=re.S)

    literals = []
    for decl in re.finditer(r'(padding|font-size|border-radius)\s*:\s*([^;}]+)', block):
        if 'var(--' not in decl.group(2):
            literals.append(decl.group(0).strip())
    assert not literals, (
        f'the listbox styles hardcode {literals}. Stage 8 replaced these '
        'scales with tokens; a new component is where they come back.')


def test_the_chevron_inherits_its_colour(source):
    """The defect .week-select's chevron has, not repeated here.

    That control paints its arrow with `stroke='%238A93A8'` inside a data-URI
    -- a dark-theme grey baked into a URL, and therefore wrong in light mode.
    It is the same literal as teamColor()'s fallback. A chevron drawn as inline
    SVG with currentColor cannot have that defect in any theme.
    """
    # Anchored on `class="`, not on the bare class name. The first draft of
    # this matcher was r'lbx-chevron.*?</svg>', which found the CSS RULE
    # declaring the class -- there is no </svg> for 50,000 characters after it,
    # so the non-greedy match ran through half the file and swept up
    # .week-select's `%238A93A8` chevron, failing this test with the defect it
    # was written to prove absent. CLAUDE.md records this shape verbatim: a
    # regex anchored on a bare class name also matches the CSS that defines it.
    m = re.search(r'<svg class="lbx-chevron".*?</svg>', source, re.S)
    assert m, 'the listbox chevron is gone'
    # A matcher that drifts can still satisfy every assertion below it, so
    # bound the span rather than trusting non-greedy to stay local.
    assert len(m.group(0)) < 500, (
        f'the chevron match ran to {len(m.group(0))} characters, so it is no '
        'longer this element. Re-anchor it before reading anything off it.')
    assert 'currentColor' in m.group(0), (
        'the listbox chevron no longer inherits its colour')
    assert not re.search(r'%23[0-9A-Fa-f]{6}|#[0-9A-Fa-f]{6}', m.group(0)), (
        'the listbox chevron has a hardcoded hex, which is how .week-select '
        'ended up with a dark-theme grey that is wrong in light mode')
