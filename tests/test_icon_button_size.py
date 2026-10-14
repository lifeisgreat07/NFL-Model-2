"""
Stage 75 item 5 (the 2026-10-13 UI/UX audit): the week stepper's arrows are
40x40, from 28x28 beside 48x58 day chips; the 15px glyph is kept.

Measured 2026-10-13 on all three sports at 390 and 1440 px in both themes:
"Previous week" and "Next week" 28x28, glyph 15x15; after, 40x40 and 15x15.
`.btn-icon` is the stepper's only class and the shared stylesheet is every
sport's, so the rule is held here, with nothing else resizing it.

Run with: pytest tests/test_icon_button_size.py -v
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SHEETS = [REPO / 'src' / 'dashboard' / 'styles.css', REPO / 'src' / 'site' / 'home' / 'home.css',
          REPO / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.css', REPO / 'src' / 'sports' / 'nba' / 'pages' / 'nba.css']


def css_of(sheet):
    return re.sub(r'/\*.*?\*/', '', sheet.read_text(encoding='utf-8'), flags=re.S)


def rules(css, selector):
    return re.findall(r'(?:^|[}\s])' + re.escape(selector) + r'\s*\{([^}]*)\}', css)


def test_the_stepper_arrow_is_40_by_40_with_a_15px_glyph():
    css = css_of(SHEETS[0])
    (body,) = rules(css, '.btn-icon')
    assert 'width:40px' in body and 'height:40px' in body, body
    (glyph,) = rules(css, '.btn-icon svg')
    assert 'width:15px' in glyph and 'height:15px' in glyph, glyph


def test_no_other_rule_resizes_it():
    found = 0
    for sheet in SHEETS:
        css = css_of(sheet)
        for m in re.finditer(r'([^{}]*\.btn-icon[^{}]*)\{([^}]*)\}', css):
            found += 1
            sel, body = m.group(1).strip(), m.group(2)
            if sel == '.btn-icon' or sel.endswith('svg'):
                continue
            assert not re.search(r'(^|[;\s])(width|height|min-width|min-height|padding)\s*:', body), (sheet.name, sel, body)
    assert found >= 3, 'the scan found the .btn-icon rules'
