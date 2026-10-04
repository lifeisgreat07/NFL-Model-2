"""One HTML escaper and one spelling (Stage 25 item 5).

The 2026-09-28 audit found three identical escapers in the template
(cardEsc, clEscape, and a local esc in renderTeamNews) and the Why panel
saying "Offence"/"Defence" while Power Ratings says "Offense"/"Defense".
Three copies of an escaper is three places to fix when one is found
wanting; two spellings on one page read as two different things.
"""
import re

from src.pipeline.template_parts import read_template

TEMPLATE = read_template()

# The body every copy shared: replacing & < > " with entities.
ESCAPE_BODY = re.compile(r"""replace\(/\[&<>"\]/g""")


def test_there_is_one_escaper():
    assert len(ESCAPE_BODY.findall(TEMPLATE)) == 1, (
        'more than one HTML escaper in the template -- use escapeHtml()')


def test_the_page_spells_offense_and_defense_one_way():
    assert not re.search(r'\b(Offence|Defence)\b', TEMPLATE)
    assert "{off_matchup: 'Offense', def_matchup: 'Defense'," in TEMPLATE
