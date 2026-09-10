"""The motion system, guarded statically.

These exist because Booth found the same class of defect twice by hand, and
nothing in this suite could have. On PR #51 the claim "prefers-reduced-motion
verified end to end -- every measured element reports 0s" was written after
measuring eight hand-picked selectors. Booth swept all 3,582 elements in a
headless browser and found 64 still animating: every `.tele-bar-seg`, at a
hardcoded `.4s`, because that one rule had never been wired to the duration
tokens. A user with reduced motion enabled still saw sixteen probability bars
animate on every Week Board render.

Why these are static parses rather than a browser sweep. The browser sweep is
what caught it, and it is the stronger check -- it reads computed styles, so
it cannot be fooled by a rule the parser misreads. But it needs Playwright and
a downloaded Chromium in CI, which is a heavy dependency for one property, and
it is slow enough that nobody would run it locally. The static version is
milliseconds, needs nothing, and catches the specific mistake that actually
happened: a literal duration written into a rule instead of a token. If a
browser-based check is ever added, it belongs beside these, not instead of
them.

The rule being guarded, stated once: every duration in the stylesheet is a
`--dur-*` token, so that the single `prefers-reduced-motion` block can collapse
all of them at once. A literal duration anywhere is invisible to that block.
"""
import re
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).parent.parent / 'src' / 'dashboard_template.html'


def stylesheet():
    src = TEMPLATE.read_text(encoding='utf-8')
    return src[src.index('<style'):src.index('</style>')]


def strip_comments(css):
    return re.sub(r'/\*.*?\*/', '', css, flags=re.S)


# A duration is legal if it is a token, or a literal zero. Zero is allowed
# because it is used deliberately -- `transition: visibility 0s linear
# var(--dur-slow)` holds a collapsing panel visible until its animation ends,
# and a zero there is not motion.
LEGAL_DURATION = re.compile(r'var\(\s*--dur-(fast|base|slow)\s*\)|(?<![\d.])0m?s\b')
ANY_DURATION = re.compile(r'(?<![\w.-])(\d*\.?\d+)(ms|s)\b')


def motion_declarations():
    """Every transition/animation declaration, comments removed."""
    css = strip_comments(stylesheet())
    return re.findall(r'(?:transition|animation)\s*:\s*([^;}]+)', css)


# The brand mark's three animations (bm-settle, bm-nudge, bm-tumble) are the one
# exemption, and it is narrow on purpose.
#
# The rule exists because a literal duration is INVISIBLE to the single
# prefers-reduced-motion block that collapses --dur-*. That reasoning does not
# reach these: the mark is switched off outright under reduced motion with
# `animation:none !important`, which is stronger than collapsing a duration to
# zero, and it swaps in a non-motion "busy" cue in its place. Tokenising them
# would also mean adding 320/480/700ms to a scale whose whole claim is that the
# dashboard's feel is four values.
#
# The exemption is only honest while that disabling rule exists, so the test
# below asserts it rather than trusting this comment.
BRAND_ANIMATIONS = ('bm-settle', 'bm-nudge', 'bm-tumble')


def test_every_duration_is_a_token():
    """A literal duration cannot be collapsed by the reduced-motion block.

    This is the exact defect Booth found: `.tele-bar-seg` carried
    `transition:width .4s cubic-bezier(...)`, which no amount of overriding
    `--dur-slow` could reach.
    """
    offenders = []
    for decl in motion_declarations():
        if any(name in decl for name in BRAND_ANIMATIONS):
            continue
        for m in ANY_DURATION.finditer(decl):
            span = decl[max(0, m.start() - 24):m.end() + 4]
            if not LEGAL_DURATION.search(span):
                offenders.append(decl.strip())
                break
    assert not offenders, (
        "these declarations carry a literal duration instead of a --dur-* token, so "
        "prefers-reduced-motion cannot collapse them:\n  " + "\n  ".join(offenders))


