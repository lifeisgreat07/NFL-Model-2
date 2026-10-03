"""Below 1080px a top bar carries the h1 and a theme button, and the page's
foot carries the provenance line (Stage 26 item 3).

The sidebar holds all three and is hidden below 1080px, so a phone had no
h1, no theme toggle and no line saying what built the page. Mark picked the
top bar on 2026-09-28 from rendered side-by-sides of three treatments. The
bar and the line are display:none at desktop widths, where the sidebar shows
its own, so exactly one h1 is ever rendered. Checked in a browser at 375
and 1280 for the PR; held here by source, as the suite has no browser.
"""
import re
from pathlib import Path

from src.pipeline.template_parts import read_template  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = read_template()


def css():
    return TEMPLATE[:TEMPLATE.index('</style>')]


def phone_block():
    m = re.search(r'@media \(max-width:1079px\)\{\n    body\{flex-direction:column;\}(.*?)\n  \}\n', css(), re.S)
    assert m, 'the below-1080px block is not findable -- re-anchor this test'
    return m.group(1)


def test_the_bar_and_the_line_are_hidden_at_desktop_widths():
    assert '.topbar, .page-prov{display:none;}' in css()
    block = phone_block()
    assert '.sidebar{display:none;}' in block
    assert re.search(r'\.topbar\{display:flex;', block), 'the top bar is not shown below 1080px'
    assert re.search(r'\.page-prov\{display:block;', block), 'the provenance line is not shown below 1080px'


def test_the_bar_holds_the_h1_and_a_theme_button_before_main():
    bar = re.search(r'<header class="topbar">(.*?)</header>\s*<main id="main-content"', TEMPLATE, re.S)
    assert bar, 'the top bar is not directly before <main>'
    assert re.search(r'<h1>Pick\'em Model <span class="topbar-sub">Weekly NFL picks, graded</span></h1>', bar.group(1))
    assert '<button type="button" class="topbar-theme" aria-label="Toggle light and dark theme">' in bar.group(1)
    assert '<svg class="brand-ball" viewBox="0 0 20 20" aria-hidden="true">' in bar.group(1), (
        'the ball in the bar should be decoration; the h1 names the site')


def test_both_theme_buttons_toggle_the_theme():
    init = re.search(r'\(function initTheme\(\)\{.*?\n\}\)\(\);', TEMPLATE, re.S).group(0)
    assert "document.querySelectorAll('#theme-toggle, .topbar-theme').forEach(btn => btn.addEventListener('click'" in init


def test_the_bar_is_a_real_target_and_stays_put():
    block = phone_block()
    assert re.search(r'\.topbar\{[^}]*position:sticky; top:0;', block)
    assert re.search(r'\.topbar-theme\{[^}]*width:40px; height:40px;', block), 'the theme button is under 40px'


def test_the_provenance_line_ends_main_and_is_filled_by_the_build():
    assert re.search(r'<p class="page-prov">__SIDEBAR_FOOT__</p>\n</main>', TEMPLATE.replace('\r\n', '\n'))
    from src.pipeline import generate_dashboard as gd
    assert 'built from NFL play-by-play since' in gd.provenance_line()
