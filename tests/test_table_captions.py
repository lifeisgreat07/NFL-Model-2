"""
Every data table on the page has a caption, so a screen reader announces
what the table is before it reads the first cell.

The 2026-09-29 re-audit (Stage 34 item 29) found none. Sighted readers
already have a heading above each table, so the caption is visually hidden
(.visually-hidden, the page's one hiding rule) rather than a second visible
title. The check enumerates the class: every <table in the template, whether
it is markup or a JavaScript template string, including tables added later.

Run with: pytest tests/test_table_captions.py -v
"""
import re

from src.pipeline.template_parts import JOINED_TEMPLATE  # noqa: E402

TEMPLATE = JOINED_TEMPLATE
TABLE = re.compile(r'<table\b[^>]*>')
CAPTION = re.compile(r'\s*<caption class="visually-hidden">([^<]+)</caption>')


def captions(html):
    """[(line, caption text or None)] for every table, in order."""
    found = []
    for m in TABLE.finditer(html):
        line = html.count('\n', 0, m.start()) + 1
        c = CAPTION.match(html, m.end())
        found.append((line, c.group(1).strip() if c else None))
    return found


def test_every_table_opens_with_a_caption():
    found = captions(TEMPLATE.read_text(encoding='utf-8'))
    assert len(found) >= 14, f"only {len(found)} tables found; the matcher is broken"
    missing = [line for line, text in found if not text]
    assert not missing, f"tables with no caption as their first child, at template lines {missing}"


def test_no_two_tables_share_a_caption():
    texts = [text for _, text in captions(TEMPLATE.read_text(encoding='utf-8')) if text]
    repeated = sorted({t for t in texts if texts.count(t) > 1})
    assert not repeated, f"captions used twice, so they do not tell the tables apart: {repeated}"


def test_the_hiding_rule_the_captions_use_exists():
    html = TEMPLATE.read_text(encoding='utf-8')
    assert re.search(r'\.visually-hidden\s*\{[^}]*position:\s*absolute', html), (
        "the captions rely on .visually-hidden, which no longer hides anything")


def test_a_table_without_a_caption_is_found():
    """Synthetic, so the failing branch stays reachable while every table has one."""
    html = ('<table><caption class="visually-hidden">A</caption><tr></tr></table>\n'
            '<table class="metrics-table">\n  <thead></thead></table>')
    assert captions(html) == [(1, 'A'), (2, None)]
