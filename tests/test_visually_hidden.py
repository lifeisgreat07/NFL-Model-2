"""The .visually-hidden utility, and the one property that defeats it.

Reported from a phone on 2026-09-15: choosing a sort on the Week Board left
the whole page zoomed out, cards no longer fitting. The listbox was innocent.

`.visually-hidden` sets `width:1px`, and `.week-select` -- worn by every
select the listbox and the week stepper hide -- sets `min-width:160px`.
**min-width beats width.** So the "hidden" select stayed a 160px-wide box.
`clip` and `clip-path` stop it being painted; neither removes it from the
page's scrollable overflow area, so the box still widens the document.

It is absolutely positioned with no `left`/`top`, which puts it at its static
position: immediately after the button inside `.lbx`. On the Week Board at a
430px viewport the filter row does not wrap, the sort control sits at x=191,
and the phantom select ran from 373 to 533. Measured at that width, against
the shipped page:

    documentElement.scrollWidth   533   (viewport 430)
    .bottom-nav width             533   (position:fixed, stretched with it)
    .game-card width              351   (398 once the overflow is gone)

A phone with `width=device-width` shrink-fits a layout wider than the
viewport, which is the reported zoom-out. It is width-dependent -- at 375px
the row wraps, the control drops to x=12, and nothing overflows -- which is
why it looked intermittent and why it never showed on a desktop width.

These guards are source-level because the failure is in a stylesheet and the
suite has no browser. That is a real limit: they assert the utility neutralizes
the properties that can defeat it, not that the page stops overflowing. The
rendered measurement above is what proves the fix, and it belongs in the PR
body rather than here.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'src' / 'dashboard_template.html'


@pytest.fixture(scope='module')
def rule():
    """The .visually-hidden declaration block.

    Anchored on the selector at a line start with its brace, so it cannot
    match a mention of the class name inside a comment or a JS string -- the
    class is named in both, and a bare-identifier matcher finding whichever
    occurrence comes first is a defect this repo has shipped three times.
    """
    src = TEMPLATE.read_text(encoding='utf-8')
    m = re.search(r'\n\s*\.visually-hidden\s*\{(.*?)\}', src, re.S)
    assert m, (
        '.visually-hidden is gone or was renamed. Every select the listbox '
        'and the week stepper hide depends on it; re-anchor this file rather '
        'than deleting it.')
    assert len(m.group(1)) < 600, (
        f'the .visually-hidden match ran to {len(m.group(1))} characters, so '
        'it is no longer one rule. Re-anchor it before reading anything off it.')
    return m.group(1)


@pytest.mark.parametrize('prop', ['min-width', 'min-height'])
def test_it_neutralises_the_minimums_that_outrank_its_own_size(rule, prop):
    """width:1px is a request; min-width is a floor, and the floor wins.

    Both axes, not just the one that bit: `.week-select` sets min-width today
    and the next component to be hidden this way may set min-height. A guard
    that covers only the reported axis is the "prose names a protection but
    never its coverage" shape, and the cost of the second axis is one word.
    """
    m = re.search(r'\b%s\s*:\s*([^;}]+)' % re.escape(prop), rule)
    assert m, (
        f'.visually-hidden does not set {prop}, so any class it is combined '
        f'with can set a {prop} that outranks its width/height and the '
        'element keeps a real box. That box is clipped, not removed: it still '
        'widens the document, and a phone shrink-fits the page to match.')
    value = m.group(1).strip()
    assert re.fullmatch(r'0(\w*)?', value), (
        f'.visually-hidden sets {prop}:{value}, which is still a floor. It '
        'has to be 0 for width:1px/height:1px to be what the element is.')


def test_the_size_it_asks_for_is_still_one_pixel(rule):
    """The neutralisation must not become the whole rule.

    Setting min-width:0 and dropping width:1px leaves the element sized by its
    content, which is worse than the defect being fixed: a 160px select
    becomes an auto-width select. The pair only works together.
    """
    for prop in ('width', 'height'):
        m = re.search(r'(?<!-)\b%s\s*:\s*([^;}]+)' % prop, rule)
        assert m, f'.visually-hidden no longer sets {prop}'
        assert m.group(1).strip() == '1px', (
            f'.visually-hidden sets {prop}:{m.group(1).strip()}. It is 1px so '
            'the element keeps a box in the accessibility tree without '
            'occupying space; changing it changes what the utility means.')


def test_it_is_still_clipped_and_still_in_the_accessibility_tree(rule):
    """The fix must not be "use display:none", which is the obvious tidy-up.

    display:none removes the element from the accessibility tree along with
    the picture. These selects are the accessible control and the single
    source of truth for the value -- the listbox and the stepper only read and
    write them -- so hiding them that way would silently delete the control a
    screen-reader user operates while fixing a layout bug for everyone else.
    """
    assert 'position:absolute' in rule.replace(' ', ''), (
        '.visually-hidden is no longer taken out of flow')
    assert 'clip-path' in rule, '.visually-hidden no longer clips its painting'
    assert 'display:none' not in rule.replace(' ', ''), (
        '.visually-hidden now uses display:none, which removes the select '
        'from the accessibility tree. The hidden select IS the accessible '
        'control; the listbox is a div that reads and writes it.')
