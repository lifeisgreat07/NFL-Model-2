"""Model Lab is cards on a phone (Stage 18).

Below 768px the experiment table's rows become cards: the same markup and
reading order (name, result, decision), with only the boxes changed, so a
screen reader hears what it heard before and nothing scrolls sideways. The
breakpoint is measured, not the page's usual 640px: the table still scrolls
sideways at 640 and first fits at about 651 to 655px. The exact figure depends
on text rendering (two Chromium runs measured 651 and 655), so the guard holds
the breakpoint to the higher of the two.

Run with: pytest tests/test_model_lab_cards.py -v
"""
import re

from src.pipeline.template_parts import JOINED_TEMPLATE  # noqa: E402

TEMPLATE = JOINED_TEMPLATE
LOG = '#page-modellab .table-wrap[data-scroll-label="Experiment log"]'


def block():
    """The card block's width and body, read from the stylesheet with its
    comments blanked out, so a block that sits inside an unclosed comment
    (and so does nothing) is not found."""
    page = TEMPLATE.read_text(encoding='utf-8').replace('\r\n', '\n')
    css = re.search(r'<style>(.*?)</style>', page, re.S).group(1)
    src = re.sub(r'/\*.*?\*/', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), css, flags=re.S)
    at = src.find(LOG + ' :is(')
    assert at >= 0, ('the Model Lab card rules are not in the stylesheet outside a comment -- '
                     'is a comment above them left open?')
    start = src.rindex('@media', 0, at)
    m = re.match(r'@media \(max-width:(\d+)px\)\{\n((?:    [^\n]*\n)+)  \}', src[start:])
    assert m, ('the Model Lab card block is not findable outside a comment -- '
               'is a comment above it left open, or does the guard need re-anchoring?')
    return int(m.group(1)), m.group(2)


def rule(body, selector):
    m = re.search(re.escape(selector) + r'\{([^}]*)\}', body)
    return m.group(1).replace(' ', '') if m else None


def test_the_cards_start_below_the_width_the_table_first_fits():
    width, _ = block()
    assert width >= 655, f"at {width}px the table can still scroll sideways (measured: fits from about 651 to 655px)"


def test_rows_become_cards_only_in_the_experiment_log():
    _, body = block()
    assert rule(body, LOG + ' :is(table, tbody, tr, td)').startswith('display:block')
    for line in body.splitlines():
        if '{' in line and not line.strip().startswith('/*'):
            assert line.strip().startswith(LOG), f'a card rule escapes the experiment log: {line.strip()}'


def test_a_filtered_out_card_stays_hidden():
    """The display:block above would override the hidden attribute the
    decision filter sets, and every filtered row would come back."""
    _, body = block()
    assert rule(body, LOG + ' tr[hidden]') == 'display:none;'


def test_the_header_row_is_hidden_from_sight_not_from_assistive_technology():
    _, body = block()
    head = rule(body, LOG + ' thead')
    assert head and 'display:none' not in head and 'clip-path:inset(50%)' in head


def test_the_card_rules_are_live_css_not_a_comment():
    """An unclosed comment above the block swallows it: the page then shows
    the table on a phone, and every other test here would still read the
    rules from the raw text."""
    width, body = block()
    assert width and body.strip()
