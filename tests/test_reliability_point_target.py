"""Every reliability-diagram point has a hit target of at least 24 CSS px.

Stage 12 (CLAUDE.md). Model Lab's reliability points are keyboard- and
pointer-reachable (<g class="rel-point" tabindex="0">), and each one's hit
target is a transparent halo. The halo was r=11 in the chart's 470-unit
viewBox and the chart scales with its container, so it was 22 CSS px across
only at exactly 470px rendered: the browser checker built for Stage 12
measured 21-22px at 360, 390, 1024 and 1280 wide, under WCAG 2.5.8's 24.

relHaloRadius() is executed here under node over rendered widths either side
of the crossover; the wiring (sized on mount and on every resize, rounded up)
is held by source guards, because it needs a browser to run.

Run with: pytest tests/test_reliability_point_target.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / 'src' / 'dashboard_template.html'
NODE = shutil.which('node')
VIEWBOX = 470
WIDTHS = [0, 200, 330, 400, 452, 470, 480, 520, 680, 900]


@pytest.fixture(scope='module')
def source():
    return TEMPLATE.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def radii(source):
    if not NODE:
        pytest.skip('node not available')
    base = re.search(r'const REL_HALO_BASE_R = [^;]+;', source)
    fn = re.search(r'function relHaloRadius\(.*?\n\}\n', source, re.S)
    assert base and fn, 'relHaloRadius is not findable -- re-anchor this guard'
    js = (base.group(0) + '\n' + fn.group(0) +
          f'\nconst W={json.dumps(WIDTHS)};'
          f'process.stdout.write(JSON.stringify({{base: REL_HALO_BASE_R, '
          f'r: W.map(w => relHaloRadius(w, {VIEWBOX}, 24))}}));')
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_the_halo_is_at_least_24_css_px_at_every_rendered_width(radii):
    for w, r in zip(WIDTHS, radii['r']):
        if w == 0:
            continue
        across_px = 2 * r * (w / VIEWBOX)
        assert across_px >= 24 - 1e-9, f'at {w}px rendered the halo is {across_px:.2f}px across'


def test_the_halo_never_shrinks_below_its_old_size(radii):
    """On a wide chart the old r=11 already cleared 24px; keep it there."""
    assert radii['base'] == 11
    assert all(r >= 11 for r in radii['r'])
    assert radii['r'][WIDTHS.index(680)] == 11


def test_a_chart_on_a_hidden_page_keeps_the_base_radius(radii):
    """Model Lab is display:none until opened, so the chart measures 0 wide."""
    assert radii['r'][0] == 11


def test_the_halos_are_sized_on_mount_and_on_every_resize(source):
    body = re.search(r'function initReliabilityDiagram\(\)\{.*?\n\}\n', source, re.S)
    assert body, 'initReliabilityDiagram is gone -- re-anchor this guard'
    code = re.sub(r'(?m)^\s*//.*$', '', body.group(0))
    assert re.search(r'relHaloRadius\(\s*svgEl\.getBoundingClientRect\(\)\.width', code), (
        'the halos are no longer sized from the rendered width')
    assert re.search(r'\n\s*sizeRelHalos\(\);', code), 'the halos are not sized on mount'
    assert 'new ResizeObserver(sizeRelHalos)' in code, (
        'the halos are not re-sized when the chart changes width -- including '
        'when Model Lab opens and the chart goes from 0 wide to its real width')
    assert 'Math.ceil(' in code, 'the radius is no longer rounded up'
