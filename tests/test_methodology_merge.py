"""How This Compares, Data Sources and the Glossary, folded into Methodology.

Stage 7.5's target was 14 pages down to 9. This merge is what reaches it.

THE BUG THIS FILE EXISTS BECAUSE OF

The first attempt lifted each page's contents with a regex over nested divs.
It left behind, inside Methodology, an orphan `<section class="page"
id="page-datasources">` open tag and an unbalanced `</div>` -- broken markup
that the browser silently repaired by swallowing the rest of the part.

The whole suite stayed green, and the reason is worth remembering: the guard
that checks navigation targets builds its set of real pages from exactly those
`<section class="page" id="page-...">` tags. The orphans made the deleted
pages still look like they existed, so the guard compared a stale nav against a
stale page list and found them consistent. A leftover fragment defeated the
check by looking like the thing it was checking for.

So `test_no_orphan_section_tags_survived_the_merge` checks structure directly
rather than trusting any set built from it.
"""

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = REPO_ROOT / 'src' / 'dashboard_template.html'

MERGED = ['compare', 'datasources', 'glossary']
PARTS = ['part-method', 'part-compare', 'part-datasources', 'part-glossary']


def _page():
    return TEMPLATE.read_text(encoding='utf-8')


def test_the_three_pages_are_gone_as_pages():
    page = _page()
    for pid in MERGED:
        assert f'id="page-{pid}"' not in page, (
            f"page-{pid} still exists as a section; it was supposed to become "
            f"a part of Methodology, not stay a page")
        assert f'data-page="{pid}"' not in page, (
            f"a navigation control still points at the deleted page-{pid}")


def test_no_orphan_section_tags_survived_the_merge():
    """Every `<section>` opened must be closed at the top level of the page
    body -- no section may be nested inside another. The first attempt left
    three orphan open tags inside Methodology and nothing noticed, because the
    orphans were themselves what the nav guard reads to decide which pages
    exist."""
    page = _page()
    opens = len(re.findall(r'<section\b', page))
    closes = len(re.findall(r'</section>', page))
    assert opens == closes, f"{opens} <section> tags but {closes} </section> tags"

    method = re.search(r'<section class="page" id="page-method">(.*?)\n  </section>',
                       page, re.S)
    assert method, "the Methodology section has lost its shape"
    assert '<section' not in method.group(1), (
        "there is a <section> tag nested inside Methodology. That is an orphan "
        "left by a merge, and it will read as a real page to anything that "
        "counts pages -- including the nav guard")


def test_methodology_is_four_titled_parts():
    """A 26k-character page needs to say what is on it. Each part carries its
    own heading and lead so the jump links land somewhere that identifies
    itself; the first attempt gave three parts a title and left the fourth
    bare, so one link arrived at an unlabelled wall of text."""
    page = _page()
    found = re.findall(r'<div class="method-part" id="(part-[a-z]+)">\s*<h3>(.*?)</h3>',
                       page, re.S)
    assert [f for f, _ in found] == PARTS, (
        f"expected four titled parts in order {PARTS}, found {[f for f, _ in found]}")
    for pid, title in found:
        assert title.strip(), f"{pid} has an empty title"


def test_every_jump_link_lands_on_a_part_that_exists():
    page = _page()
    targets = set(re.findall(r'<a href="#(part-[a-z]+)"', page))
    parts = set(re.findall(r'<div class="method-part" id="(part-[a-z]+)"', page))
    assert targets, "the jump navigation is gone"
    assert targets <= parts, (
        f"jump links point at parts that do not exist: {sorted(targets - parts)}")
    assert parts <= targets, (
        f"these parts have no jump link, so nothing on the page reaches them: "
        f"{sorted(parts - targets)}")


