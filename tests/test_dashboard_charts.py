"""
Guards on the dashboard's chart layer.

Two things are checked here, and they fail for different reasons.

1. WIRING -- data/calibration.json actually reaches the page, the template's
   placeholders are all filled, and a checkout without that file still builds.
   These catch the ordinary regression: someone edits generate_dashboard.py
   and the reliability diagram silently disappears, or worse, ships with a
   literal "__CALIBRATION_JSON__" in it.

2. THE PALETTE ITSELF -- the --series-* colours are re-measured from the
   template on every run: OKLab distance under normal vision, under simulated
   protanopia and deuteranopia (Machado, Oliveira & Fernandes 2009, severity
   1.0), OKLCH lightness and chroma, and WCAG contrast against each theme's
   own chart surface.

   The maths is reimplemented here rather than imported, deliberately. These
   colours were produced by a tool that lives outside this repo, and a test
   that only asserted "the hexes are still the strings I wrote down" would
   pass just as happily for a wrong value someone pasted in confidently. It
   would also say nothing about WHY those values are the ones. This way the
   test states the property -- these colours are far enough apart to tell
   apart, in both themes, including for a red-green colourblind reader -- and
   any future change has to satisfy the property, not match a hash.

   The live dashboard genuinely failed this before 2026-09-04: in light mode
   the market line (--chalk-dim) and Model B (--amber) sat at normal-vision
   dE 13.8, under the floor of 15. That is the regression this locks down.

Run with: pytest tests/test_dashboard_charts.py -v
"""
import json
import math
import re
import subprocess
import sys
import tempfile
from itertools import combinations
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
TEMPLATE = REPO_ROOT / 'src' / 'dashboard_template.html'
CALIBRATION = REPO_ROOT / 'data' / 'calibration.json'

# Thresholds, from the data-viz checks. CVD_TARGET is the pass mark for the
# minimum of the protan and deutan distances; NORMAL_FLOOR is a hard gate --
# a pair below it is hard to tell apart even with full colour vision, and no
# amount of secondary encoding excuses that one.
CVD_TARGET = 8.0
NORMAL_FLOOR = 15.0
CONTRAST_MIN = 3.0
BAND = {'light': (0.43, 0.77), 'dark': (0.48, 0.67)}   # OKLCH L
CHROMA_FLOOR = 0.10                                     # OKLCH C

# Each theme's chart surface is --panel, because .method-block (which every
# chart sits inside) is painted with it.
SURFACE = {'dark': '#131826', 'light': '#FFFFFF'}

MACHADO = {
    'protan': ((0.152286, 1.052583, -0.204868),
               (0.114503, 0.786281, 0.099216),
               (-0.003882, -0.048116, 1.051998)),
    'deutan': ((0.367322, 0.860646, -0.227968),
               (0.280085, 0.672501, 0.047413),
               (-0.011820, 0.042940, 0.968881)),
}


