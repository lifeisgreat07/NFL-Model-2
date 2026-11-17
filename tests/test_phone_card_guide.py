""""How to read a card" opens the card guide where the cards are (Stage 77 item 29, the 2026-10-13 UI/UX audit's N4).

The phone's onboarding banner showed one line, "New here? How to read a
card", and the link went to #method: Methodology, 3,566 words with no
section on reading a card (measured at 390 px, both themes). It is a
button that opens the banner's own three points and "How to read this" in
place, and says so with aria-expanded.

Since audit 9 D4 the banner is that one line at every width: on a wide
screen it was a heading, three points and a disclosure, 217 px tall above
the board's cards on a first visit. The line and its Got it sit on one row.

Run with: pytest tests/test_phone_card_guide.py -v
"""
from pathlib import Path

from src.core.template_parts import APP_SCRIPT

ROOT = Path(__file__).resolve().parents[1]
APP = APP_SCRIPT.read_text(encoding='utf-8')
BODY = (ROOT / 'src' / 'dashboard' / 'body.html').read_text(encoding='utf-8')
CSS = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')


def phone_css():
    phone = CSS[CSS.index('@media (max-width:640px){\n  .nfl-phone-only'):]
    return phone[:phone.index('\n}\n')]


def base_css():
    """The stylesheet outside every @media block, where a rule holds at every width."""
    out, depth, i = [], 0, 0
    while i < len(CSS):
        if CSS.startswith('@media', i):
            j = CSS.index('{', i) + 1
            d = 1
            while d:
                d += {'{': 1, '}': -1}.get(CSS[j], 0)
                j += 1
            i = j
            continue
        out.append(CSS[i])
        i += 1
    return ''.join(out)


def test_the_line_opens_the_guide_here_not_methodology_at_every_width():
    assert '<p class="onboarding-phone">New here? <button type="button" class="btn btn-link" id="onboarding-phone-more" aria-expanded="false" aria-controls="onboarding-banner">How to read a card</button></p>' in BODY
    assert 'href="#method">How to read a card' not in BODY


def test_the_button_opens_and_closes_the_guide_and_says_which():
    fn = APP[APP.index('(function phoneOnboardingGuide(){'):]
    fn = fn[:fn.index('})();')]
    assert "banner.classList.toggle('onboarding-open', open);" in fn
    assert "btn.setAttribute('aria-expanded', String(open));" in fn


def test_closed_it_is_one_line_and_open_shows_the_points_and_the_more_at_every_width():
    base = base_css()
    hide = ('  #onboarding-banner .onboarding-content > h4,\n  #onboarding-banner .onboarding-content > ul,\n'
            '  #onboarding-banner .onboarding-more{display:none;}\n')
    show = ('  #onboarding-banner.onboarding-open .onboarding-content > ul,\n'
            '  #onboarding-banner.onboarding-open .onboarding-more{display:block;}')
    assert hide in base and show in base and base.index(show) > base.index(hide), 'open must come after, so it wins'
    assert '#onboarding-banner .onboarding-content{display:flex; flex-wrap:wrap; align-items:center;' in base
    assert '#onboarding-banner [data-act="dismiss-onboarding"]{margin-left:auto;}' in base, 'Got it on the same row'
    assert '.onboarding-phone .btn-link{font-size:inherit; min-height:24px;}' in base
    assert 'onboarding' not in phone_css(), 'nothing about the banner is left to a phone alone'
