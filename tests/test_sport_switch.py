"""Every sport's page links home and to every other sport (Stage 59 item 2).

Since audit 9 D3 (Mark's M1 B, 2026-11-16) the switcher is a menu: a <details> whose button is the page you
are on, and whose list holds Home and each sport, the page's own sport marked current, in the sidebar on a
wide screen and in a strip under the top bar on a phone. Each sport's row has a slot for its season record,
which the site build fills (tests/test_sport_menu.py). The links are relative, so they work at /<sport>/ on
the site; the list is the site build's SPORTS, so a fourth sport cannot be published without each page
offering it.

Run with: pytest tests/test_sport_switch.py -v
"""
import re
from pathlib import Path

import pytest

from src.core.template_parts import read_template
from src.site.build import SPORTS

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    'nfl': read_template(),
    'nhl': (ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'body.html').read_text(encoding='utf-8'),
    'nba': (ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'body.html').read_text(encoding='utf-8'),
}
NAV = re.compile(r'<nav class="sport-switch( sport-strip)?" aria-label="Sports">(.*?)</nav>', re.S)
MARK = re.compile(r'<span class="lgm lgm-sm" aria-hidden="true">.*?</span>', re.S)
MENU = re.compile(r'<details class="sm"><summary>(.*?)<span class="sm-caret" aria-hidden="true"></span></summary>'
                  r'<div class="sm-list">(.*?)</div></details>', re.S)


def test_every_published_sport_has_a_page_here():
    assert set(PAGES) == set(SPORTS)


@pytest.mark.parametrize('sport', SPORTS)
def test_each_page_has_the_sidebar_menu_and_the_phone_strip(sport):
    navs = NAV.findall(PAGES[sport])
    assert sorted(bool(strip) for strip, _ in navs) == [False, True], (
        f'{sport}: expected one sidebar switcher and one phone strip, found {len(navs)}')


@pytest.mark.parametrize('sport', SPORTS)
def test_each_menu_names_its_page_and_lists_home_and_every_sport_with_a_record_slot(sport):
    for _, body in NAV.findall(PAGES[sport]):
        # Stage 102: each sport leads with its league's mark (tests/test_league_marks.py holds it); the links
        # and their names are read with the marks set aside.
        m = MENU.fullmatch(MARK.sub('', body))
        assert m, f'{sport}: the switcher is not one menu (a button, then the list)'
        assert m.group(1) == sport.upper(), f'{sport}: the menu button does not name the page you are on'
        got = re.findall(r'<a href="([^"]+)"( aria-current="page")?>([^<]+)(<span class="sm-rec" data-rec="([a-z]+)">'
                         r'</span>)?</a>', m.group(2))
        assert [(h, t) for h, _, t, _, _ in got] == [('../', 'Home')] + [(f'../{s}/', s.upper()) for s in SPORTS]
        assert [t for _, cur, t, _, _ in got if cur] == [sport.upper()], f'{sport}: the current sport is not marked'
        assert [r for *_, r in got] == [''] + list(SPORTS), f'{sport}: a sport without its record slot, or Home with one'
        assert m.group(2).endswith('<p class="sm-note">Records are this season\'s graded picks (Model B\'s for the NFL).</p>'), (
            f'{sport}: the records are not said to be graded picks, the NFL\'s Model B\'s')


def test_the_strip_shows_only_on_a_phone_and_hover_waits_for_a_pointer():
    css = read_template()
    css = css[:css.index('</style>')]
    assert '.sport-strip{display:none;}' in css
    assert re.search(r'@media \(max-width:1079px\)\{\s*\.sport-strip\{display:block;', css)
    assert re.search(r'@media \(hover: hover\)\{\s*\.sport-switch a:hover\{', css)
