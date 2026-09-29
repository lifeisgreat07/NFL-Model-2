"""The reliability diagram is one Tab stop, walked with the arrow keys.

Stage 26 item 10 (CLAUDE.md). Every point used to carry tabindex="0", so a
keyboard reader pressed Tab thirty times to get past the chart to its table.
Now the points form one group with a roving tabindex: one visible point holds
the Tab stop, the arrow keys move through the visible points, Home and End go
to the ends, and switching a series off never leaves the Tab stop on a point
nobody can see.

initReliabilityDiagram() is executed here under node against a small stand-in
DOM (the points, their series, the toggles and the tooltip), so the tests
drive the real handlers rather than read their source.

Run with: pytest tests/test_reliability_focus_group.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / 'src' / 'dashboard_template.html'
NODE = shutil.which('node')

# A stand-in for the parts of the DOM initReliabilityDiagram touches: three
# series of three points, three toggles, the tooltip and its plot.
HARNESS = r"""
function node(extra){
  const attrs = {}, on = {};
  const n = Object.assign({
    style: {}, dataset: {}, classList: {add(){}, remove(){}},
    setAttribute(k, v){ attrs[k] = String(v); }, getAttribute(k){ return k in attrs ? attrs[k] : null; },
    addEventListener(t, f){ (on[t] = on[t] || []).push(f); },
    fire(t, e){ (on[t] || []).forEach(f => f(e || {})); },
  }, extra || {});
  return n;
}
const doc = {active: null};
const SERIES = ['model_a', 'model_b', 'market'].map(k => node({dataset: {model: k}}));
const POINTS = [];
SERIES.forEach((g, si) => { for(let b = 0; b < 3; b++){
  const p = node({dataset: {tip: 't', cx: '10', cy: '10'}, name: `${si}.${b}`});
  p.setAttribute('tabindex', '-1');
  p.closest = () => g;
  p.focus = () => { doc.active = p; p.fire('focus'); };
  POINTS.push(p);
}});
const svg = node({getBoundingClientRect: () => ({width: 470, height: 470}),
                  viewBox: {baseVal: {width: 470}}, querySelectorAll: () => []});
const plot = node({querySelector: () => svg, querySelectorAll: s => s === '.rel-point' ? POINTS : []});
const tip = node({parentElement: plot, offsetWidth: 10, offsetHeight: 10});
const TOGGLES = SERIES.map(g => node({dataset: {model: g.dataset.model}}));
var relVisible = {model_a: true, model_b: true, market: true};
function relHaloRadius(){ return 11; }
var window = {addEventListener(){}};
var document = {
  getElementById: id => id === 'rel-tip' ? tip : null,
  querySelectorAll: s => s === '.rel-toggle' ? TOGGLES : [],
  querySelector: s => SERIES.find(g => s.includes(`"${g.dataset.model}"`)) || null,
};
"""

DRIVE = r"""
const out = {};
const stops = () => POINTS.filter(p => p.getAttribute('tabindex') === '0').map(p => p.name);
const key = k => { let prevented = false; doc.active.fire('keydown', {key: k, preventDefault(){ prevented = true; }}); return prevented; };
out.onMount = stops();
POINTS[0].focus();
key('ArrowRight'); out.afterRight = [doc.active.name, stops()];
key('ArrowDown');  out.afterDown = [doc.active.name, stops()];
key('ArrowLeft');  out.afterLeft = doc.active.name;
key('End');        out.afterEnd = doc.active.name;
key('ArrowRight'); out.pastTheEnd = doc.active.name;
key('Home');       out.afterHome = doc.active.name;
out.tabIsLeftAlone = key('Tab') === false && doc.active.name === '0.0';
// Switch Model A off while it holds the Tab stop.
TOGGLES[0].fire('click');
out.afterHidingA = stops();
POINTS[3].focus();
key('Home'); out.homeSkipsHidden = doc.active.name;
key('ArrowLeft'); out.leftSkipsHidden = doc.active.name;
// Switch Model B off too while one of its points holds the stop.
POINTS[4].focus();
TOGGLES[1].fire('click');
out.afterHidingB = stops();
process.stdout.write(JSON.stringify(out));
"""


@pytest.fixture(scope='module')
def source():
    return TEMPLATE.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def run(source):
    if not NODE:
        pytest.skip('node not available')
    fn = re.search(r'function initReliabilityDiagram\(\)\{.*?\n\}\n', source, re.S)
    assert fn, 'initReliabilityDiagram is gone -- re-anchor this guard'
    js = HARNESS + fn.group(0) + '\ninitReliabilityDiagram();\n' + DRIVE
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_the_markup_gives_no_point_its_own_tab_stop(source):
    tags = re.findall(r'<g class="rel-point"[^>]*', source)
    assert tags, 'the reliability points are not findable -- re-anchor this guard'
    assert all('tabindex="-1"' in t for t in tags), 'a point is in the Tab order on its own again'


def test_exactly_one_point_holds_the_tab_stop_on_mount(run):
    assert run['onMount'] == ['0.0']


def test_the_arrow_keys_move_the_focus_and_the_tab_stop_with_it(run):
    assert run['afterRight'] == ['0.1', ['0.1']]
    assert run['afterDown'] == ['0.2', ['0.2']]
    assert run['afterLeft'] == '0.1'


def test_home_and_end_go_to_the_ends_and_the_ends_do_not_wrap(run):
    assert run['afterEnd'] == '2.2'
    assert run['pastTheEnd'] == '2.2'
    assert run['afterHome'] == '0.0'


def test_tab_is_not_captured(run):
    """The group is one stop, not a trap: Tab must still leave it."""
    assert run['tabIsLeftAlone']


def test_hiding_a_series_moves_the_tab_stop_to_a_visible_point(run):
    assert run['afterHidingA'] == ['1.0']
    assert run['afterHidingB'] == ['2.0']


def test_the_arrow_keys_skip_a_hidden_series(run):
    assert run['homeSkipsHidden'] == '1.0'
    assert run['leftSkipsHidden'] == '1.0'
