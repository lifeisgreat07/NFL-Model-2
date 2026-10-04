"""The first card's per-model rows stay retired (Stage 17).

Card v2 (#146) replaced the Week Board card's two per-model rows
(`.model-row`, `.model-label`, `.tele`, `.tele-team`, `.tele-logo`,
`.tele-marker`) with one headline, one bar and one probability line. Their
rules outlived them, and Stage 17 removed them. This holds that: no rule for
them in the stylesheet, and no element wearing them in the markup or the
script. `.tele-bar` and `.tele-bar-seg` are NOT on the list: card v2 still
draws its bar with them.

Run with: pytest tests/test_retired_card_css.py -v
"""
import re

from src.pipeline.template_parts import JOINED_TEMPLATE

TEMPLATE = JOINED_TEMPLATE
RETIRED = ('model-row', 'model-label', 'tele', 'tele-team', 'tele-logo', 'tele-marker')


def token(name):
    """The class name as a whole token: `tele` must not match `tele-bar`."""
    return re.compile(r'(?<![\w-])' + re.escape(name) + r'(?![\w-])')


def test_no_rule_styles_a_retired_class():
    src = TEMPLATE.read_text(encoding='utf-8')
    css = re.search(r'<style>(.*?)</style>', src, re.S).group(1)
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    back = [n for n in RETIRED if re.search(r'\.' + re.escape(n) + r'(?![\w-])', css)]
    assert not back, f'a rule styles {back} again; nothing on the page wears them'


def test_nothing_wears_a_retired_class():
    src = TEMPLATE.read_text(encoding='utf-8')
    rest = src[src.index('</style>'):]
    rest = re.sub(r'/\*.*?\*/|<!--.*?-->', '', rest, flags=re.S)
    worn = [n for n in RETIRED if token(n).search(' '.join(re.findall(r'class="([^"]*)"', rest)))]
    assert not worn, f'markup wears {worn}, which have no rules any more'


def test_the_bar_classes_card_v2_uses_are_still_styled():
    """The rule whose selector IS the class, at the start of a line. A bare
    substring check passed with `.tele-bar` deleted, because
    `.card-scale .tele-bar{...}` contains the same text (the mutation corpus
    found that on this PR's first run)."""
    src = TEMPLATE.read_text(encoding='utf-8')
    for name in ('tele-bar', 'tele-bar-seg'):
        assert re.search(r'(?m)^[ \t]*\.' + re.escape(name) + r'\{', src), (
            f'.{name} has no rule of its own, and card v2 draws its bar with it')
