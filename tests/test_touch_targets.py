"""On a phone every tap target is 44 px (audit 9 D18).

The audit measured, at 375 px wide: the home's questions 24 px tall, its steps' links 20, its footer links 18
and its Settings button 24; the favourite star 24 by 24; filter chips 31 to 33; a table row's link 24. The
star, a chip and a row's link keep their size and gain a target around them, an ::after with no paint, so
nothing on the page moves; the home's questions, its steps' links, its footer links and its Settings button
are given the height. A link inside a sentence keeps its line (WCAG 2.5.8 exempts it).

Run with: pytest tests/test_touch_targets.py -v
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
HOME = (ROOT / 'src' / 'site' / 'home' / 'home.css').read_text(encoding='utf-8')


def phone_blocks(css):
    """The bodies of every @media (max-width:640px) block, each with its rules as {selector: body}."""
    out = {}
    for m in re.finditer(r'@media \(max-width:640px\)\{', css):
        depth, i = 1, m.end()
        while depth:
            depth += {'{': 1, '}': -1}.get(css[i], 0)
            i += 1
        for sel, body in re.findall(r'([^{}]+)\{([^{}]*)\}', css[m.end():i - 1]):
            out[re.sub(r'\s+', ' ', sel.split('*/')[-1]).strip()] = re.sub(r'\s+', ' ', body).strip()
    return out


def px(value):
    return float(re.match(r'-?(\d+(?:\.\d+)?)px', value).group(1))


def test_the_star_a_chip_and_a_row_link_gain_a_target_around_them_on_a_phone():
    rules = phone_blocks(SHARED)
    assert rules['.fav-star, .btn-chip, .row-link'] == 'position:relative;'
    # Each ::after reaches far enough to make the measured size 44: the star 24 + 2 x 10, a chip 31 + 2 x 7,
    # a row's link 24 + 2 x 10.
    for sel, size in (('.fav-star::after', 24), ('.btn-chip::after', 31), ('.row-link::after', 24)):
        body = rules[sel]
        assert "content:''" in body and 'position:absolute' in body, sel
        inset = re.search(r'inset:([^;]+);', body).group(1).split()
        assert size + 2 * px(inset[0]) >= 44, f'{sel}: {size} + 2 x {inset[0]} is under 44'
    assert rules['.home-settings'] == 'min-height:44px;'


def test_the_homes_questions_steps_and_footer_links_are_44_px_on_a_phone():
    rules = phone_blocks(HOME)
    for sel in ('.home-faq summary', '.home-step-link', '.home-links a'):
        assert 'min-height:44px' in rules[sel] and 'align-items:center' in rules[sel], sel
