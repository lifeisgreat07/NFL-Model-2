"""One safe_json, one font_faces_css, one escapeHtml (Stage 68 item 24, the 2026-10-09 audit's E17).

The home, NHL and NBA builds each carried a copy of the first two and the
NHL's and NBA's scripts a copy of the third. They live in src/core now,
and these tests keep a copy from growing back. The NFL's board keeps its
own safe_json, which passes json.dumps's arguments through
(tests/test_safe_json_fills.py), and uses the core's font_faces_css.

Run with: pytest tests/test_one_page_fill.py -v
"""
import re
from pathlib import Path

import pytest

from src.core import page_fill
from src.site import home
from src.sports.nba import site as nba_site
from src.sports.nfl import generate_dashboard as gd
from src.sports.nhl import site as nhl_site

ROOT = Path(__file__).resolve().parents[1]
BUILDS = {'home': 'src/site/home.py', 'nhl': 'src/sports/nhl/site.py', 'nba': 'src/sports/nba/site.py'}


@pytest.mark.parametrize('name', BUILDS)
def test_no_build_defines_its_own(name):
    src = (ROOT / BUILDS[name]).read_text(encoding='utf-8')
    assert not re.search(r'^def (safe_json|font_faces_css)\(', src, re.M), name
    assert re.search(r'^from src\.core\.page_fill import .*\bsafe_json\b', src, re.M), name


def test_every_build_uses_the_core_functions():
    for mod in (home, nhl_site, nba_site):
        assert mod.safe_json is page_fill.safe_json and mod.font_faces_css is page_fill.font_faces_css
    assert gd.font_faces_css is page_fill.font_faces_css


@pytest.mark.parametrize('sport', ('nhl', 'nba'))
def test_the_sport_scripts_share_one_escape(sport):
    js = (ROOT / 'src' / 'sports' / sport / 'pages' / f'{sport}.js').read_text(encoding='utf-8')
    assert 'function escapeHtml' not in js
    page = (ROOT / 'src' / 'sports' / sport / 'pages' / 'page.html').read_text(encoding='utf-8')
    assert f'<script>\n{{% include "escape.js" %}}\n{{% include "{sport}.js" %}}\n' in page.replace('\r\n', '\n')


@pytest.mark.parametrize('sport', ('nhl', 'nba'))
def test_the_build_fills_the_include(sport):
    src = (ROOT / BUILDS[sport]).read_text(encoding='utf-8')
    assert """.replace('{% include "escape.js" %}', ESCAPE_JS.read_text(encoding='utf-8'))""" in src
    assert page_fill.ESCAPE_JS.read_text(encoding='utf-8').count('function escapeHtml(') == 1


def test_safe_json_cannot_close_a_script():
    out = page_fill.safe_json({'x': '</script><b>&'})
    assert '<' not in out and '>' not in out and '&' not in out
