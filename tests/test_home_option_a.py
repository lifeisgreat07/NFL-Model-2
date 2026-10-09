"""The home page as option A of "Sportalytics Home Page Options", with option
C's "New here?" questions (Stage 66; Mark, 2026-10-09).

Option A puts a scoreboard first: a header with the three sports' marks,
wordmark W2, the sport pills and a theme button; a plain statement of what
the site does; each sport's record; the cards; three steps on how it works;
and links to the method, the checks and the source. From option C come
three questions a newcomer asks, closed until opened. The browser checks
render the page; these tests hold its parts, and run the scoreboard's code
under node.

Run with: pytest tests/test_home_option_a.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PAGE = (REPO / 'src' / 'site' / 'home' / 'page.html').read_text(encoding='utf-8')
JS = (REPO / 'src' / 'site' / 'home' / 'home.js').read_text(encoding='utf-8')
NFL_BODY = (REPO / 'src' / 'dashboard' / 'body.html').read_text(encoding='utf-8')
NODE = shutil.which('node')


def header():
    return re.search(r'<header class="home-bar">(.*?)</header>', PAGE, re.S).group(1)


def test_the_header_has_the_three_marks_the_wordmark_the_pills_and_a_theme_button():
    h = header()
    assert len(re.findall(r'<svg class="home-mark"', h)) == 3
    assert 'rx="8.6" ry="5.2"' in h and 'rx="8.4" ry="3.2"' in h and 'r="8.4"' in h, 'football, puck P3, ball B2'
    assert '<span class="home-marks" aria-hidden="true">' in h, 'the marks repeat the name; a reader skips them'
    assert '<span class="home-wordmark">Sporta<span class="wm-accent">lytics</span></span>' in h
    assert re.search(r'<nav class="home-switch" aria-label="Sports">.*?aria-current="page">Home</a>', h, re.S)
    assert '<button type="button" class="home-theme" aria-label="Switch to the light theme">' in h


def test_the_page_says_what_the_site_does_before_anything_else():
    main = PAGE[PAGE.index('<main'):]
    first = re.search(r'<h1 class="home-title">(.*?)</h1>', main).group(1)
    assert first == 'Sports picks, made before the game and graded in public'
    assert main.index('home-title') < main.index('id="home-score"') < main.index('id="home-cards"')


def test_how_it_works_has_three_steps_in_order():
    steps = re.findall(r'<li><span class="home-step-n" aria-hidden="true">(\d)</span><span><b>(.*?)</b>', PAGE)
    assert steps == [('1', 'Picked before the game'), ('2', 'Locked in public'), ('3', 'Graded after')]


def test_new_here_asks_option_cs_three_questions_closed():
    faq = re.search(r'<section class="home-faq".*?</section>', PAGE, re.S).group(0)
    assert '<h2 id="home-faq-title">New here?</h2>' in faq
    asked = re.findall(r'<details><summary>(.*?)</summary><p>.+?</p></details>', faq)
    assert asked == ['What is a model?', 'What is the market?', 'Can I check the picks?']
    assert ' open' not in faq, 'the answers wait to be asked'


def test_the_footer_links_reach_real_pages():
    links = re.findall(r'<a href="([^"]+)">', re.search(r'<footer class="home-links">(.*?)</footer>', PAGE, re.S).group(1))
    assert links == ['nfl/#method', 'nfl/#reliability', 'https://github.com/lifeisgreat07/NFL-Model-2']
    for page in ('method', 'reliability'):
        assert f'id="page-{page}"' in NFL_BODY, f'the NFL board has no {page} page to land on'


def test_the_theme_button_shares_every_page_s_key():
    block = re.search(r"\(function\(\)\{\n  const btn = document\.querySelector\('\.home-theme'\);.*?\}\)\(\);", JS, re.S)
    assert block, 'the theme button is not wired'
    assert "localStorage.setItem('site:theme'" in block.group(0)
    assert "localStorage.getItem('site:theme')" in PAGE, 'the page no longer reads the same key on load'


def function_source(name):
    """One top-level function of home.js: a one-line function, or the lines
    up to the closing brace at the start of a line."""
    lines = JS.splitlines()
    i = next(n for n, line in enumerate(lines) if line.startswith(f'function {name}('))
    if lines[i].rstrip().endswith('}'):
        return lines[i] + '\n'
    j = next(n for n in range(i + 1, len(lines)) if lines[n] == '}')
    return '\n'.join(lines[i:j + 1]) + '\n'


def scoreboard(home):
    funcs = ''.join(function_source(name) for name in ('esc', 'record', 'tile', 'scoreTile'))
    js = (funcs + f'const HOME = {json.dumps(home)};'
          "process.stdout.write(scoreTile(HOME.nfl, 'NFL, Model B') + '|' + scoreTile(HOME.nhl, 'NHL, picks'));")
    return subprocess.run([NODE, '-e', js], capture_output=True, encoding='utf-8', check=True).stdout.split('|')


@pytest.mark.skipif(not NODE, reason='node not available')
def test_the_scoreboard_counts_each_sports_graded_games():
    nfl, nhl = scoreboard({'nfl': {'built': True, 'record': {'won': 39, 'lost': 25}},
                           'nhl': {'built': True, 'record': {'won': 1, 'lost': 0}}})
    assert '<b>39–25</b>' in nfl and 'after 64 games' in nfl
    assert 'after 1 game<' in nhl


@pytest.mark.skipif(not NODE, reason='node not available')
def test_the_scoreboard_says_so_when_nothing_is_graded_or_built():
    nfl, nhl = scoreboard({'nfl': {'built': True, 'record': {'won': 0, 'lost': 0}}, 'nhl': {'built': False}})
    assert 'no graded games yet' in nfl
    assert 'page not built this time' in nhl
