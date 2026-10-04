"""The phone's More button lights up on exactly the pages in its sheet
(Stage 25 item 4).

OVERFLOW_PAGES decides when the bottom nav's More button is marked active.
Until Stage 25 it named four pages Stage 7.5 had folded into others
(roadmap, datasources, compare, glossary) and left out changelog, so on
What's Changed a phone showed no active tab at all. The list is now held
equal to the data-page values of the More sheet's own buttons.
"""
import json
import re

from src.pipeline.template_parts import JOINED_TEMPLATE

TEMPLATE = JOINED_TEMPLATE


def overflow_pages(src):
    m = re.search(r'const OVERFLOW_PAGES = (\[[^\]]*\]);', src)
    assert m, 'OVERFLOW_PAGES is not findable -- re-anchor this test'
    return json.loads(m.group(1).replace("'", '"'))


def sheet_pages(src):
    return re.findall(r'<button class="bnav-more-item[^"]*" data-page="([^"]+)"', src)


def test_the_scan_finds_the_sheet():
    pages = sheet_pages(TEMPLATE.read_text(encoding='utf-8'))
    assert 'changelog' in pages and len(pages) >= 3, pages


def test_the_more_button_list_is_the_sheet():
    src = TEMPLATE.read_text(encoding='utf-8')
    assert sorted(overflow_pages(src)) == sorted(sheet_pages(src))


def test_every_listed_page_exists():
    src = TEMPLATE.read_text(encoding='utf-8')
    for page in overflow_pages(src):
        assert f'id="page-{page}"' in src, f'{page} is in OVERFLOW_PAGES but has no page'
