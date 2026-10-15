"""Four table and chart details (Stage 78 item 39, the 2026-10-13 UI/UX audit's N8, L4, N9 and N10).

Measured 2026-10-14 on the NFL page at 1440 px: every td.num drew
proportional figures (160 cells on Power Ratings, 120 on Model Lab), the
last row of every .metrics-table kept a 1 px border under its th, .rel-prov
drew at 14 px because .method-block p outranked it, and the Power Ratings
sparkline wore the accent beside a Net bar that had left it. After: tabular
figures, no last-row border, 11 px, --text-3.

Run with: pytest tests/test_table_details.py -v
"""
import re

from src.core.template_parts import every_stylesheet

CSS = re.sub(r'/\*.*?\*/', '', dict(every_stylesheet())['the NFL template'], flags=re.S)


def rule(selector):
    found = [b for s, b in re.findall(r'([^{}]+)\{([^{}]*)\}', CSS)
             if s.strip() == selector or selector in {x.strip() for x in s.split(',')}]
    assert found, f'{selector} is not findable -- re-anchor this guard'
    return ' '.join(found)


def specificity(selector):
    ids = selector.count('#')
    classes = len(re.findall(r'\.[\w-]+|\[[^\]]+\]|:(?!:)[\w-]+', selector))
    elements = len(re.findall(r'(?:^|[\s>+~])([a-z][\w-]*)', selector))
    return (ids, classes, elements)


def test_number_cells_use_tabular_figures():
    assert 'font-variant-numeric:tabular-nums' in rule('td.num')


def test_the_last_row_has_no_border_under_its_header_cell_either():
    assert 'border-bottom:none' in rule('.metrics-table tr:last-child :is(td, th)')


def test_the_provenance_note_outranks_the_prose_rule_it_sits_inside():
    assert 'font-size:var(--fs-11)' in rule('.method-block .rel-prov')
    assert specificity('.method-block .rel-prov') > specificity('.method-block p')


def test_the_sparkline_is_quiet():
    assert 'stroke:var(--text-3)' in rule('.trend-spark polyline')
    assert 'fill:var(--text-3)' in rule('.trend-spark circle')
