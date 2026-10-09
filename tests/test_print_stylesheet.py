"""Printing a page prints that page (Stage 47 item 11).

Held here: there is one print block; it keeps the navigation, the controls
and every page but the open one off the paper; it keeps the bars and chips,
which are backgrounds a browser drops by default; it does not split a card
or a table row across sheets; and a page in the dark theme prints in the
light one and goes back afterwards.

Checked by hand once, in Chromium's own PDF output: the Week Board and Power
Ratings printed in the light theme, with no menu or controls, every bar
drawn, and the reader's theme back after.

Run with: pytest tests/test_print_stylesheet.py -v
"""
import re

import pytest

from src.core.template_parts import JOINED_TEMPLATE

SRC = JOINED_TEMPLATE.read_text(encoding='utf-8').replace('\r\n', '\n')


def print_block():
    blocks = re.findall(r'@media print\{(.*?)\n  \}', SRC, re.S)
    assert len(blocks) == 1, f'expected one print block, found {len(blocks)}'
    return blocks[0]


@pytest.mark.parametrize('sel', ['.sidebar', '.topbar', '.sport-strip', '.bottom-nav', '.bnav-more-sheet',
                                 '.filter-row', '.pdf-link', '.onboarding-banner'])
def test_navigation_and_controls_stay_off_the_paper(sel):
    hide = re.search(r'([^{}]*)\{display:none !important;\}', print_block()).group(1)
    assert sel in [s.strip() for s in hide.split(',')], sel


def test_only_the_open_page_prints():
    assert '.page:not(.active){display:none !important;}' in print_block()


def test_the_bars_and_chips_print():
    assert 'print-color-adjust:exact' in print_block()


def test_cards_and_rows_are_not_split_across_sheets():
    rule = re.search(r'([^{}]*)\{break-inside:avoid;\}', print_block()).group(1)
    for sel in ('.game-card', 'tr', '.method-block'):
        assert sel in [s.strip() for s in rule.split(',')], sel


def test_a_dark_page_prints_light_and_goes_back():
    js = SRC[SRC.index('(function printInLight(){'):]
    js = js[:js.index('})();') + 5]
    assert "addEventListener('beforeprint'" in js and "setAttribute('data-theme', 'light')" in js
    assert "addEventListener('afterprint'" in js and "removeAttribute('data-theme')" in js
