"""A page state's border is visible in both themes (Stage 79 item 50, the 2026-10-13 UI/UX audit's C2 and V7).

Every sport's empty, waiting and missing states share .state (src/dashboard/
styles.css). Its dashed border was --border, 1.24:1 on --surface in both
themes (computed 2026-10-14 from the tokens), so in light mode the dashed
"not yet" could not be told from the solid "missing" except by the missing
state's left rule. It is --border-strong now, 1.50:1 dark and 1.54:1 light;
the audit asked for 1.5:1.

Run with: pytest tests/test_state_borders.py -v
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')


def tokens(block_start):
    block = CSS[CSS.index(block_start):]
    block = block[:block.index('}')]
    return dict(re.findall(r'--(n\d):(#[0-9A-Fa-f]{6})', block))


def luminance(hex_):
    def ch(v):
        v = int(v, 16) / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(hex_[i:i + 2]) for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def state_border_token():
    rule = re.search(r'\n  \.state\{[^}]*\}', CSS).group(0)
    m = re.search(r'border:1px dashed var\(--([\w-]+)\);', rule)
    assert m, 'the state no longer draws a dashed border -- re-anchor this guard'
    return m.group(1)


def test_the_state_border_reaches_1_5_to_1_in_both_themes():
    # --border is --n3, --border-strong --n4, and --surface --n1 in both themes.
    assert '--surface:var(--n1);' in CSS and '--border:var(--n3); --border-strong:var(--n4);' in CSS
    n = {'border': 'n3', 'border-strong': 'n4'}[state_border_token()]
    for name, start in (('dark', ':root{'), ('light', '[data-theme="light"]{')):
        t = tokens(start)
        assert ratio(t[n], t['n1']) >= 1.5, f'{name}: {ratio(t[n], t["n1"]):.2f}:1'


def test_missing_is_still_solid_with_its_rule():
    assert '.state--missing{border-style:solid; border-left:3px solid var(--border-strong);}' in CSS
