"""A select hidden behind its visible control is not in the Tab order.

Stage 12 (CLAUDE.md). The Week Board and My Picks each keep a native week
<select>, clipped to 1x1 by .visually-hidden, as the element that owns which
week is selected; the week stepper beside it is what people see and use. The
select stayed focusable, so on both pages at every width Tab landed on a 1x1
box and a keyboard user's focus vanished for one stop. Nothing in the suite
could see it; the browser checker built for Stage 12 found it on its first
run against the real page.

enhanceSelect() already took the sort and team selects out of the Tab order
when it hid them. The two hidden in the markup were missed. The rule is
stated over the class, so a third hidden select is covered too.

Run with: pytest tests/test_hidden_select_tab_order.py -v
"""
import re

import pytest

from src.core.template_parts import JOINED_TEMPLATE

TEMPLATE = JOINED_TEMPLATE


@pytest.fixture(scope='module')
def source():
    src = TEMPLATE.read_text(encoding='utf-8')
    return re.sub(r'<!--.*?-->', '', src, flags=re.S)


def hidden_selects(src):
    return [t for t in re.findall(r'<select\b[^>]*>', src)
            if re.search(r'class="[^"]*\bvisually-hidden\b', t)]


def test_the_scan_finds_the_two_hidden_week_selects(source):
    ids = {re.search(r'id="([^"]+)"', t).group(1) for t in hidden_selects(source)}
    assert {'week-select', 'picks-week-select'} <= ids, (
        f'the hidden week selects were not found ({sorted(ids)}) -- this guard is looking at nothing')


def test_every_select_hidden_in_the_markup_is_out_of_the_tab_order(source):
    focusable = [t for t in hidden_selects(source) if 'tabindex="-1"' not in t]
    assert not focusable, (
        f'a visually hidden select can still take focus: {focusable}. Tab lands '
        'on a 1x1 box nobody can see.')


def test_the_selects_hidden_by_script_are_taken_out_too(source):
    """enhanceSelect() hides the sort and team selects at runtime."""
    body = re.search(r'function enhanceSelect\(.*?\n\}\n', source, re.S)
    assert body, 'enhanceSelect is gone -- re-anchor this guard'
    hide = body.group(0).find("classList.add('visually-hidden')")
    out = body.group(0).find("setAttribute('tabindex', '-1')")
    assert hide != -1 and out != -1, (
        'enhanceSelect hides its select but no longer takes it out of the Tab order')
