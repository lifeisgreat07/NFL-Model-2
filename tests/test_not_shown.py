"""Methodology says what the page leaves out on purpose (Stage 37 item 5,
the 2026-10-04 fourth audit).

Each gap is real and known: picks after kickoff, regional TV markets,
Monday night's final before Tuesday, neutral-site home edges, and the
lock-time line against the closing line. Said once, on the page a reader
goes to for "how does this work", so a missing number never reads as a
broken page.

Run with: pytest tests/test_not_shown.py -v
"""
import re

from src.core.template_parts import JOINED_TEMPLATE


def block():
    t = JOINED_TEMPLATE.read_text(encoding='utf-8')
    method = t[t.index('id="page-method"'):]
    method = method[:method.index('</section>')]
    m = re.search(r'<div class="method-block" id="not-shown">(.*?)</ul>', method, re.S)
    assert m, 'Methodology no longer says what the page leaves out (#not-shown)'
    return m.group(1)


def test_methodology_names_each_gap_once():
    b = block()
    items = re.findall(r'<li>(.*?)</li>', b, re.S)
    assert len(items) == 5, items
    for words in ('after kickoff', 'regional', 'Monday night', 'Neutral-site', 'closing line'):
        assert sum(words in i for i in items) == 1, f'{words!r} is not exactly one item'