def test_the_parts_are_the_only_top_level_headings():
    """The ten original Methodology headings were demoted h3 -> h4 so the four
    parts are the only h3s. If a later edit adds an h3 inside a part, the page
    has two things claiming to be the same level and the jump nav starts
    lying about the structure."""
    page = _page()
    method = re.search(r'<section class="page" id="page-method">(.*?)\n  </section>',
                       page, re.S).group(1)
    h3s = re.findall(r'<h3[^>]*>(.*?)</h3>', method, re.S)
    assert len(h3s) == len(PARTS), (
        f"Methodology has {len(h3s)} h3 headings but {len(PARTS)} parts: {h3s}. "
        f"Section headings inside a part belong at h4")


def test_the_ats_finding_survived():
    """The reason How This Compares was never allowed to be deleted. The
    honest negative is the project's credibility, and it is the single most
    load-bearing sentence on the merged page."""
    page = _page()
    assert '51.61' in page, "the ATS accuracy figure is gone"
    method = re.search(r'<section class="page" id="page-method">(.*?)\n  </section>',
                       page, re.S).group(1)
    assert '51.61' in method, (
        "the ATS finding is no longer on Methodology, so it survived the merge "
        "of How This Compares in name only")


@pytest.mark.parametrize('phrase', [
    'In Production',            # Data Sources
    'Research-Only',            # Data Sources
    'Betting Terms',            # Glossary
    'Evaluation Terms',         # Glossary
    'The Short Version',        # How This Compares
])
def test_the_merged_content_is_actually_there(phrase):
    """Named individually, for the same reason the What's Changed suite names
    its milestones: a merge that renders correctly and quietly drops half its
    content passes every structural check."""
    assert phrase in _page(), f"{phrase!r} did not survive the merge"


def test_every_table_row_matches_its_header():
    """A pre-existing defect this merge surfaced. The Research-Only table
    declared four columns and five of its six rows supplied three, so their
    outcome text had been rendering under "What It Was Tested For" since the
    page was written -- a table quietly saying the wrong thing about every row
    but one.

    Nothing caught it because nothing compared rows to headers, and it stayed
    invisible until removing a column shifted the misalignment far enough to
    see in a screenshot. Checked over every table on the page, and by the
    MINIMUM row width rather than the maximum: taking the max is what let this
    hide, since one correct row made the table look consistent.
    """
    page = _page()
    method = re.search(r'<section class="page" id="page-method">(.*?)\n  </section>',
                       page, re.S).group(1)
    for n, table in enumerate(re.findall(r'<table[^>]*>.*?</table>', method, re.S)):
        head = re.search(r'<thead><tr>(.*?)</tr></thead>', table, re.S)
        if not head:
            continue
        cols = len(re.findall(r'<th[^>]*>', head.group(1)))
        for row in re.findall(r'<tr>((?:(?!</tr>).)*)</tr>', table, re.S):
            if '<th' in row or 'colspan' in row:
                continue
            cells = len(re.findall(r'<td[^>]*>', row))
            assert cells == cols, (
                f"table {n} on Methodology declares {cols} columns but a row has "
                f"{cells} cells, so that row's values are printed under the wrong "
                f"headings: {re.sub(r'<[^>]+>', ' | ', row).strip()[:120]}")


def test_the_clutter_the_plan_named_is_gone():
    """Two things Stage 7.5 explicitly called clutter on Data Sources. Removing
    the page without removing them would have moved the clutter, not cut it."""
    page = _page()
    assert 'Checked and Blocked' not in page, (
        "the 'Checked and Blocked' block is still here -- a list of sources we "
        "do not use, on the part that answers where the numbers come from")
    assert '<th>Function</th>' not in page, (
        "the Function column is still here; a reader asking where the numbers "
        "come from does not need the library call that fetched them")


def test_the_built_page_carries_the_merge():
    built = REPO_ROOT / 'index.html'
    if not built.exists():
        pytest.skip('index.html has not been generated in this checkout')
    page = built.read_text(encoding='utf-8')
    assert 'id="page-glossary"' not in page, "the built page still ships a deleted section"
    assert 'part-glossary' in page, "the built page is stale -- regenerate it"


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
