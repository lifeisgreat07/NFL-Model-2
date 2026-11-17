"""On a phone the home's sport cards come straight after its headline and action (audit 9 D16, first half).

At a phone's width the hero was 384 px tall and the first sport's card began 853 px down, below the first
screen. Under 600 px the hero's box gives way (display:contents) and the page orders its parts: the headline,
the one action, a starred team's games, the next games, the cards, then everything else in the page's own
order. Only parts that take no focus move: the focusable ones keep the order they have in the page, so a
keyboard meets them in the order they are seen (WCAG 2.4.3).

Run with: pytest tests/test_home_phone_order.py -v
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / 'src' / 'site' / 'home' / 'home.css').read_text(encoding='utf-8')
PAGE = (ROOT / 'src' / 'site' / 'home' / 'page.html').read_text(encoding='utf-8')
ORDER = [('.home-hero > .home-title', 1), ('.home-hero > .home-cta', 2), ('.page.active.home-page > #home-yours', 3),
         ('.page.active.home-page > #site-strip', 4), ('.page.active.home-page > #home-cards', 5)]


def phone_rules():
    m = re.search(r'/\* Audit 9 D16, first half:.*?\*/\n@media \(max-width: 600px\)\{(.*?)\n\}', CSS, re.S)
    assert m, 'the phone order block is gone'
    return {re.sub(r'\s+', ' ', s).strip(): b.strip() for s, b in re.findall(r'([^{}]+)\{([^{}]*)\}', m.group(1))}


def test_on_a_phone_the_cards_follow_the_headline_its_action_and_the_next_games():
    rules = phone_rules()
    assert rules['.home-hero'] == 'display:contents;', "the hero's parts must be the page's to order"
    assert rules['.page.active.home-page > *, .home-hero > *'] == 'order:10;', 'everything else after, in page order'
    for sel, n in ORDER:
        assert re.match(rf'order:{n};', rules[sel]), (sel, rules[sel])


def test_the_parts_that_take_focus_keep_the_pages_own_order():
    ids = ['id="home-cta"', 'id="home-yours"', 'id="site-strip"', 'id="home-cards"']
    at = [PAGE.index(i) for i in ids]
    assert at == sorted(at), 'the order seen on a phone is not the order the keyboard meets them'
    hero = PAGE[PAGE.index('<div class="home-hero">'):PAGE.index('</div>', PAGE.index('<div class="home-hero">'))]
    assert not re.search(r'<(a|button|input|select|details)\b', hero.replace('id="home-cta"', '')), \
        'a control in the hero other than the action would be met before the cards it now follows'