def test_the_brand_marks_exemption_is_paid_for():
    """The brand mark may use literal durations ONLY because it is switched off
    entirely under reduced motion. Delete that rule and the exemption above
    becomes a hole: three animations that a reduced-motion user still sees, and
    a test that no longer looks at them."""
    css = stylesheet()
    block = re.search(
        r'@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)\s*\{'
        r'[^{}]*\.brand-ball[^{}]*\{[^{}]*animation\s*:\s*none\s*!important',
        css, re.S)
    assert block, (
        "no @media (prefers-reduced-motion: reduce) rule sets "
        "`.brand-ball .spin { animation: none !important }`. Either restore it, "
        "or remove bm-settle/bm-nudge/bm-tumble from BRAND_ANIMATIONS so their "
        "durations are checked like everything else.")
    for name in BRAND_ANIMATIONS:
        assert name in css, f"{name} is exempted but no longer exists"


def test_reduced_motion_collapses_every_duration_token():
    """The one block that has to be right.

    If a fourth duration token is ever added and not listed here, every rule
    using it silently stops honouring the preference.
    """
    css = stylesheet()
    m = re.search(r'@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)\s*\{(.*?)\}\s*\}', css, re.S)
    assert m, "no prefers-reduced-motion block in the stylesheet"
    block = m.group(1)

    declared = set(re.findall(r'(--dur-[\w-]+)\s*:', strip_comments(css)))
    collapsed = {name for name, value in re.findall(r'(--dur-[\w-]+)\s*:\s*([^;]+);', block)
                 if re.fullmatch(r'0m?s', value.strip())}
    missing = declared - collapsed
    assert not missing, (
        f"declared duration tokens not set to 0 under reduced motion: {sorted(missing)}. "
        f"Every rule using them keeps animating for a user who asked for no motion.")


def test_transition_all_never_appears():
    """`transition: all` animates properties nobody chose.

    It was removed from `.pick-btn` and `.filter-btn`; the risk it leaves behind
    is that a future layout property starts animating by accident.
    """
    hits = [d.strip() for d in motion_declarations() if re.match(r'\s*all\b', d)]
    assert not hits, f"transition: all found -- name the properties instead: {hits}"


def test_every_hover_rule_sits_behind_the_hover_guard():
    """An unguarded :hover sticks after a tap.

    The phone layout has a bottom nav, so there are real touch users. This is a
    separate failure from the duration one but the same family: a rule that is
    correct on a desktop and wrong everywhere else.
    """
    css = strip_comments(stylesheet())
    guards = [m.start() for m in re.finditer(r'@media\s*\(\s*hover\s*:\s*hover\s*\)\s*\{', css)]
    assert guards, "no @media (hover: hover) block in the stylesheet"

    # Span of each guard block, by brace matching from its opening brace.
    spans = []
    for start in guards:
        i = css.index('{', start)
        depth, j = 0, i
        while j < len(css):
            if css[j] == '{':
                depth += 1
            elif css[j] == '}':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        spans.append((i, j))

    unguarded = []
    for m in re.finditer(r'([^\n{}]*:hover[^\n{}]*)\{', css):
        pos = m.start()
        if not any(a <= pos <= b for a, b in spans):
            unguarded.append(m.group(1).strip())
    assert not unguarded, (
        "these :hover rules are outside @media (hover: hover) and will stick "
        f"after a tap on touch: {unguarded}")


@pytest.mark.parametrize('token', ['--dur-fast', '--dur-base', '--dur-slow', '--ease', '--press'])
def test_the_motion_tokens_are_defined(token):
    """Named separately so a deletion says which token went missing."""
    assert re.search(rf'{token}\s*:', stylesheet()), f"{token} is not defined"


def test_there_is_exactly_one_easing_curve():
    """Seven durations and a scattering of eases is what this replaced.

    One curve is the whole point: the dashboard's feel is four values, and a
    second curve appearing means it has quietly become five.
    """
    css = strip_comments(stylesheet())
    body = re.sub(r'--ease\s*:[^;]+;', '', css)          # the definition itself is exempt
    strays = set(re.findall(r'cubic-bezier\([^)]*\)', body))
    strays |= {w for w in re.findall(r'\b(ease-in-out|ease-in|ease-out|linear)\b', body)
               if w != 'linear'}                          # `0s linear` is a delay, not a curve
    assert not strays, f"easing curves other than var(--ease): {sorted(strays)}"
