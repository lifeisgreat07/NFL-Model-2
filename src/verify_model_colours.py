"""Regenerate the colour figures the Stage 11 model-identity comments state.

Those comments carry five measured numbers -- how far apart Model A's dot and
the pick tick are, in both themes, under normal vision and under red-green
colour vision deficiency, plus how far apart the chart series are. They are in
PERMANENT SOURCE COMMENTS, which this repository's history says is the worst
place for an unverified number: it outlives the pull request and is read by
people who cannot see the diff that would contradict it.

So they are computed here rather than quoted, and
tests/test_model_colour_comment.py asserts the comment agrees with this script.
Same arrangement as src/verify_matchup_cvd.py, which exists for the same reason
after Booth found the matchup figures unreproducible on PR #52.

Every choice a number depends on is named, because the PR #52 lesson was that
two people can agree on a figure while measuring different objects:

  * Tokens are PARSED out of src/dashboard_template.html, never copied, so this
    cannot drift from the palette it describes.
  * Distance is CIEDE2000 on sRGB -> Lab (D65), reusing the implementation in
    verify_matchup_cvd.py rather than keeping a second copy of colour science.
  * CVD is Machado 2009 at severity 1.0, protanopia and deuteranopia only --
    the common red-green types. The reported figure is the MINIMUM across
    those two, i.e. the worst case for a reader.
  * Colours are compared AS THE TOKENS ARE. This is the part that is easy to
    get wrong: verify_matchup_cvd.worst_dE() applies matchupColors()' shading
    push before simulating, because two team fills that touch in a bar really
    are pushed apart before anyone sees them. Tokens are not. Calling that
    function here reported 34.1 dE00 for a pair that is actually 10.8 -- the
    shading was doing the separating, and the figure would have been wrong in
    the safe direction, which is the kind nobody checks.

Run:  python src/verify_model_colours.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import verify_matchup_cvd as v  # noqa: E402

TEMPLATE = ROOT / 'src' / 'dashboard_template.html'

#: The pairs worth reporting, and why each one is here.
PAIRS = (
    ('--series-a', '--accent',
     "Model A's dot against the pick tick -- the residual this work leaves "
     "behind. Not a defect while they never share a view; the pair to "
     "re-measure if they ever land side by side."),
    ('--series-a', '--series-b',
     "the two model series as the CHARTS draw them. The point of comparison: "
     "prose used to draw the same two models far closer than this."),
)


def _source():
    return TEMPLATE.read_text(encoding='utf-8')


def theme_block(name, src=None):
    """The custom-property block for a theme.

    Dark is the bare `:root`; light is `[data-theme="light"]`. Matched
    separately rather than by scanning for the first `{...}` after a keyword,
    because the two blocks define the same token names and picking the wrong
    one produces plausible numbers for the wrong theme.
    """
    src = src or _source()
    if name == 'dark':
        m = re.search(r':root\s*\{(.*?)\}', src, re.S)
    else:
        m = re.search(r"\[data-theme=['\"]light['\"]\]\s*\{(.*?)\}", src, re.S)
    if not m:
        raise SystemExit(f'no {name}-theme custom-property block found')
    return m.group(1)


def token(block, name):
    m = re.search(re.escape(name) + r'\s*:\s*(#[0-9A-Fa-f]{3,8})', block)
    if not m:
        raise SystemExit(f'token {name} not found in this theme block')
    return m.group(1)


def distances(a_hex, b_hex):
    """(normal-vision dE00, worst dE00 over the red-green CVD types).

    Deliberately NOT verify_matchup_cvd.worst_dE -- see this module's
    docstring. These are raw tokens; nothing pushes them apart first.
    """
    ra, rb = v.hex_to_rgb(a_hex), v.hex_to_rgb(b_hex)
    normal = v.ciede2000(v.rgb_to_lab(ra), v.rgb_to_lab(rb))
    worst = min(
        v.ciede2000(v.rgb_to_lab(v.simulate(ra, kind)),
                    v.rgb_to_lab(v.simulate(rb, kind)))
        for kind in v.MACHADO)
    return normal, worst


def measure():
    """{theme: {(token_a, token_b): (hex_a, hex_b, normal, worst)}}"""
    src = _source()
    out = {}
    for theme in ('dark', 'light'):
        block = theme_block(theme, src)
        out[theme] = {}
        for a, b, _why in PAIRS:
            ha, hb = token(block, a), token(block, b)
            out[theme][(a, b)] = (ha, hb) + distances(ha, hb)
    return out


def report():
    data = measure()
    print('CIEDE2000, sRGB->Lab (D65). CVD: Machado 2009 severity 1.0,')
    print('protanopia and deuteranopia, worst (minimum) of the two.')
    print('Tokens parsed from src/dashboard_template.html.\n')
    for theme in ('dark', 'light'):
        print(f'{theme}:')
        for a, b, why in PAIRS:
            ha, hb, normal, worst = data[theme][(a, b)]
            print(f'  {a} {ha}  vs  {b} {hb}')
            print(f'      normal {normal:.1f}   worst under red-green CVD {worst:.1f}')
            print(f'      {why}')
        print()
    print('The dataviz floor is 15 dE00; below it a pair needs a secondary')
    print('encoding to be distinguishable. The model chip is exactly that:')
    print('the dot carries identity, the words next to it wear --text.')


if __name__ == '__main__':
    report()
