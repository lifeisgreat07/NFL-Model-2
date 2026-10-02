"""No text on the page is dimmed with opacity.

Stage 12 (CLAUDE.md). The first CI run of the browser checks found axe's
color-contrast on `.agent-stat-note`: --text-2 at opacity .8 on the stat
card's --border fill measured about 4.0:1 in the light theme, under WCAG
1.4.3's 4.5:1 for small text. The same idiom was used on five more text
rules. A sweep of every page in both themes found two of them failing where
axe cannot look (the sidebar's gradient background makes axe report "needs
review", not a violation): the "This Week" group labels at .7 and the
sidebar's "Updated ..." line at .75. The series toggles on Model Lab faded
their whole label to .45 when switched off, under 3:1 in both themes, in a
state no automated check reaches because it takes a click.

The palette's contrast is summed token against token; opacity sits outside
those sums. So text is dimmed with the neutral ramp, and opacity below 1 is
kept for things that carry no text. Every such rule is listed here with the
reason it is not text; a new one fails until it is looked at and listed.

Run with: pytest tests/test_no_dimmed_text.py -v
"""
import re
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / 'src' / 'pipeline' / 'dashboard_template.html'

# selector -> why an opacity below 1 is not dimming text
NOT_TEXT = {
    '.nav-btn svg': 'the sidebar icon beside the label, not the label',
    '.nav-btn.disabled': 'a disabled control; WCAG 1.4.3 exempts inactive UI',
    '.srs-bar-track.diverging::before': "the Net Rating bar's zero line",
    '.btn-chip.btn-toggle[aria-pressed="false"] svg': "a switched-off series' marker, not its label",
    '.btn-chip.btn-toggle[aria-pressed="false"]:hover svg': 'the same marker on hover',
    '.score-coin': "the scoreboard's 50% line",
    '.tele-bar-seg': 'an empty bar segment',
}
# Rules that dimmed text before Stage 12 and must not again.
# (.foot-freshness was one too; Stage 13 removed the rule when the "Updated"
# line moved to the Week Board header as .board-updated.)
WERE_DIMMED = ['.agent-stat-note', '.nav-group-label',
               '.btn-chip.btn-toggle[aria-pressed="false"]', '.track-note', '.dive-why-note',
               '.picks-readonly .pick-btn']


@pytest.fixture(scope='module')
def rules():
    """(selector, body) for every rule in the page's stylesheet, comments
    stripped, @media wrappers unwrapped, @keyframes dropped (a fade runs to
    opacity 1 and is not a resting state)."""
    src = TEMPLATE.read_text(encoding='utf-8')
    css = re.search(r'<style>(.*?)</style>', src, re.S).group(1)
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    css = re.sub(r'@keyframes[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}', '', css)
    css = re.sub(r'@media[^{]*\{', '', css)
    out = []
    for sel, body in re.findall(r'([^{}]+)\{([^{}]*)\}', css):
        for s in sel.split(','):
            out.append((' '.join(s.split()), body))
    return out


def resting_opacity(body):
    m = re.search(r'(?<![-\w])opacity\s*:\s*([0-9.]+)', body)
    return float(m.group(1)) if m else None


def test_every_partial_opacity_is_on_something_without_text(rules):
    found = {s for s, b in rules if (o := resting_opacity(b)) is not None and 0 < o < 1}
    assert found, 'no partial opacity found at all -- the stylesheet parse is broken'
    unlisted = sorted(found - set(NOT_TEXT))
    assert not unlisted, (
        f'opacity below 1 on {unlisted}: if it holds text, dim it with the neutral ramp '
        'instead; if not, list it in NOT_TEXT with the reason')


def test_the_list_holds_nothing_stale(rules):
    found = {s for s, b in rules if (o := resting_opacity(b)) is not None and 0 < o < 1}
    assert not sorted(set(NOT_TEXT) - found), 'NOT_TEXT names a rule that no longer exists'


def test_the_rules_that_dimmed_text_no_longer_do(rules):
    for sel in WERE_DIMMED:
        bodies = [b for s, b in rules if s == sel]
        assert bodies, f'{sel} is gone -- re-anchor this guard'
        assert all(resting_opacity(b) in (None, 1.0) for b in bodies), f'{sel} is dimmed with opacity again'


def test_a_switched_off_series_still_says_so(rules):
    """Losing the fade must not lose the state: the border goes dashed."""
    bodies = [b for s, b in rules if s == '.btn-chip.btn-toggle[aria-pressed="false"]']
    assert any(re.search(r'border-style\s*:\s*dashed', b) for b in bodies), (
        'a switched-off series toggle no longer looks different from a switched-on one')
