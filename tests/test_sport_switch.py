"""Every sport's page links home and to every other sport (Stage 59 item 2).

Option A of the rendered "Sport Switcher Options": Home and each sport as
pills, the page's own sport marked current, in the sidebar on a wide screen
and in a strip under the top bar on a phone. The links are relative, so they
work at /<sport>/ on the site; the list is the site build's SPORTS, so a
fourth sport cannot be published without each page offering it.

Run with: pytest tests/test_sport_switch.py -v
"""
import re
from pathlib import Path

import pytest

from src.pipeline.template_parts import read_template
from src.site.build import SPORTS

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    'nfl': read_template(),
    'nhl': (ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'body.html').read_text(encoding='utf-8'),
    'nba': (ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'body.html').read_text(encoding='utf-8'),
}
NAV = re.compile(r'<nav class="sport-switch( sport-strip)?" aria-label="Sports">(.*?)</nav>', re.S)


def test_every_published_sport_has_a_page_here():
    assert set(PAGES) == set(SPORTS)


@pytest.mark.parametrize('sport', SPORTS)
def test_each_page_has_the_sidebar_pills_and_the_phone_strip(sport):
    navs = NAV.findall(PAGES[sport])
    assert sorted(bool(strip) for strip, _ in navs) == [False, True], (
        f'{sport}: expected one sidebar switcher and one phone strip, found {len(navs)}')


@pytest.mark.parametrize('sport', SPORTS)
def test_each_switcher_links_home_and_every_sport_marking_its_own(sport):
    for _, body in NAV.findall(PAGES[sport]):
        got = re.findall(r'<a href="([^"]+)"( aria-current="page")?>([^<]+)</a>', body)
        assert [(h, t) for h, _, t in got] == [('../', 'Home')] + [(f'../{s}/', s.upper()) for s in SPORTS]
        assert [t for _, cur, t in got if cur] == [sport.upper()], f'{sport}: the current sport is not marked'


def test_the_strip_shows_only_on_a_phone_and_hover_waits_for_a_pointer():
    css = read_template()
    css = css[:css.index('</style>')]
    assert '.sport-strip{display:none;}' in css
    assert re.search(r'@media \(max-width:1079px\)\{\s*\.sport-strip\{display:flex;', css)
    assert re.search(r'@media \(hover: hover\)\{\s*\.sport-switch a:hover\{', css)
