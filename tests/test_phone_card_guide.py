"""On a phone, "How to read a card" opens the card guide where the cards are (Stage 77 item 29, the 2026-10-13 UI/UX audit's N4).

The phone's onboarding banner shows one line, "New here? How to read a
card", and the link went to #method: Methodology, 3,566 words with no
section on reading a card (measured at 390 px, both themes). It is now a
button that opens the banner's own three points and "How to read this" in
place, and says so with aria-expanded. Desktop is unchanged: the banner
shows the three points there already.

Run with: pytest tests/test_phone_card_guide.py -v
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'src' / 'dashboard' / 'app.js').read_text(encoding='utf-8')
BODY = (ROOT / 'src' / 'dashboard' / 'body.html').read_text(encoding='utf-8')
CSS = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')


def phone_css():
    phone = CSS[CSS.index('@media (max-width:640px){\n  .nfl-phone-only'):]
    return phone[:phone.index('\n}\n')]


def test_the_phone_line_opens_the_guide_here_not_methodology():
    assert '<p class="nfl-phone-only onboarding-phone">New here? <button type="button" class="btn btn-link" id="onboarding-phone-more" aria-expanded="false" aria-controls="onboarding-banner">How to read a card</button></p>' in BODY
    assert 'href="#method">How to read a card' not in BODY


def test_the_button_opens_and_closes_the_guide_and_says_which():
    fn = APP[APP.index('(function phoneOnboardingGuide(){'):]
    fn = fn[:fn.index('})();')]
    assert "banner.classList.toggle('onboarding-open', open);" in fn
    assert "btn.setAttribute('aria-expanded', String(open));" in fn


def test_open_shows_the_points_and_the_more_on_a_phone():
    phone = phone_css()
    assert ('  #onboarding-banner.onboarding-open .onboarding-content > ul,\n'
            '  #onboarding-banner.onboarding-open .onboarding-more{display:block;}') in phone
    # after the rule that hides them, so it wins
    assert phone.index('#onboarding-banner.onboarding-open .onboarding-more{display:block;}') > phone.index('  #onboarding-banner .onboarding-more{display:none;}')
    assert '.onboarding-phone .btn-link{font-size:inherit; min-height:24px;}' in phone
