"""The Week Board no longer shows an "Illustrative margin".

Stage 11 (CLAUDE.md, "Stage 11 - Integrity and access"). Each card's
"numbers behind this" panel carried a row like "Illustrative margin  KC by
~10.1", a point margin back-solved from the win probability. Margin
modelling was tested as a predictor and REJECTED (Model Lab), so the page was
presenting a number of the kind the project had decided not to trust -- and
at card size its "~" read as a minus (docs/design/UX-REVIEW-2026-09-26.md).

Retired, not restyled. This guard is what keeps a deletion deleted: the
helper, the markup, the label and the styles are each named, because a
partial revert could bring back any one of them. It reads code with comments
stripped, since the comment marking where the row used to be names it.

Run with: pytest tests/test_no_illustrative_margin.py -v
"""
import re

import pytest

from src.pipeline.template_parts import JOINED_TEMPLATE  # noqa: E402

TEMPLATE = JOINED_TEMPLATE


@pytest.fixture(scope='module')
def code():
    src = TEMPLATE.read_text(encoding='utf-8')
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    src = re.sub(r'<!--.*?-->', '', src, flags=re.S)
    return re.sub(r'(?m)^\s*//.*$', '', src)


def test_the_page_has_something_to_search(code):
    """Vacuity: the why-panel the row lived in must still be found."""
    assert 'class="why-panel"' in code and 'whyRow(' in code, (
        'the why-panel is gone, so the absence checks below prove nothing')


@pytest.mark.parametrize('token, what', [
    ('Illustrative margin', 'the label'),
    ('impliedMargin', 'the helper that back-solved the margin'),
    ('implied-margin', 'the markup and its styles'),
    ('marginHtml', 'the panel slot the row was written into'),
])
def test_the_retired_margin_does_not_come_back(code, token, what):
    assert token.lower() not in code.lower(), (
        f'{what} ({token!r}) is back in the template. Margin modelling was '
        'rejected; a margin back-solved from the probability says the same '
        'thing with less honesty than the Vegas line already on the card.')
