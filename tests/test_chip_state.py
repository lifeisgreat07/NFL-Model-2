"""Every chip says whether it is on the same way: aria-pressed (Stage 26 item 9).

The 2026-09-28 audit found three conventions for one control: the Week
Board's filters marked the chosen chip with .active alone (nothing a screen
reader hears), Model Lab's filters used aria-current, and the reliability
series toggles used aria-pressed. All three now carry aria-pressed. The
LOOK still differs by kind, as the button system says: .active for the one
chosen filter, .btn-toggle for an on/off series. So the neutral series look
is keyed on .btn-toggle, and a filter chip carrying aria-pressed="false"
does not turn dashed.
"""
import re

from src.core.template_parts import read_template

TEMPLATE = read_template()


def chip_tags():
    return re.findall(r'<button[^>]*class="btn btn-chip[^"]*"[^>]*>', TEMPLATE)


def test_the_scan_finds_all_three_kinds():
    tags = chip_tags()
    assert any('filter-btn' in t for t in tags), 'Week Board filters not found'
    assert any('lab-filter' in t for t in tags), 'Model Lab filters not found'
    assert any('rel-toggle' in t for t in tags), 'reliability toggles not found'


def test_every_chip_carries_aria_pressed_and_none_aria_current():
    for t in chip_tags():
        assert 'aria-pressed="' in t, f'a chip without aria-pressed: {t[:120]}'
        assert 'aria-current' not in t, f'a chip still uses aria-current: {t[:120]}'
    # aria-current="page" on the nav buttons is navigation, where it belongs
    # (Stage 26 item 2); any other aria-current a script sets is a chip.
    assert not re.search(r"setAttribute\('aria-current', (?!'page'\))", TEMPLATE), (
        'a script sets aria-current to something other than "page"')


def test_each_filter_click_updates_aria_pressed():
    board = re.search(r"document\.querySelectorAll\('#filter-row \.filter-btn\[data-filter\]'\)\.forEach\(b=>\{(.*?)\}\);",
                      TEMPLATE, re.S)
    assert board and "b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');" in board.group(1)
    assert "b.setAttribute('aria-pressed', on ? 'true' : 'false');" in TEMPLATE


def test_the_series_look_is_keyed_on_btn_toggle_not_on_the_state():
    """A bare .btn-chip[aria-pressed=...] rule would restyle every filter chip
    now that filters carry the attribute too."""
    css = TEMPLATE[:TEMPLATE.index('</style>')]
    assert not re.search(r'\.btn-chip\[aria-pressed', css), 'a chip-state rule not scoped to .btn-toggle'
    assert '.btn-chip.btn-toggle[aria-pressed="false"]{border-style:dashed;' in css
