"""
The sort mark on Power Ratings' headers: what the CSS promises.

Stage 34 item 29, from the 2026-09-29 re-audit, which found the "#" header
styled like the headers that sort. At rest every header looked alike, so
nothing on screen said which ones sort. Mark chose the fix from rendered
options: every header that sorts shows a faint up-down mark, the sorted one
an arrow for its direction, and "#" (the net-rating rank, which is not a
control) shows none.

What a reader SEES is checked in the browser (tests/browser/check_page.py,
the sortmark rule, on every page at every width). This file checks what a
static read can: that each of the three states has its rule, that the mark
is silent to screen readers (they are told the sort through aria-sort
already), and that "#" is still not a control.

Run with: pytest tests/test_sort_marks.py -v
"""
import re
from pathlib import Path

TEMPLATE = Path(__file__).parent.parent / 'src' / 'pipeline' / 'dashboard_template.html'
GLYPH = {'none': r'\2195', 'descending': r'\25BC', 'ascending': r'\25B2'}


def css():
    html = TEMPLATE.read_text(encoding='utf-8')
    return html[:html.index('</style>')]


def rule_for(text, state):
    """The declaration block whose selector marks headers in this state."""
    sel = r'thead th\[aria-sort\]' if state == 'none' else rf'thead th\[aria-sort={state}\]'
    m = re.search(sel + r':not\(:has\(\.net-head\)\)::after,\s*'
                  + sel + r' \.net-head > span:first-child::after\{([^}]*)\}', text)
    return m.group(1) if m else None


def test_each_sort_state_draws_its_own_mark():
    text = css()
    for state, glyph in GLYPH.items():
        body = rule_for(text, state)
        assert body is not None, f"no sort-mark rule for aria-sort={state}"
        assert f"content:'{glyph}'" in body, f"aria-sort={state} does not draw {glyph}"


def test_every_mark_is_silent_to_a_screen_reader():
    """aria-sort already tells a screen reader the sort. Without the empty
    alt text the mark would also be read out, as "up down arrow"."""
    text = css()
    for state, glyph in GLYPH.items():
        body = rule_for(text, state) or ''
        assert f"content:'{glyph}' / ''" in body, (
            f"the aria-sort={state} mark has no empty alt text, so it is read out")


def test_the_rank_column_is_not_a_control():
    """'#' is each team's net-rating rank and stays put when another column
    sorts, so sorting by it would only repeat Net Rating. It carries no
    aria-sort, so it draws no mark and takes no focus."""
    html = TEMPLATE.read_text(encoding='utf-8')
    m = re.search(r'<th scope="col" data-key="rank"([^>]*)>#</th>', html)
    assert m, "the '#' header was not found; re-anchor this guard"
    assert 'aria-sort' not in m.group(1) and 'tabindex' not in m.group(1), m.group(0)


def test_a_missing_state_is_caught():
    """Synthetic, so the failing branch stays reachable while all three exist."""
    text = css().replace("th[aria-sort=ascending]", "th[aria-sort=up]")
    assert rule_for(text, 'ascending') is None
