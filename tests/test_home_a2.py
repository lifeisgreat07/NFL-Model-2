"""The home page as Mark chose on 2026-10-10: option A2 (Stage 68 item 34).

Inside option A (Stage 66): the hero gets one primary action, to the
sport whose next game starts first, and on a phone the three record tiles
sit in one compact row instead of a 279 px stack, so the first sport card
rises from y=679 to about 569 at 390 px (measured in Chromium on the
"Stage 68 Design Options" page).

Run with: pytest tests/test_home_a2.py -v
"""
import re

from src.site import home

PAGE = (home.TEMPLATE / 'page.html').read_text(encoding='utf-8')
JS = (home.TEMPLATE / 'home.js').read_text(encoding='utf-8')
CSS = (home.TEMPLATE / 'home.css').read_text(encoding='utf-8')


def phone_block():
    start = CSS.index('@media (max-width:600px){')
    return CSS[start:CSS.index('\n}\n', start)]


def test_the_hero_has_one_action_after_its_sub_line():
    hero = PAGE[PAGE.index('<div class="home-hero">'):PAGE.index('<div class="home-score"')]
    assert hero.index('class="home-sub"') < hero.index('<p class="home-cta" id="home-cta"></p>')


def test_the_action_goes_to_the_sport_with_the_next_game():
    assert 'ahead.sort((a, b) => a[1] - b[1]);' in JS and 'return ahead[0] || null;' in JS
    assert "if(!g){ box.remove(); return; }" in JS, 'no game ahead: no button, not an empty one'
    assert '<a class="home-cta-btn" href="${s}/">${esc(label)}' in JS


def test_the_records_are_one_row_on_a_phone():
    phone = phone_block()
    assert not re.search(r'\.home-score\{\s*grid-template-columns:1fr;', phone), 'the tiles stack again'
    assert '.home-tile b{ font-size:19px;' in phone


def test_the_button_is_a_full_tap_target():
    assert re.search(r'\.home-cta-btn\{[^}]*min-height:48px', CSS)
