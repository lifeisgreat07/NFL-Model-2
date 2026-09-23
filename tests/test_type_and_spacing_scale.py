"""
The page on its type and spacing scales (Stage 10, 2026-09-23).

Stage 8 defined an eight-step type scale (--fs-11 ... --fs-32) and a 4px
spacing scale (--s1 ... --s9), and CLAUDE.md recorded the audit's
foundations list as "satisfied by the token block". It was not. The
Stage 10 audit re-run counted 106 literal font sizes against 10 uses of the
scale, 232 literal spacing declarations against 17, and 21 distinct font
sizes on the rendered page -- the count the original audit had flagged.
A token block that nothing uses is a proposal, not a system.

So the rule is stated about the whole template, outside comments: a
font-size is a scale token, and a padding / margin / gap length is a
spacing token. What is allowed to stay literal is named below, each with
its reason.

Run with: pytest tests/test_type_and_spacing_scale.py -v
"""
import re
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).parent.parent / 'src' / 'dashboard_template.html'

SPACING_PROP = re.compile(
    r'(?<![\w-])((?:padding|margin)(?:-(?:top|right|bottom|left|block|inline)(?:-(?:start|end))?)?'
    r'|gap|row-gap|column-gap)\s*:\s*([^;}"]*)')

#: Literal spacing lengths that stay, and why. Anything else is a finding.
ALLOWED_SPACING = {
    # Hairlines: a 1-2px nudge is an optical correction, not rhythm, and
    # rounding it to 4px would move things a whole step.
    'hairline': lambda n: abs(n) <= 2,
    # <main>'s 60px bottom padding on desktop: room at the end of a page,
    # larger than the scale's top step (48px), and there is exactly one.
    'page end': lambda n: n == 60,
}


def strip_comments(src):
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    return re.sub(r'<!--.*?-->', '', src, flags=re.S)


def literal_font_sizes(src):
    return re.findall(r'font-size\s*:\s*(\d+(?:\.\d+)?px)', strip_comments(src))


def literal_spacing(src):
    """Spacing lengths written in px outside calc(), and not allowed above."""
    found = []
    for m in SPACING_PROP.finditer(strip_comments(src)):
        value = re.sub(r'calc\([^)]*\)', '', m.group(2))
        for n in re.findall(r'(?<![\w.])(-?\d+(?:\.\d+)?)px', value):
            if not any(ok(float(n)) for ok in ALLOWED_SPACING.values()):
                found.append(f'{m.group(1)}: {m.group(2).strip()}')
    return found


def declared_tokens(src, prefix):
    root = re.search(r':root\s*\{(.*?)\n\s*\}', src, re.S)
    assert root, ':root block not found -- re-anchor this guard'
    return set(re.findall(r'(--' + prefix + r'[\w-]+)\s*:', root.group(1)))


@pytest.fixture(scope='module')
def src():
    return TEMPLATE.read_text(encoding='utf-8')


def test_every_font_size_is_on_the_scale(src):
    lits = literal_font_sizes(src)
    assert not lits, f'font sizes off the type scale: {sorted(set(lits))}. Use var(--fs-N).'


def test_every_spacing_length_is_on_the_scale(src):
    lits = literal_spacing(src)
    assert not lits, 'spacing off the 4px scale:\n  ' + '\n  '.join(lits[:20])


def test_every_scale_token_used_is_declared(src):
    body = strip_comments(src)
    used_fs = set(re.findall(r'var\((--fs-\d+)\)', body))
    used_s = set(re.findall(r'var\((--s\d)\)', body))
    assert used_fs <= declared_tokens(src, 'fs-'), used_fs - declared_tokens(src, 'fs-')
    assert used_s <= declared_tokens(src, 's'), used_s - declared_tokens(src, 's')


def test_the_scales_are_actually_used(src):
    """Vacuity guard: the rules above pass trivially on a page with no type
    at all. Pin that the tokens carry the page."""
    body = strip_comments(src)
    assert len(re.findall(r'font-size\s*:\s*var\(--fs-', body)) >= 100
    assert len(re.findall(r'var\(--s\d\)', body)) >= 200


@pytest.mark.parametrize('css, fonts, spacing', [
    ('.a{font-size:12.5px; padding:10px 14px;}', 1, 2),
    ('.a{font-size:var(--fs-12); padding:var(--s2) var(--s3);}', 0, 0),
    ('.a{margin-top:1px; margin-left:-1px;}', 0, 0),
    ('.a{padding:calc(88px + var(--safe-bottom));}', 0, 0),
    ('/* font-size:12.5px; padding:10px */', 0, 0),
    ('<div style="margin-top:11px;">', 0, 1),
])
def test_the_rules_over_synthetic_css(css, fonts, spacing):
    assert len(literal_font_sizes(css)) == fonts
    assert len(literal_spacing(css)) == spacing
