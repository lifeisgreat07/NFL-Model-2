"""The Week Board card's two disclosure buttons say whether they are open
(Stage 26 item 6).

The 2026-09-28 audit: "+ the numbers behind this" (.why-toggle) and
"+ view context" (.toggle-flag) open and close a panel, but carried no
aria-expanded or aria-controls, so a screen reader heard a button and
nothing about the state; the "+"/"−" in the label is not a state. Team
Deep-Dive's .dive-game-head already did it right, and these follow it:
aria-controls names the panel's id, and aria-expanded starts "false" and is
set from the panel's .open on every click.
"""
import re

from src.pipeline.template_parts import read_template

TEMPLATE = read_template()

BUTTONS = {
    # class -> (panel id prefix, handler's panel variable)
    'why-toggle': ('why-', 'panel'),
    'toggle-flag': ('flag-', 'note'),
}


def button(cls):
    m = re.search(r'<button class="btn btn-link ' + cls + r'"[^>]*>', TEMPLATE)
    assert m, f'the .{cls} button is not findable -- re-anchor this test'
    return m.group(0)


def handler(cls):
    m = re.search(r"document\.querySelectorAll\('\." + cls + r"'\)\.forEach\(btn=>\{(.*?)\n  \}\);",
                  TEMPLATE, re.S)
    assert m, f'the .{cls} click handler is not findable -- re-anchor this test'
    return m.group(1)


def test_each_button_starts_closed_and_names_its_panel():
    for cls, (prefix, _) in BUTTONS.items():
        b = button(cls)
        assert 'aria-expanded="false"' in b, f'.{cls} has no aria-expanded'
        assert f'aria-controls="{prefix}${{idSafe}}"' in b, f'.{cls} does not name its panel'
        assert f'id="{prefix}${{idSafe}}"' in TEMPLATE, f'no panel with the id .{cls} names'


def test_each_click_sets_the_state_from_the_panel():
    for cls, (_, var) in BUTTONS.items():
        h = handler(cls)
        assert (f"btn.setAttribute('aria-expanded', {var}.classList.toggle('open') "
                f"? 'true' : 'false');") in h, f'.{cls} click does not set aria-expanded'
