"""A phone prints the cards (Stage 78 item 44, the 2026-10-13 UI/UX audit's N7).

Printing the NFL Week Board at 390 px put 15 rows on the paper and none of
the 15 cards (measured 2026-10-14 with print media emulated): the phone
layout hides every card its row has not opened, and the print block did not
undo that. In print now every card shows, with its matchup header (the
phone hides it because the row names the game), and the rows, the flag
legend and the filter line, which belong to the rows, do not.

Run with: pytest tests/test_phone_print.py -v
"""
import re

from src.core.template_parts import every_stylesheet

CSS = re.sub(r'/\*.*?\*/', '', dict(every_stylesheet())['the NFL template'], flags=re.S)


def print_block():
    start = CSS.index('@media print{')
    i, depth = CSS.index('{', start), 0
    for j in range(i, len(CSS)):
        depth += {'{': 1, '}': -1}.get(CSS[j], 0)
        if depth == 0:
            return CSS[i:j]
    raise AssertionError('the print block is not closed')


def test_print_shows_every_card_with_its_header():
    block = print_block()
    assert '#game-grid .game-card.nfl-collapsible{display:block !important;}' in block
    assert '#game-grid .game-card.nfl-collapsible > .matchup-header{display:flex !important;}' in block


def test_print_leaves_out_what_belongs_to_the_rows():
    assert '#game-grid .nfl-row, .nfl-flag-legend, .nfl-filtered-note{display:none !important;}' in print_block()
