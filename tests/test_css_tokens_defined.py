"""Every CSS custom property the template uses is declared somewhere.

Found 2026-09-28: `.card-status` (#134) set `color:var(--text-1)`, a token the
stylesheet never declares -- it has `--text`, `--text-2`, `--text-3` and
`--text-disabled`. An undefined custom property with no fallback makes the
declaration invalid at computed-value time, so the status line silently
inherited its colour from the card. Nothing failed, and a reader of the CSS
sees a colour that is not the one on the page.

So the guard is over the class, not the one line: every `var(--x)` without a
fallback must name a property declared in the template (`--x:` in a rule, or
set from script with `setProperty`). A `var(--x, fallback)` is allowed to
name an undeclared one, because it says what happens when it is missing.

Run with: pytest tests/test_css_tokens_defined.py -v
"""
import re
from pathlib import Path

from src.pipeline.template_parts import JOINED_TEMPLATE

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = JOINED_TEMPLATE

USE = re.compile(r'var\(\s*(--[\w-]+)\s*(,)?')
DECLARE = re.compile(r'(--[\w-]+)\s*:')
SET_FROM_SCRIPT = re.compile(r"setProperty\(\s*['\"](--[\w-]+)")


def undeclared(source):
    """[(token, line)] for every fallback-less var() naming an undeclared token."""
    declared = set(DECLARE.findall(source)) | set(SET_FROM_SCRIPT.findall(source))
    out = []
    for m in USE.finditer(source):
        if m.group(2) is None and m.group(1) not in declared:
            out.append((m.group(1), source.count('\n', 0, m.start()) + 1))
    return out


def test_every_token_the_template_uses_is_declared():
    missing = undeclared(TEMPLATE.read_text(encoding='utf-8'))
    assert not missing, (
        'var() names a custom property the template never declares, so that '
        'declaration is dropped and the element inherits instead: '
        + ', '.join(f'{t} (line {n})' for t, n in missing))


def test_the_check_can_fail():
    """Over synthetic CSS, because today's template reaches only the passing
    branch (CLAUDE.md: a guard whose failure needs data the repository does
    not contain needs synthetic inputs)."""
    css = ':root{--text:#fff;} .a{color:var(--text);} .b{color:var(--text-1);}'
    assert undeclared(css) == [('--text-1', 1)]
    assert undeclared(':root{--text:#fff;} .a{color:var(--gone, #000);}') == [], (
        'a var() with a fallback says what happens when the token is missing')
    assert undeclared(".a{color:var(--x);} el.style.setProperty('--x', '1px');") == []
