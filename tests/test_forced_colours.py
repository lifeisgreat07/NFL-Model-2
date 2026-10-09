"""Windows' high-contrast themes (forced colours, Stage 47 item 10).

A forced-colours theme repaints every background with its one Canvas colour,
so a bar drawn as a background vanishes: Model B's split on every card and
the Net Rating bar showed empty tracks. Held here:
- the page keeps its own paint for those bars, in the theme's system colours,
  inside an outlined track;
- chips and badges gain an outline;
- the browser checks run a forced-colours pass that reports a bar matching
  what is behind it, with a fixture it must catch.

Checked once in Chromium with forced colours on. The checker reported the
card bars and both Net Rating bars on the page before these rules and nothing
after, and the cards and table were looked at.

Run with: pytest tests/test_forced_colours.py -v
"""
import re
from pathlib import Path

from src.core.template_parts import JOINED_TEMPLATE

ROOT = Path(__file__).resolve().parents[1]
SRC = JOINED_TEMPLATE.read_text(encoding='utf-8').replace('\r\n', '\n')
CHECKER = (ROOT / 'tests' / 'browser' / 'check_page.py').read_text(encoding='utf-8')


def block():
    blocks = re.findall(r'@media \(forced-colors: active\)\{(.*?)\n  \}', SRC, re.S)
    assert len(blocks) == 1, f'expected one forced-colours block, found {len(blocks)}'
    return blocks[0]


def test_the_bars_keep_their_own_paint_in_system_colours():
    b = block()
    assert '.tele-bar-seg, .srs-bar-fill{forced-color-adjust:none;}' in b
    assert '.tele-bar-seg:first-child{background:CanvasText !important;}' in b
    assert '.tele-bar-seg:last-child{background:Highlight !important;}' in b
    assert '.srs-bar-fill{background:Highlight !important;}' in b


def test_tracks_chips_and_badges_are_outlined():
    b = block()
    assert '.tele-bar, .srs-bar-track{border:1px solid CanvasText;}' in b
    rules = re.findall(r'^\s*([^{}\n]+)\{border:1px solid CanvasText;\}', b, re.M)
    outlined = {s.strip() for r in rules for s in r.split(',')}
    for sel in ('.model-chip', '.insight-chip', '.badge'):
        assert sel in outlined, sel


def test_the_browser_checks_run_a_forced_colours_pass_with_its_fixture():
    assert "forced_colors='active'" in CHECKER
    assert "FORCED_BARS = '.tele-bar-seg, .srs-bar-fill'" in CHECKER
    assert 'await check_forced_colours(browser, url, report)' in CHECKER
    assert "'forced': dict(" in CHECKER and "expect='forced colours'" in CHECKER


def test_every_bar_the_pass_watches_is_on_the_page():
    """A class the pass watches but the page no longer draws would make the
    pass check nothing."""
    for cls in ('tele-bar-seg', 'srs-bar-fill'):
        assert f'class="{cls}"' in SRC, cls
