"""Every column header says it is one (Stage 26 item 7).

The 2026-09-28 audit counted 46 <th> in the template and none with a
scope. Every one sits in a <thead>, so each is scope="col". Held over the
template's text, which includes the tables its JavaScript builds.
"""
import re

from src.core.template_parts import read_template

TEMPLATE = read_template()


def headers():
    out = []
    for m in re.finditer(r'<th\b[^>]*>', TEMPLATE):
        before = TEMPLATE[:m.start()]
        out.append((m.group(0), before.rfind('<thead') > before.rfind('</thead')))
    return out


def test_the_scan_finds_the_headers():
    assert len(headers()) >= 40, f'only {len(headers())} <th> found -- re-anchor this test'


def test_every_header_is_in_a_thead_and_scoped_to_its_column():
    loose = [tag for tag, in_head in headers() if not in_head]
    assert not loose, f'a <th> outside any <thead> needs a decision (scope="row"?): {loose}'
    missing = [tag for tag, _ in headers() if 'scope="col"' not in tag]
    assert not missing, f'<th> without scope="col": {missing}'
