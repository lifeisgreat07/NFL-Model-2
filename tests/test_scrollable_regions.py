"""A box that scrolls sideways can be reached, and scrolled, from the keyboard.

Stage 12 (CLAUDE.md). The first CI run of the browser checks found axe's
scrollable-region-focusable on five boxes at 390px: the wide tables on
Accuracy, Model Lab and Method, and the ridge formula. Each scrolled
sideways and held no control of its own, so a keyboard user saw the first
columns and could never reach the rest (WCAG 2.1.1).

setScrollStop() now makes a box that scrolls a named, focusable region and
takes that back when the box fits. Its bookkeeping, and the names it gives,
are executed under node against a fake DOM (tests/scroll_stop_harness.js);
the wiring into fitTables() and the focus ring are held by source guards,
because they need a browser -- which is what the browser checks are for.

Run with: pytest tests/test_scrollable_regions.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.pipeline.template_parts import JOINED_TEMPLATE  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = JOINED_TEMPLATE
HARNESS = ROOT / 'tests' / 'scroll_stop_harness.js'
NODE = shutil.which('node')
ADDED = {'tabindex': '0', 'role': 'region'}


@pytest.fixture(scope='module')
def source():
    return TEMPLATE.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def run(source):
    if not NODE:
        pytest.skip('node not available')
    code = re.search(r'function headingBefore\(.*?\nfunction setScrollStop\(.*?\n\}\n', source, re.S)
    assert code, 'the scroll-stop functions are not findable -- re-anchor this guard'
    r = subprocess.run([NODE, str(HARNESS)], input=code.group(0),
                       capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_a_box_that_scrolls_becomes_a_named_tab_stop(run):
    a = run['scrolls']
    assert {k: a.get(k) for k in ADDED} == ADDED
    assert a['aria-label'] == 'Table: Backtest Results by season, scrolls sideways'
    assert sorted(a['data-scroll-stop'].split()) == ['aria-label', 'role', 'tabindex']
    assert run['scrolls_twice'] == a, 'running it again on the same box changed it'


def test_a_box_that_fits_leaves_the_tab_order(run):
    assert run['fits_again'] == {}, (
        f'a box that fits kept {run["fits_again"]}: a Tab stop that does nothing')


def test_markup_attributes_survive_the_box_fitting(run):
    """Only what setScrollStop added is taken away."""
    s = run['markup_scrolls']
    assert s['role'] == 'region' and s['aria-label'] == 'Set in the markup'
    assert s['tabindex'] == '0' and s['data-scroll-stop'] == 'tabindex'
    assert run['markup_fits'] == {'role': 'region', 'aria-label': 'Set in the markup'}
    assert run['never_marked'] == {'tabindex': '0'}, (
        'a tabindex the function never added was removed')


def test_a_box_with_its_own_control_gets_no_extra_stop(run):
    assert run['has_control'] == {}, 'a box already reachable through its own control got a second stop'
    assert run['gains_control'] == {}, 'a stop was kept after the box gained a control of its own'
    assert run['minus_one_is_not_a_control']['tabindex'] == '0', (
        'a tabindex="-1" element was counted as a way in, but Tab never lands on it')


def test_the_region_is_named_after_the_section_it_sits_in(run):
    assert run['label_formula'] == 'Formula: Rating System, scrolls sideways'
    assert run['label_caption'] == 'Table: Bins, scrolls sideways'
    assert run['label_ancestor_sibling'] == 'Table: Page title, scrolls sideways'
    assert run['label_none'] == 'Table, scrolls sideways', 'the name came from another page'


def test_an_explicit_label_wins(run):
    """Model Lab's experiment log sits straight after the reliability section."""
    assert run['label_given'] == 'Table: Experiment log, scrolls sideways'


def test_a_heading_inside_a_nested_note_is_not_the_name(run):
    assert run['label_nested_note'] == 'Table: Are these percentages honest?, scrolls sideways'


def test_fit_tables_marks_every_box_that_scrolls(source):
    body = re.search(r'function fitTables\(\)\{.*?\n\}\n', source, re.S)
    assert body, 'fitTables is gone -- re-anchor this guard'
    code = body.group(0)
    assert re.search(r"querySelectorAll\('\.table-wrap'\).*?setScrollStop\(w, !fits\)", code, re.S), (
        'table wrappers are no longer made reachable when they scroll')
    assert re.search(r"querySelectorAll\('\.formula'\).*?setScrollStop\(f, f\.scrollWidth > f\.clientWidth\)",
                     code, re.S), 'the formula block is no longer made reachable when it scrolls'


def test_a_scroll_stop_shows_focus(source):
    css = re.sub(r'/\*.*?\*/', '', source.split('</style>')[0], flags=re.S)
    rule = re.search(r'\[data-scroll-stop\]:focus-visible\{([^}]*)\}', css)
    assert rule and re.search(r'outline:\s*2px solid', rule.group(1)), (
        'a focused scroll stop has no visible ring (WCAG 2.4.7)')


def test_the_experiment_log_carries_its_name(source):
    # Anchored on Model Lab's section rather than on what sits right before
    # the table: the decision chips (Stage 18) came in between, and the next
    # item moves the reliability diagram below it.
    section = source[source.index('<section class="page" id="page-modellab">'):]
    section = section[:section.index('</section>')]
    assert section.count('<div class="table-wrap" data-scroll-label="Experiment log">') == 1
