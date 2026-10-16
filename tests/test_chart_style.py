"""One chart style for every sport's charts (Stage 79 item 45, the 2026-10-13 UI/UX audit's N9 and V3).

Measured 2026-10-14 in headless Chromium: the NFL's accuracy trend printed
13 labels at 9 px at 1440 px and drew no 50% line, its calibration chart 4
labels at 9 px at 390 and 1440, and its reliability diagram "perfect
calibration" at 10.5 px; each chart chose its own grey, dash and marker size
(9 and 10 units). Every SVG chart is now an svg.chart, styled once in
styles.css: text 11 units and up, a hairline grid, the 50% or
perfect-calibration reference dashed in --text-2, whiskers on each 95%
interval, and series markers 12 across, as the scoreboard's marks now are.
The NFL's trend labels as many weeks as fit at 11 units, counted back from
the latest. tests/browser/check_chart_text.py measures the rendered text on
every sport's chart pages.

Run with: pytest tests/test_chart_style.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'src' / 'dashboard' / 'app.js').read_text(encoding='utf-8')
ACC = (ROOT / 'src' / 'core' / 'accuracy.js').read_text(encoding='utf-8')
CSS = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
NODE = shutil.which('node')


def fn(src, name):
    m = re.search(r'function %s\(.*?\n\}\n' % name, src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


CHARTS = [('app.js', fn(APP, 'buildCumulativeTrendChart')), ('app.js', fn(APP, 'buildCalibrationChart')),
          ('app.js', fn(APP, 'buildReliabilityDiagram')), ('accuracy.js', fn(ACC, 'accTrendHtml')),
          ('accuracy.js', fn(ACC, 'accDiagramHtml'))]


@pytest.mark.parametrize('where,src', CHARTS, ids=[f'{w}:{s[9:s.index("(")]}' for w, s in CHARTS])
def test_every_chart_is_drawn_in_the_chart_style(where, src):
    svgs = re.findall(r'<svg [^>]*viewBox="0 0 \$\{', src)
    assert svgs and all(s.startswith('<svg class="chart" ') for s in svgs), svgs
    assert not re.search(r'<text[^>]*font-size=', src), 'a chart sets its own text size'
    assert not re.search(r'<line [^>]*stroke="var\(--border', src), 'a chart draws its own grid or reference'


def test_the_style_sets_the_floor_the_grid_the_reference_and_the_whisker():
    assert '/* ---------- One chart style (Stage 79 item 45' in CSS
    block = '\n'.join(re.findall(r'^  \.chart [^\n]*', CSS, re.M))
    assert '.chart text{font-size:var(--fs-11); fill:var(--text-2);}' in block
    assert '.chart .chart-title{font-size:var(--fs-12);}' in block
    assert re.findall(r'font-size:([^;}]+)', block) == ['var(--fs-11)', 'var(--fs-12)'], 'no chart text under 11'
    assert '.chart .chart-grid{stroke:var(--border); stroke-width:1;}' in block
    assert '.chart .chart-ref{stroke:var(--text-2); stroke-width:1; stroke-dasharray:4 3; fill:none;}' in block
    assert '.chart .chart-whisker{stroke-width:2; stroke-opacity:.5; stroke-linecap:round;}' in block


def test_each_chart_draws_its_reference():
    assert """<line class="${gv === 50 ? 'chart-ref' : 'chart-grid'}" """ in fn(APP, 'buildCumulativeTrendChart')
    assert '<line class="chart-ref" x1="${pad}" y1="${S-pad}" x2="${S-pad}" y2="${pad}"/>' in fn(APP, 'buildCalibrationChart')
    assert '<line class="chart-ref" x1="${x(0).toFixed(1)}" ' in fn(APP, 'buildReliabilityDiagram')
    assert """<line class="${v === 50 ? 'chart-ref' : 'chart-grid'}" """ in fn(ACC, 'accTrendHtml')
    assert '<line class="chart-ref" x1="${x(50).toFixed(1)}" ' in fn(ACC, 'accDiagramHtml')
    # The scoreboard's coin flip and Deep-Dive's zero are the same dashed reference.
    assert '.score-coin{position:absolute; left:50%; top:-6px; bottom:-6px; width:0; border-left:1px dashed var(--text-2);}' in CSS
    assert re.search(r'\.srs-bar-track\.diverging::before\{[^}]*border-left:1px dashed var\(--text-2\);', CSS)


def test_intervals_are_whiskers_and_series_shapes_are_12_across():
    assert 'const bar = chartWhisker(cx, barTop, barBot, s.color);' in fn(APP, 'buildReliabilityDiagram')
    assert 'accWhisker(x(p.said), y(p.ci[1] * 100), y(p.ci[0] * 100))' in fn(ACC, 'accDiagramHtml')
    assert 'const CHART_MARK_R = 6;' in APP
    assert 'markerPath(s.shape, x(last.i), y(last.v), CHART_MARK_R)' in fn(APP, 'buildCumulativeTrendChart')
    assert 'markerPath(s.shape, cx, cy, CHART_MARK_R)' in fn(APP, 'buildReliabilityDiagram')
    assert 'const r = 6;' in fn(ACC, 'accMarker') and 'r="6"' in fn(ACC, 'accDiagramHtml')
    assert '.score-mark{width:12px; height:12px; flex-shrink:0; background:var(--series);}' in CSS


def test_week_labels_thin_to_what_fits_counted_back_from_the_latest():
    if not NODE:
        pytest.skip('node not available')
    weeks = json.dumps([f'Wk {i}' for i in range(1, 19)])
    code = fn(APP, 'chartTickStep') + (
        f'const w = {weeks};'
        'console.log(JSON.stringify([chartTickStep(w, (300-34-20)/17), chartTickStep(w, (680-36-74)/17),'
        ' chartTickStep(w.slice(0, 5), (680-36-74)/4)]));')
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == [3, 2, 1], 'a phone labels every third of 18 weeks, a desktop every second, 5 weeks all'
    assert "const weekTicks = accuracy.weeks.map((w, i) => (n - 1 - i) % every ? '' :" in fn(APP, 'buildCumulativeTrendChart')
