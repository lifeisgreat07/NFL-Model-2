"""Every text toggle is at least 24 CSS px tall (WCAG 2.5.8, target size).

Stage 11 (CLAUDE.md, "Stage 11 - Integrity and access"). `.btn-link` had no
padding, so a text toggle was only as tall as its 11px line: the Week Board's
"+ view context" measured 13px at 390 wide
(docs/design/UX-REVIEW-2026-09-26.md). The floor is on the component, so it
holds for every text toggle -- "+ the numbers behind this", "+ view context"
and Undo -- and for the next one anybody adds.

There is no browser in this suite, so the rendered height cannot be read
here. What CAN be held is the three things the rendered height rests on: the
component's floor, every text toggle wearing the component, and nothing more
specific capping the height below the floor. Stage 12 adds the rendered
check in CI.

Run with: pytest tests/test_text_toggle_target.py -v
"""
import re

import pytest

from src.core.template_parts import JOINED_TEMPLATE

TEMPLATE = JOINED_TEMPLATE
FLOOR = 24
# The hooks each text toggle is selected by (CLAUDE.md, Stage 10: look and
# behaviour are separate, and these older classes carry the behaviour).
TOGGLE_HOOKS = ('why-toggle', 'toggle-flag', 'undo-btn')


@pytest.fixture(scope='module')
def source():
    return TEMPLATE.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def css_rules(source):
    styles = ''.join(re.findall(r'<style[^>]*>(.*?)</style>', source, re.S))
    styles = re.sub(r'/\*.*?\*/', '', styles, flags=re.S)
    rules = [(sel.strip(), body) for sel, body in re.findall(r'([^{}]+)\{([^{}]*)\}', styles)]
    assert len(rules) > 100, f'only {len(rules)} CSS rules parsed -- the parser is blind'
    return rules


def _px(body, prop):
    m = re.search(r'(?:^|;)\s*' + prop + r'\s*:\s*([0-9.]+)px', body)
    return float(m.group(1)) if m else None


def test_the_text_toggle_component_is_at_least_24px_tall(css_rules):
    base = [body for sel, body in css_rules if sel == '.btn-link']
    assert len(base) == 1, f'expected one base .btn-link rule, found {len(base)}'
    h = _px(base[0], 'min-height')
    assert h is not None and h >= FLOOR, (
        f'.btn-link has min-height {h}; a text toggle with no padding is only as '
        f'tall as its line, 13px at 390 wide before Stage 11')


def test_every_text_toggle_wears_the_component(source):
    buttons = re.findall(r'<button\b[^>]*class="([^"]*)"', source)
    hooked = [c for c in buttons if any(h in c.split() for h in TOGGLE_HOOKS)]
    found = {h for c in hooked for h in TOGGLE_HOOKS if h in c.split()}
    assert found == set(TOGGLE_HOOKS), (
        f'expected a button for each of {TOGGLE_HOOKS}, found {sorted(found)} -- '
        'this guard is looking at the wrong markup')
    bare = [c for c in hooked if 'btn-link' not in c.split()]
    assert not bare, f'text toggles without .btn-link, so without its floor: {bare}'


def test_nothing_caps_a_text_toggle_below_the_floor(css_rules):
    names = ('btn-link',) + TOGGLE_HOOKS
    capped = []
    for sel, body in css_rules:
        if not any(re.search(r'\.' + n + r'\b', sel) for n in names):
            continue
        for prop in ('height', 'max-height', 'min-height'):
            v = _px(body, prop)
            if v is not None and v < FLOOR:
                capped.append(f'{sel} {{{prop}:{v}px}}')
    assert not capped, f'rules holding a text toggle under {FLOOR}px: {capped}'
