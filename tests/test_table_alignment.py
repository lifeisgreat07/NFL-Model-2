"""A table's header sits over its column (2026-09-28).

Methodology's "Which Features Actually Do the Work" table right-aligned its
numbers (td.num) under left-aligned headers, so ACCURACY CHANGE and 95% CI
read as labels for the wrong column. Mark spotted it on the page. The rule
now: in every table written into the template, a column's header and its
cells agree on class="num", and th.num is right-aligned like td.num.

The reverse also held a bug: the "Research-only" table marked three words
("Rejected") as numbers, so they sat right while the rest of their column
sat left.

Run with: pytest tests/test_table_alignment.py -v
"""
import re

import pytest

from src.core.template_parts import JOINED_TEMPLATE

TEMPLATE = JOINED_TEMPLATE


def source():
    return TEMPLATE.read_text(encoding='utf-8')


def static_tables():
    """(line, header attrs, [row cell attrs]) for each table whose rows are
    written into the template rather than rendered by a script."""
    src = source()
    out = []
    for m in re.finditer(r'<table[^>]*>(.*?)</table>', src, re.S):
        head = re.search(r'<thead>(.*?)</thead>', m.group(1), re.S)
        body = re.search(r'<tbody>(.*?)</tbody>', m.group(1), re.S)
        if not head or not body:
            continue
        rows = [re.findall(r'<td([^>]*)>', r) for r in re.findall(r'<tr>(.*?)</tr>', body.group(1), re.S)]
        if not rows:
            continue
        out.append((src[:m.start()].count('\n') + 1, re.findall(r'<th([^>]*)>', head.group(1)), rows))
    return out


def test_there_are_tables_to_check():
    assert len(static_tables()) >= 8, 'the scan found fewer tables than the template has'


@pytest.mark.parametrize('line, ths, rows', static_tables())
def test_a_number_column_is_a_number_column_from_header_to_last_row(line, ths, rows):
    for r in rows:
        if any('colspan' in a for a in r):
            continue
        for i, (th, td) in enumerate(zip(ths, r)):
            assert ('num' in th) == ('num' in td), (
                f'table at line {line}, column {i + 1}: the header and a cell disagree on '
                f'class="num" ({th.strip() or "none"} vs {td.strip() or "none"}), so they are '
                'aligned differently')


def test_a_number_header_is_right_aligned_like_its_numbers():
    m = re.search(r'\.metrics-table th\.num\{([^}]*)\}', source())
    assert m and 'text-align:right' in m.group(1).replace(' ', '')