# ============================================================
# Colour maths (see module docstring for why this is not imported)
# ============================================================
def _srgb(hex_str):
    h = hex_str.strip().lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _linear(hex_str):
    def f(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(f(c) for c in _srgb(hex_str))


def _oklab_from_linear(rgb):
    r, g, b = rgb
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def _simulate(rgb, kind):
    M = MACHADO[kind]
    return tuple(min(1.0, max(0.0, sum(M[i][j] * rgb[j] for j in range(3)))) for i in range(3))


def delta_e(a, b, kind=None):
    """Euclidean distance in OKLab, x100. kind=None is unsimulated vision."""
    la, lb = _linear(a), _linear(b)
    if kind:
        la, lb = _simulate(la, kind), _simulate(lb, kind)
    pa, pb = _oklab_from_linear(la), _oklab_from_linear(lb)
    return 100 * math.dist(pa, pb)


def oklch(hex_str):
    L, a, b = _oklab_from_linear(_linear(hex_str))
    return L, math.hypot(a, b)


def contrast(a, b):
    def lum(h):
        r, g, bl = _linear(h)
        return 0.2126 * r + 0.7152 * g + 0.0722 * bl
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_colour_maths_matches_a_known_value():
    """Anchor the reimplementation before trusting anything it says.

    Black-to-white in OKLab is the L axis end to end: L runs 0 to 1, a and b
    are 0 for both, so the distance is exactly 100. If this drifts, every
    threshold below is being measured with the wrong ruler."""
    assert delta_e('#000000', '#FFFFFF') == pytest.approx(100.0, abs=0.5)
    assert contrast('#000000', '#FFFFFF') == pytest.approx(21.0, abs=0.01)
    L_white, C_white = oklch('#FFFFFF')
    assert L_white == pytest.approx(1.0, abs=0.01)
    assert C_white == pytest.approx(0.0, abs=0.01)


# ============================================================
# Reading the tokens back out of the template
# ============================================================
def series_tokens(theme):
    """The four --series-* values as the template actually defines them for a
    theme. Parsed from the file rather than hardcoded, so the test measures
    what ships."""
    src = TEMPLATE.read_text()
    # :root{...} is the dark theme; [data-theme="light"]{...} overrides it.
    marker = ':root{' if theme == 'dark' else '[data-theme="light"]{'
    start = src.index(marker)
    block = src[start:src.index('}', start)]
    out = {}
    for slot in 'abcd':
        m = re.search(rf'--series-{slot}\s*:\s*(#[0-9A-Fa-f]{{6}})', block)
        assert m, f"--series-{slot} missing from the {theme} theme block"
        out[slot] = m.group(1).upper()
    return out


@pytest.mark.parametrize('theme', ['dark', 'light'])
def test_every_theme_defines_all_four_series_tokens(theme):
    tokens = series_tokens(theme)
    assert len(set(tokens.values())) == 4, f"duplicate series colours in {theme}: {tokens}"


@pytest.mark.parametrize('theme', ['dark', 'light'])
def test_series_lightness_and_chroma_are_in_band(theme):
    """Outside the band a mark either glares or sinks into the surface; below
    the chroma floor it stops reading as a hue at all and becomes 'the grey
    one', which is not an identity a fourth series can have."""
    lo, hi = BAND[theme]
    for slot, hex_str in series_tokens(theme).items():
        L, C = oklch(hex_str)
        assert lo <= L <= hi, f"{theme} --series-{slot} {hex_str}: L={L:.3f} outside {lo}-{hi}"
        assert C >= CHROMA_FLOOR, f"{theme} --series-{slot} {hex_str}: C={C:.3f} reads gray"


@pytest.mark.parametrize('theme', ['dark', 'light'])
def test_reliability_diagram_trio_separates_under_every_pairing(theme):
    """Model A, Model B and the market are drawn as overlapping dots on one
    plot, so EVERY pair has to separate -- not just neighbours in the palette
    order. This is the strict case."""
    t = series_tokens(theme)
    trio = {'a': t['a'], 'b': t['b'], 'c': t['c']}
    for (n1, c1), (n2, c2) in combinations(trio.items(), 2):
        cvd = min(delta_e(c1, c2, 'protan'), delta_e(c1, c2, 'deutan'))
        assert cvd >= CVD_TARGET, (
            f"{theme}: series-{n1} {c1} and series-{n2} {c2} are dE {cvd:.1f} apart "
            f"under red-green colourblindness (need {CVD_TARGET})")
        normal = delta_e(c1, c2)
        assert normal >= NORMAL_FLOOR, (
            f"{theme}: series-{n1} {c1} and series-{n2} {c2} are dE {normal:.1f} apart "
            f"for a full-colour reader (hard floor {NORMAL_FLOOR})")


@pytest.mark.parametrize('theme', ['dark', 'light'])
def test_line_chart_quartet_separates_between_neighbours(theme):
    """The cumulative-accuracy chart adds My Picks as a fourth line. Lines are
    separated in space as well as colour, so the CVD gate applies to adjacent
    slots -- but the normal-vision floor is held across all four, because
    lines cross."""
    t = series_tokens(theme)
    order = [t['a'], t['b'], t['c'], t['d']]
    for c1, c2 in zip(order, order[1:]):
        cvd = min(delta_e(c1, c2, 'protan'), delta_e(c1, c2, 'deutan'))
        assert cvd >= CVD_TARGET, f"{theme}: adjacent {c1}/{c2} dE {cvd:.1f} under CVD"
    for c1, c2 in combinations(order, 2):
        normal = delta_e(c1, c2)
        assert normal >= NORMAL_FLOOR, f"{theme}: {c1}/{c2} dE {normal:.1f} for a full-colour reader"


@pytest.mark.parametrize('theme', ['dark', 'light'])
def test_series_colours_clear_contrast_against_their_own_surface(theme):
    for slot, hex_str in series_tokens(theme).items():
        c = contrast(hex_str, SURFACE[theme])
        assert c >= CONTRAST_MIN, f"{theme} --series-{slot} {hex_str}: {c:.2f}:1 on {SURFACE[theme]}"


def _token_value(theme, name):
    src = TEMPLATE.read_text()
    marker = ':root{' if theme == 'dark' else '[data-theme="light"]{'
    start = src.index(marker)
    block = src[start:src.index('}', start)]
    m = re.search(rf'--{name}\s*:\s*(#[0-9A-Fa-f]{{6}})', block)
    assert m, f"--{name} missing from the {theme} block"
    return m.group(1).upper()


@pytest.mark.parametrize('theme', ['dark', 'light'])
def test_the_my_picks_series_cannot_be_mistaken_for_the_good_status(theme):
    """One specific pair, held to the series floor on purpose.

    The general rule is weaker than this, and worth stating so nobody
    "fixes" the palette to satisfy a bar that was never the standard: a
    series colour and a status colour in the same hue family are allowed to
    sit close, because status in this dashboard is always a labelled tag
    (ACCEPT / REJECT / DEFERRED) and never a bare swatch, so the label and
    placement carry the distinction rather than hue. Model B's amber sits
    dE 11-13 from --warn under that rule and that is fine; --warn is never
    painted on a chart mark, and every experiment verdict is spelled out in
    words beside its colour.

    My Picks is the exception, because there the confusion would be about
    the DATA rather than about a tag: a green line labelled "My Picks",
    tracking a hit rate, on a page where green already means "this went
    well", invites the reader to see the colour as a verdict on the line.
    The fourth series was moved off green to violet for exactly that reason,
    and this test is what stops it drifting back."""
    good = _token_value(theme, 'good')
    d = delta_e(series_tokens(theme)['d'], good)
    assert d >= NORMAL_FLOOR, (
        f"{theme}: the My Picks series is only dE {d:.1f} from --good {good} -- "
        f"it will read as a status rather than as a line")


def test_status_colours_are_never_painted_on_a_chart_mark():
    """The other half of the same rule. Status may sit near a series in hue,
    but it must not BE one: no chart mark is ever filled or stroked with
    --good or --warn, so a chart can't accidentally deliver a verdict."""
    src = TEMPLATE.read_text()
    chart_src = src[src.index('const SERIES = {'):src.index('function renderAccuracy()')]
    for banned in ('--good', '--warn'):
        for m in re.finditer(re.escape(banned), chart_src):
            line = chart_src[max(0, m.start() - 90):m.start() + 40]
            assert 'fill=' not in line and 'stroke=' not in line, (
                f"a chart mark is painted with {banned}: ...{line.strip()}...")


def test_charts_do_not_paint_series_with_ui_accents():
    """--amber and --blue are UI accents (active buttons, tags, links) and
    --chalk-dim is muted ink. Painting a data series with any of them is how
    the light theme ended up with a market line and a Model B line at dE 13.8.
    The SERIES map is the single place series colour is decided, so it is the
    thing to check."""
    src = TEMPLATE.read_text()
    block = src[src.index('const SERIES = {'):src.index('/* Marker path for a series shape')]
    for banned in ('--amber', '--blue', '--chalk-dim', '--good', '--warn'):
        assert banned not in block, f"SERIES assigns {banned} to a data series"
    assert block.count('var(--series-') == 4


# ============================================================
# Wiring: does the data actually reach the page?
# ============================================================
def test_generated_page_has_no_unfilled_placeholders():
    """A missed .replace() ships a literal __SOMETHING_JSON__ into the page and
    breaks the script that follows it."""
    html = (REPO_ROOT / 'index.html').read_text()
    leftovers = re.findall(r'__[A-Z_]+__', html)
    assert not leftovers, f"unfilled template placeholders in index.html: {set(leftovers)}"


def test_generated_page_carries_the_real_calibration_data():
    """Every bin of every model in data/calibration.json has to survive into
    the page -- the reliability diagram is only as honest as the file behind
    it, and a truncated or stale injection would still draw a plausible chart."""
    if not CALIBRATION.exists():
        pytest.skip("data/calibration.json absent -- run src/calibration.py")
    html = (REPO_ROOT / 'index.html').read_text()
    m = re.search(r'const calibration = (\{.*?\n\});\n', html, re.S)
    assert m, "const calibration = ... not found in the generated page"
    embedded = json.loads(m.group(1))
    on_disk = json.loads(CALIBRATION.read_text())
    assert embedded == on_disk, "the page's calibration data differs from data/calibration.json"
    for name, model in embedded['models'].items():
        assert model['bins'], f"{name} has no bins"
        assert sum(b['n'] for b in model['bins']) == model['metrics']['n'], (
            f"{name}: bin counts do not add up to the {model['metrics']['n']} games backtested")


def test_underpowered_bins_are_flagged_not_hidden():
    """The chart draws flagged bins hollow rather than dropping them. If the
    flag stopped being written, they would render as ordinary measurements."""
    if not CALIBRATION.exists():
        pytest.skip("data/calibration.json absent")
    data = json.loads(CALIBRATION.read_text())
    floor = data['min_bin_n']
    for name, model in data['models'].items():
        for b in model['bins']:
            assert b['underpowered'] == (b['n'] < floor), (
                f"{name} bin {b['label']}: n={b['n']} vs floor {floor}, flag={b['underpowered']}")


def test_dashboard_still_builds_without_calibration_json(tmp_path):
    """A fresh clone has never run src/calibration.py, which needs six seasons
    of play-by-play and several minutes. The dashboard must still build, and
    the diagram must omit itself rather than render an empty axis."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "gen_dash_probe", REPO_ROOT / 'src' / 'generate_dashboard.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    missing = tmp_path / 'nothing-here'
    missing.mkdir()
    original = mod.DATA_DIR
    try:
        mod.DATA_DIR = missing
        assert mod.load_calibration() is None
    finally:
        mod.DATA_DIR = original

    # And the page-side guard: the builder returns '' rather than markup.
    src = TEMPLATE.read_text()
    assert "if(!calibration || !calibration.models) return '';" in src, (
        "buildReliabilityDiagram lost its guard against a missing calibration file")


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
