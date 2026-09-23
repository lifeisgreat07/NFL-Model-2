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

    The week stepper hardcodes `visually-hidden` on its select; this list is
    built entirely by script, so the class is applied after the list is
    successfully built and the select ships visible.

    What that buys is ORDERING, not reach. The select cannot be hidden unless
    the control replacing it exists, so a script that dies between rendering
    the page and reaching the enhanceSelect call leaves a working native
    select instead of nothing.

    Until 2026-09-21 this docstring gave the reason as a no-script reader who
    would otherwise have no control. Checked on the built page, and false:
    with scripts off only #page-ratings is active, every nav control is an
    inert <button> with no href, and there is no :target rule or anchor
    reaching a page, so this select's page cannot be opened at all. The guard
    is kept -- hidden by script rather than by markup is still the right
    default -- with the honest reason attached.
    """
    m = re.search(r'<select id="sort-select"[^>]*>', source)
    assert m, 'the sort select is gone entirely'
    assert 'visually-hidden' not in m.group(0), (
        f'{m.group(0)} hides the select in the markup, so it is hidden before '
        'the listbox that replaces it is built. Hide it in enhanceSelect, '
        'after the list exists, so the two can never be out of step.')
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

    Two options share a first word -- "Biggest Model Disagreement" and
    "Biggest Spread First" -- so the space is the keystroke that tells them
    apart. Measured on the built page: typing "biggest s" walks the active
    option to "Biggest Spread First" with the list open and nothing chosen;
    with the Space arm made unconditional the space chose "Biggest Model
    Disagreement" and closed the list. Space has to be a character while a
    search is in flight and a selection otherwise. No source-reading found
    this and no accessibility checklist names it; it came out of driving the
    control.

    The example was re-measured when the "Sort: " prefix was dropped from the
    labels. It used to rest on every option sharing that prefix. The prefix is
    gone; the requirement is not, because two options still share a word.
    """
    m = re.search(r"case ' ':(.*?)break;", body, re.S)
    assert m, "the listbox no longer handles Space at all"
    arm = m.group(1)
    assert 'typing()' in arm, (
        'the Space arm no longer consults whether a type-ahead search is in '
        'flight, so typing a space selects instead of extending the search. '
        '"Biggest Model Disagreement" and "Biggest Spread First" share a '
        'first word, so the space is what tells them apart.')
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
    """The defect .week-select's chevron would have if anyone could see it.

    That control declares its arrow with `stroke='%238A93A8'` inside a
    data-URI -- a dark-theme grey baked into a URL, the same literal as
    teamColor()'s fallback. Until 2026-09-21 this docstring called it wrong in
    light mode. It cannot be: every element wearing .week-select is clipped to
    1x1 by .visually-hidden, so that chevron paints in no theme at all.

    The rule still belongs here, and only here. This chevron is the one a
    reader actually sees, so a hardcoded hex in it would be the live version
    of a defect the dead one merely resembles. Drawn as inline SVG with
    currentColor, it cannot acquire one.
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
        'ended up with a dark-theme grey baked into a data-URI -- harmless '
        'there only because that control never paints, and not harmless here')


# ---------------------------------------------------------------------------
# The second consumer: #teamdive-select.
#
# enhanceSelect takes an element rather than an id so that this page could use
# the same function instead of a copy of it -- the .game-card lesson, where two
# render paths drifted because one edit landed on one of them and the diff
# looked complete. These guards are what makes that a fact rather than an
# intention: the test above proves the function COULD serve a second select,
# and proves nothing about whether one ever does.
#
# This select differs from #sort-select in the way that matters: its options do
# not exist in the markup. renderTeamDive() writes them at runtime and uses
# `select.options.length === 0` as its sentinel for "not populated yet", so the
# listbox is built against a select that is empty when the page loads and has
# to be rebuilt when it stops being.
# ---------------------------------------------------------------------------


@pytest.fixture(scope='module')
def teamdive(source):
    """renderTeamDive's body with comments stripped.

    Anchored on `\\([^)]*\\)` rather than `\\(\\)` for the reason the
    enhanceSelect fixture above records: anchoring on a parameter list makes
    this fixture fail at SETUP when a mutation changes the signature, pytest
    calls that an ERROR rather than a FAILURE, and the mutation runner -- which
    reads failures -- reports WRONG-GUARD against a guard that is perfectly
    healthy.
    """
    m = re.search(r'function renderTeamDive\([^)]*\)\{.*?\n\}\n', source, re.S)
    assert m, (
        'renderTeamDive is gone or was renamed. If the Team Deep-Dive moved, '
        're-anchor this file rather than deleting it.')
    # A matcher that drifts can still satisfy every assertion below it. The
    # function is ~45 lines; anything an order of magnitude past that is a
    # match that ran on into the rest of the file.
    assert len(m.group(0)) < 4000, (
        f'the renderTeamDive match ran to {len(m.group(0))} characters, so it '
        'is no longer just that function. Re-anchor it before reading '
        'anything off it.')
    code = re.sub(r'/\*.*?\*/', '', m.group(0), flags=re.S)
    return re.sub(r'//.*', '', code)


def test_the_team_select_is_enhanced_at_all(teamdive):
    """Otherwise this page is the one still showing the iOS system wheel.

    The written-tested-never-called shape has shipped here before
    (src/collect_agent_log.py ran nowhere for weeks behind a full suite), and
    a shared function with one caller is the same shape wearing a better name.
    """
    assert 'enhanceSelect(' in teamdive, (
        'renderTeamDive never calls enhanceSelect, so #teamdive-select is '
        'still a native select -- and on a phone that is the system wheel '
        'this component exists to replace.')


def test_the_team_listbox_is_built_after_its_change_listener(teamdive):
    """Order decides whether the control does anything, and looks fine either way.

    enhanceSelect writes back by dispatching change on the select. Build it
    before renderTeamDive subscribes and choosing a team dispatches into
    nothing: the button updates, the list closes, and the page below it keeps
    showing the previous team. Every test that reads the source would still
    pass. This is the same assertion the Week Board's call site already
    carries, made against the call site that adds its listener at runtime.
    """
    listener = teamdive.find("addEventListener('change', renderTeamDive)")
    call = teamdive.find('enhanceSelect(')
    assert listener != -1, (
        'renderTeamDive no longer subscribes to its own select, so choosing a '
        'team changes nothing')
    assert call != -1, 'renderTeamDive never calls enhanceSelect'
    assert listener < call, (
        'enhanceSelect runs before the change listener is attached. Choosing '
        'a team would dispatch change to nothing and the page would keep '
        'showing the previous team, while the control itself looked correct.')


def test_every_write_to_the_options_reaches_the_listbox(teamdive):
    """The refresh() half of the contract, stated as coverage rather than a case.

    enhanceSelect renders the select's options once, at build time. This
    select has none then, and renderTeamDive writes them later -- so every
    write to select.innerHTML is a moment the listbox is showing something the
    select no longer says. CLAUDE.md records the shape this is written against:
    prose naming a protection but never its coverage is how a gap survives, so
    this enumerates the writes instead of checking the one anybody remembered.

    Segmented on the writes themselves rather than a fixed-size window, so it
    cannot be satisfied by a refresh that belongs to a different branch.
    """
    writes = [m.start() for m in re.finditer(r'select\.innerHTML\s*=', teamdive)]
    assert writes, 'renderTeamDive no longer writes the options at all'
    bounds = writes + [len(teamdive)]
    for n, start in enumerate(writes):
        segment = teamdive[start:bounds[n + 1]]
        assert re.search(r'enhanceSelect\(|refresh\(\)', segment), (
            'a write to select.innerHTML in renderTeamDive is not followed by '
            'enhanceSelect() or a refresh(), so the listbox keeps rendering '
            'the options the select used to have. The offending write begins: '
            + repr(segment[:80]))


def test_the_no_data_branch_empties_the_listbox_too(teamdive):
    """The specific case the coverage test above exists to keep honest.

    With no team history the select is emptied and the page shows an empty
    state -- but the listbox button is a div holding whatever label it last
    rendered. Left alone it sits above an empty-state message still naming a
    team, which is the "correct arithmetic on absent data" failure in its
    presentational form: nothing errors and the page lies.
    """
    branch = re.search(r'No team history in this build.*?return;', teamdive, re.S)
    assert branch, 'the no-data branch of renderTeamDive is gone'
    assert re.search(r'refresh\(\)', branch.group(0)), (
        'the no-data branch empties the select without refreshing the '
        'listbox, so the button goes on naming a team the select no longer '
        'offers, directly above a message saying there is no data')


def test_the_population_sentinel_is_still_the_option_count(teamdive):
    """Enhancement must not become the thing that decides whether to populate.

    `select.options.length === 0` asks the select, which is the element that
    owns the value. Swapping it for a flag about the listbox -- dataset.lbx, a
    stored handle, anything -- makes populating conditional on a control that
    is meant to be invisible to everything downstream of it, and the page then
    has two sources of truth for whether it has teams.
    """
    assert re.search(r'select\.options\.length\s*===\s*0', teamdive), (
        'the runtime population is no longer gated on select.options.length, '
        'so whether the page has teams is now decided by something other than '
        'the select that owns them')


def test_the_team_select_ships_visible_like_the_sort_select(source):
    """Progressive enhancement, asserted per select rather than per component.

    The same reasoning as the sort select above, and it is a separate test
    because it is a separate element: a page can hide one in the markup and
    not the other, and the component-level guard would not notice.
    """
    m = re.search(r'<select id="teamdive-select"[^>]*>', source)
    assert m, 'the team select is gone entirely'
    assert 'visually-hidden' not in m.group(0), (
        f'{m.group(0)} hides the select in the markup. Its options are '
        'written by script and the listbox that replaces it is built by '
        'script, so hiding it here hides it before either one exists.')


def test_the_team_select_carries_an_accessible_name(source):
    """A listbox button with no name announces as "button", and nothing else.

    enhanceSelect copies the select's aria-label onto both the button and the
    list, which is the only name either can have: there is no visible <label>
    anywhere near this control, and the <h2> two elements up is the page
    title, not a label for the select. A native select with no name is already
    a defect; replacing it with a custom widget that has no name is the same
    defect in a control a screen reader knows less about.
    """
    m = re.search(r'<select id="teamdive-select"[^>]*>', source)
    assert m, 'the team select is gone entirely'
    assert re.search(r'aria-label="[^"]+"', m.group(0)), (
        f'{m.group(0)} has no aria-label, so enhanceSelect has nothing to '
        'name the listbox button with and the control announces as an '
        'unlabelled button')


def test_the_listbox_handle_is_kept_and_is_the_one_refreshed(teamdive):
    """Written because a mutation walked straight through every guard above it.

    Dropping the assignment -- `enhanceSelect(select);` instead of
    `handle = enhanceSelect(select);` -- leaves the listbox built and correct
    on load, leaves the literal `refresh()` sitting in the no-data branch for
    the branch test to find, and leaves `enhanceSelect(` in place for the
    coverage test to find. Every listbox test passed and the refresh could
    never run, because there was no longer anything to call it on.

    So this ties the two halves together by name rather than checking that
    each exists somewhere: whatever the handle is called, that is what has to
    be refreshed. Found by asking what a mutation of this code would look
    like, which is the whole argument for the corpus.
    """
    m = re.search(r'(\w+)\s*=\s*enhanceSelect\(', teamdive)
    assert m, (
        'renderTeamDive discards what enhanceSelect returns, so nothing can '
        'call refresh() and the listbox silently stops tracking the select '
        'the moment its options change')
    handle = m.group(1)
    assert f'{handle}.refresh()' in teamdive, (
        f'the handle is stored as {handle} but nothing calls '
        f'{handle}.refresh(), so the stored handle is decoration and the '
        'listbox and the select can disagree')


# ---------------------------------------------------------------------------
# The button's width, which is a layout property of the row around it.
#
# Measured at a 430px mobile-emulated viewport before this: the Week Board's
# sort button ran 183px wearing "Sort: First Game to Last" and 248px wearing
# "Sort: Biggest Model Disagreement", on a row with 398px of content width.
# The row therefore rearranged itself when the reader changed the sort -- at
# 430 the control dropped off the stepper's line and down beside Print / PDF,
# and at 390 and below it went to three lines. Two changes answer it: the
# labels lost a "Sort: " prefix that said nothing the aria-label and the
# chevron did not, and the button is now frozen at the width of its longest
# label. Measured after: 218px for all six options at 390 and at 430, two
# lines at both, and no horizontal overflow with the list open or closed.
# ---------------------------------------------------------------------------


def test_the_sort_labels_carry_no_redundant_prefix(source):
    """The copy half of the width fix.

    Worth a guard rather than a comment because it is the kind of edit a
    future session makes back without knowing it cost 65px of a 398px row.
    """
    m = re.search(r'<select id="sort-select"[^>]*>(.*?)</select>', source, re.S)
    assert m, 'the sort select is gone'
    labels = re.findall(r'<option value="[a-z_]+">([^<]+)</option>', m.group(1))
    assert len(labels) >= 6, f'expected the six sort options, found {labels}'
    offenders = [label for label in labels if label.lower().startswith('sort:')]
    assert not offenders, (
        f'{offenders} carry a "Sort: " prefix again. It costs width on the '
        'one row that cannot afford it, and the aria-label, the chevron and '
        "the control's position already say what it is.")


def test_the_sort_control_asks_to_be_frozen_at_its_widest_label(source):
    """Opt-in, and the opt-in has to still be on the element.

    #teamdive-select is the other consumer of enhanceSelect() and this was
    never a change to that page, so the behaviour is requested per control
    rather than applied to all of them. A missing attribute is silent: the
    button goes back to sizing itself and nothing fails.
    """
    m = re.search(r'<select id="sort-select"[^>]*>', source)
    assert m, 'the sort select is gone'
    assert 'data-lbx-fit="widest"' in m.group(0), (
        'the sort control no longer asks for a frozen width, so choosing a '
        'longer option moves the filter row around again')


def test_the_frozen_width_is_a_variable_with_the_floor_as_its_fallback(source):
    """min-width:var(--lbx-fit, 160px), not a literal.

    A hardcoded pixel width would be Stage 8 unpicking itself and would be
    wrong the first time anyone edits a label. The fallback matters
    separately: a control that does not opt in, or a page with no JavaScript,
    must keep the 160px floor rather than collapsing to its content.
    """
    m = re.search(r'\.lbx-btn\{(.*?)\n  \}', source, re.S)
    assert m, '.lbx-btn is gone from the stylesheet'
    rule = m.group(1).replace(' ', '')
    assert 'min-width:var(--lbx-fit,160px)' in rule, (
        '.lbx-btn no longer takes its minimum from --lbx-fit with the 160px '
        'floor as the fallback')


def test_the_width_is_measured_on_a_clone_rather_than_by_wearing_each_label(body):
    """Six changes of selectedIndex would be six full board re-renders.

    sel.dispatchEvent('change') is what the Week Board listens to, so the
    obvious implementation -- try each option, read the width -- re-renders
    every game card six times on load to answer a question about text width.
    """
    m = re.search(r'function fitWidest\(\)\{(.*?)\n  \}', body, re.S)
    assert m, 'fitWidest() is gone, so the button sizes itself again'
    fn = m.group(1)
    assert 'cloneNode' in fn, (
        'fitWidest() no longer measures a detached clone')
    assert 'selectedIndex' not in fn, (
        'fitWidest() sets selectedIndex, which dispatches change and re-renders '
        'the whole board once per option just to measure text')
    assert "dataset.lbxFit !== 'widest'" in fn, (
        'fitWidest() no longer checks the opt-in, so it now freezes every '
        'listbox on the page including the Team Deep-Dive one')


def test_the_width_is_measured_again_once_the_webfont_has_landed(body):
    """The trap this entire change came out of.

    Every number here is a sum of text widths. The first pass runs before
    Plus Jakarta Sans has arrived and measures the fallback face: 205px
    against the webfont's 218px, measured in Chromium on the built page. A
    width frozen in the wrong typeface is the same class of wrong as a figure
    quoted from the wrong command.
    """
    assert 'document.fonts.ready.then(fitWidest)' in body, (
        'the width is no longer re-measured after the webfont loads, so it is '
        'frozen at whatever the fallback face happened to measure')
