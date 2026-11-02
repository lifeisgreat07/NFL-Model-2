"""
The day boards' side column scrolls (max-height with overflow:auto, Stage 79
item 48), and a region that scrolls must be reachable by keyboard, or a
keyboard user cannot read what is below its fold (axe-core's
scrollable-region-focusable, serious).

Found 2026-11-02: once the NBA's "who is out" list grew past the viewport at
1280 px, the browser check of the real NBA page went red on every pull request
(first seen on #542, 10-28; reproduced on the page built from main's data).
The NHL's column has the same CSS and would fail the first night its list
grew as long. tabindex="0" makes each focusable; the page's focus ring
already covers it (tests/browser/check_page.py found no invisible Tab stop).

Run with: pytest tests/test_side_column_focusable.py -v
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('sport', ['nba', 'nhl'])
def test_a_scrolling_side_column_is_reachable_by_keyboard(sport):
    body = (ROOT / 'src' / 'sports' / sport / 'pages' / 'body.html').read_text(encoding='utf-8')
    aside = re.search(rf'<aside[^>]*id="{sport}-side"[^>]*>', body)
    assert aside, f'{sport}: the side column is not findable -- re-anchor this guard'
    css = (ROOT / 'src' / 'sports' / sport / 'pages' / f'{sport}.css').read_text(encoding='utf-8')
    if re.search(rf'\.{sport}-side\{{[^}}]*overflow:auto', css):
        assert 'tabindex="0"' in aside.group(0), (
            f'{sport}: the side column scrolls but cannot take focus, so a keyboard user cannot read past its fold')
