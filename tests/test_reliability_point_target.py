"""Every reliability-diagram point has a hit target of at least 24 CSS px.

Stage 12 (CLAUDE.md). Model Lab's reliability points are keyboard- and
pointer-reachable (<g class="rel-point">, one Tab stop for the chart since
Stage 26 -- see tests/test_reliability_focus_group.py), and each one's hit
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

import pytest

from src.pipeline.template_parts import JOINED_TEMPLATE  # noqa: E402

TEMPLATE = JOINED_TEMPLATE
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


# initReliabilityDiagram run in node against stubs: an svg whose rendered
# width the test sets, two halo nodes, and a ResizeObserver that records its
# callback so the test can fire it. Replaced a text check of the function's
# source (Stage 31 item 12): this runs the real sizing code.
HALO_HARNESS = r"""
function node(extra){ const attrs={}, on={}; return Object.assign({style:{},dataset:{},classList:{add(){},remove(){}},
  setAttribute(k,v){attrs[k]=String(v);}, getAttribute(k){return k in attrs?attrs[k]:null;},
  addEventListener(t,f){(on[t]=on[t]||[]).push(f);}, fire(t,e){(on[t]||[]).forEach(f=>f(e||{}));}}, extra||{}); }
const HALOS=[node(),node()]; let W=0; let observed=null;
const svg=node({getBoundingClientRect:()=>({width:W,height:W}), viewBox:{baseVal:{width:470}},
  querySelectorAll:s=>s==='.rel-halo'?HALOS:[]});
const plot=node({querySelector:()=>svg, querySelectorAll:()=>[]});
const tip=node({parentElement:plot});
var relVisible={model_a:true};
var window={ResizeObserver:function(cb){ observed=cb; this.observe=()=>{}; }, addEventListener(){}};
var ResizeObserver=window.ResizeObserver;
var document={getElementById:id=>id==='rel-tip'?tip:null, querySelectorAll:()=>[], querySelector:()=>null};
"""


@pytest.fixture(scope='module')
def halos(source):
    """The halos' r on mount (the chart 0 wide, as on a hidden page), after a
    resize to 350px, and after one to the full 470px."""
    if not NODE:
        pytest.skip('node not available')
    base = re.search(r'const REL_HALO_BASE_R = [^;]+;', source)
    radius = re.search(r'function relHaloRadius\(.*?\n\}\n', source, re.S)
    init = re.search(r'function initReliabilityDiagram\(\)\{.*?\n\}\n', source, re.S)
    assert base and radius and init, 'the halo sizing code is not findable -- re-anchor this guard'
    js = HALO_HARNESS + base.group(0) + '\n' + radius.group(0) + init.group(0) + r"""
W=0; const out={};
initReliabilityDiagram(); out.mount=HALOS[0].getAttribute('r');
W=350; if(observed) observed(); out.narrow=HALOS[0].getAttribute('r');
W=470; if(observed) observed(); out.full=HALOS[1].getAttribute('r');
process.stdout.write(JSON.stringify(out));
"""
    r = subprocess.run([NODE, '-e', js], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_the_halos_are_sized_on_mount_and_on_every_resize(halos):
    """Sized once on mount -- 0 wide on a hidden page, so the base radius --
    and again every time the chart changes width, including when Model Lab
    opens. Rounded UP to the hundredth: at 350px the exact radius is
    16.114..., which to the nearest would be 16.11 and 23.99px across."""
    assert halos['mount'] == '11.00', halos
    assert halos['narrow'] == '16.12', halos
    assert halos['full'] == '12.00', halos
