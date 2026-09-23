""".filter-btn is a shared pill style, not a Week Board filter.

Nine elements on the page wear `.filter-btn` and only three of them are
filters. The other six are "Got it" on the onboarding banner and, on My Picks,
"Copy these into my log", "Back to my picks", "Copy Share Link", "Export My
Picks" and "Import My Picks".

The Week Board's filter handler selected all nine. Tapping Export My Picks
therefore stripped `.active` off All Games, painted Export in the accent as
though it were a filter, and set `currentFilter` to `undefined` -- which falls
through the final `return true` in the games filter, so the board re-rendered
with every game showing and no pill marked. Nothing errored and no test was
red. Measured in headless Chromium against the built page: `.active` went from
["All Games"] to ["Export My Picks"].

CLAUDE.md carried this symptom as "a :focus state persisting after touch",
which it is not -- it reproduces under a programmatic click with no touch
involved, and a focus ring cannot *remove* a class from a different element.
That correction is the reason this file exists rather than a one-line patch.

The durable shape: **a handler's selector must agree with the data it reads.**
This one reads `btn.dataset.filter`, so it must select `[data-filter]`. A
selector matching a shared style class is matching appearance, and appearance
is the thing most likely to be reused somewhere the behaviour makes no sense.

STAGE 10 (2026-09-23) removed the cause as well as the symptom. The button
component split look from behaviour: `.btn-chip` is now the pill LOOK, worn
by the three filters and by Model Lab's series toggles, and `.filter-btn` is
a hook worn only by real filters. The six actions wear `.btn`. So the hazard
this file describes has moved rather than vanished -- a shared pill look
still exists, it is just called `.btn-chip` -- and the vacuity guard below
follows it there.
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
def handler(source):
    """The filter handler block, comments stripped.

    Comments are removed because this file's own explanation quotes the very
    selector it bans -- the fifth occurrence in this repo of a guard matching
    its own docstring, which is recorded in CLAUDE.md as a recurring shape.
    """
    block = re.search(
        r"document\.querySelectorAll\([^)]*filter-btn[^)]*\)\.forEach\(btn=>\{.*?\n\}\);",
        source, re.S)
    assert block, (
        'the Week Board filter handler is no longer findable. If it was '
        'renamed or restructured, re-anchor this guard rather than deleting '
        'it -- the defect it holds shipped silently once already.')
    code = re.sub(r'/\*.*?\*/', '', block.group(0), flags=re.S)
    return re.sub(r'//.*', '', code)


def test_the_handler_selects_on_the_attribute_it_reads(handler):
    """Every selector in the handler names [data-filter], not a style class.

    Both of them, stated separately, because fixing only the attach selector
    leaves the clear selector stripping .active off buttons on another page --
    a half-fix that looks right in the diff and still breaks the Week Board.
    """
    selectors = re.findall(r'querySelectorAll\(([^)]*)\)', handler)
    assert len(selectors) == 2, (
        f'expected two querySelectorAll calls in the filter handler, found '
        f'{len(selectors)}: {selectors}. If the handler grew a third, this '
        'guard needs to cover it too.')
    for sel in selectors:
        assert '[data-filter]' in sel, (
            f'the filter handler selects {sel.strip()}, which matches a shared '
            'pill style rather than the attribute the handler reads. Six '
            'buttons wear .filter-btn and are not filters; this is how Export '
            'My Picks got painted as an active filter.')
        assert '#filter-row' in sel, (
            f'the filter handler selects {sel.strip()} page-wide. Scope it to '
            '#filter-row so a future [data-filter] elsewhere cannot silently '
            'join the Week Board filter group.')


def _elements_wearing(source, cls):
    return re.findall(
        r'<(?:button|a)[^>]*class="[^"]*\b' + re.escape(cls) + r'\b[^"]*"[^>]*>', source)


def test_there_really_are_pills_that_are_not_filters(source):
    """Keeps the guard above meaningful rather than vacuously true.

    Until Stage 10 the shared pill look was `.filter-btn` itself, worn by six
    buttons that were not filters. It is now `.btn-chip`, and the non-filters
    wearing it are Model Lab's series toggles. If that ever stops being true
    the scoping rule would still pass while protecting nothing, so assert the
    hazard still exists; if it genuinely does not, this failing is the prompt
    to re-read whether the scoping is still needed.
    """
    pills = _elements_wearing(source, 'btn-chip')
    assert pills, 'no .btn-chip elements found at all -- re-anchor this guard'

    non_filters = [p for p in pills if 'data-filter=' not in p]
    assert non_filters, (
        'every .btn-chip now carries data-filter, so the scoping guard above '
        'protects nothing. Either a non-filter pill was removed (fine -- '
        'reconsider this file) or the class was renamed (re-anchor it).')


def test_only_real_filters_wear_the_filter_hook(source):
    """`.filter-btn` is a behaviour hook now, not a look. An action button
    wearing it is the #68 defect waiting for the next unscoped selector."""
    hooks = _elements_wearing(source, 'filter-btn')
    assert len(hooks) >= 3, f'expected the three Week Board filters, found {len(hooks)}'
    strays = [h for h in hooks if 'data-filter=' not in h]
    assert not strays, (
        f'.filter-btn is worn by buttons that are not filters: {strays}. '
        'Give an action .btn; .filter-btn is only for data-filter pills.')


def test_no_data_filter_button_lives_outside_the_filter_row(source):
    """Stated as a set relation so the next button added is covered.

    The same shape as test_every_nav_on_the_page_agrees_on_which_pages_exist:
    the point is not to list today's buttons but to make tomorrow's obey the
    rule without anyone remembering this file exists.
    """
    row = re.search(r'<div class="filter-row" id="filter-row">.*?</div>',
                    source, re.S)
    assert row, 'the Week Board #filter-row is gone -- re-anchor this guard'
    start, end = row.span()

    # Positions, not a set of values. The first draft of this test compared
    # set(values inside) against set(values anywhere) and a mutation adding a
    # second data-filter="flagged" on My Picks SURVIVED it: the duplicate value
    # was already inside the row, so the set difference was empty while the
    # stray button sat there wearing the active style and wired to nothing.
    # That is CLAUDE.md's "a count assertion validates the number of matches,
    # not their identity", one layer up -- caught by the mutation corpus and by
    # nothing else, which is the argument for running it before opening a PR.
    stray = [m.group(0) for m in re.finditer(r'data-filter="[^"]+"', source)
             if not (start <= m.start() < end)]
    assert not stray, (
        f'data-filter is used outside #filter-row: {stray}. The Week Board '
        'handler is scoped to that row, so these buttons look like filters, '
        'wear the active style, and do nothing -- or worse, are meant to be '
        'filters and are silently unwired.')
