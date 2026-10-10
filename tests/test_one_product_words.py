"""The three sport pages speak as one product (Stage 68 item 18b).

The 2026-10-09 audit found four title patterns (U13), three sub-line
shapes (U14), a wordmark that went home only from the home page (U12), the
season pulse on two pages of three (U21), rows saying Right/Wrong where
everything else says Correct/Missed (U26), and 10 px goalie pills under the
type scale's 11 px floor (U30).

Run with: pytest tests/test_one_product_words.py -v
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPORTS = {
    'NFL': ('src/dashboard/page.html', 'src/dashboard/body.html', 'src/dashboard/app.js', 'Week Board', 'Weekly'),
    'NHL': ('src/sports/nhl/pages/page.html', 'src/sports/nhl/pages/body.html', 'src/sports/nhl/pages/nhl.js', 'Day Board', 'Daily'),
    'NBA': ('src/sports/nba/pages/page.html', 'src/sports/nba/pages/body.html', 'src/sports/nba/pages/nba.js', 'Day Board', 'Daily'),
}


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


@pytest.mark.parametrize('sport', SPORTS)
def test_one_title_rule(sport):
    page, _, js, board, _ = SPORTS[sport]
    assert f'<title>{sport} {board} — Sportalytics</title>' in read(page)
    assert f': `{sport} ${{heading.textContent.trim()}} — Sportalytics`;' in read(js)


@pytest.mark.parametrize('sport', SPORTS)
def test_one_sub_line_shape(sport):
    _, body, _, _, cadence = SPORTS[sport]
    assert f'<div class="brand-sub">{cadence} {sport} picks, graded</div>' in read(body)


@pytest.mark.parametrize('sport', SPORTS)
def test_the_wordmark_goes_home_and_the_season_pulses(sport):
    body = read(SPORTS[sport][1])
    assert '<h1 class="wordmark"><a class="wordmark-link" href="../">' in body
    assert re.search(r'<div class="brand-mark"><span class="pulse"></span>Season ', body)


@pytest.mark.parametrize('sport', ['NHL', 'NBA'])
def test_rows_say_correct_or_missed(sport):
    js = read(SPORTS[sport][2])
    assert "{text: 'Correct', cls: 'right'}" in js and "{text: 'Missed', cls: 'wrong'}" in js
    assert "text: 'Right'" not in js and "text: 'Wrong'" not in js


def test_goalie_pills_are_on_the_type_scale():
    assert re.search(r'\.nhl-goalie\{[^}]*font-size:var\(--fs-11\)', read('src/sports/nhl/pages/nhl.css'))
