"""NFL prose keeps a readable measure (Stage 78 item 40, the 2026-10-13 UI/UX audit's N11).

At 1440 px the NFL's Methodology and Checks paragraphs ran to 159
characters a line (measured 2026-10-14) while the NHL's and NBA's ledes
cap at 72ch. The NFL's .method-block paragraphs and list items now cap at
72ch too: 738 px at 14 px type, where the longest line holds about 115
characters of this face (a "ch" is the width of a zero, wider than the
average letter).

Run with: pytest tests/test_prose_measure.py -v
"""
import re

from src.core.template_parts import every_stylesheet

CSS = re.sub(r'/\*.*?\*/', '', dict(every_stylesheet())['the NFL template'], flags=re.S)


def test_nfl_prose_caps_at_72ch():
    rules = [b for s, b in re.findall(r'([^{}]+)\{([^{}]*)\}', CSS)
             if {'.method-block p', '.method-block li'} <= {x.strip() for x in s.split(',')}]
    assert rules and all('max-width:72ch' in b for b in rules), rules


def test_it_matches_the_other_sports_ledes():
    sheets = dict(every_stylesheet())
    for sp in ('nhl', 'nba'):
        assert 'max-width:72ch' in sheets[f'src/sports/{sp}/pages/{sp}.css'], f'the {sp} lede no longer caps at 72ch'
