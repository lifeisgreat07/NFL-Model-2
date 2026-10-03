"""The accuracy trend chart labels its weeks and keeps its end-labels apart
(Stage 19).

The UX review found the chart had no week labels on its x-axis and that its
end-labels stacked. Labels were nudged one at a time, in draw order and always
downwards, by less than their own height: when Model A and Model B finished on
the same value their labels overprinted. They are now placed together once
every line is known -- sorted by where their lines end, spread to a minimum
gap, and moved back inside the plot if that pushed them out.

tests/trend_labels_harness.js runs the shipped spreadLabels(); the rest reads
the chart's source. Requires node; skipped loudly if absent.

Run with: pytest tests/test_accuracy_trend_labels.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.pipeline.template_parts import JOINED_TEMPLATE  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = JOINED_TEMPLATE
HARNESS = Path(__file__).parent / 'trend_labels_harness.js'
NODE = shutil.which('node')
LABEL_FONT = 10     # the end-labels' font-size, in the chart's own units


@pytest.fixture(scope='module')
def spread():
    if NODE is None:
        pytest.skip('node not on PATH -- spreadLabels() cannot be executed')
    proc = subprocess.run([NODE, str(HARNESS)], cwd=REPO_ROOT,
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, f'harness failed:\n{proc.stderr}'
    data = json.loads(proc.stdout)
    assert 'fatal' not in data, data.get('fatal')
    return data


def chart():
    src = TEMPLATE.read_text(encoding='utf-8').replace('\r\n', '\n')
    start = src.index('function buildCumulativeTrendChart(')
    return src[start:src.index('\n}\n', start)]


def test_labels_already_apart_stay_where_their_lines_end(spread):
    assert spread['apart'] == [40, 100, 160]


def test_lines_ending_together_get_labels_a_full_gap_apart(spread):
    assert spread['together_min_gap'] >= 14
    # Nothing moves further than it has to: the first stays on its line.
    assert spread['together'][0] == 100


def test_labels_pushed_past_the_floor_come_back_inside_the_plot(spread):
    assert max(spread['at_bottom']) <= 192
    assert spread['at_bottom_min_gap'] >= 14


def test_labels_keep_their_lines_order(spread):
    assert spread['reversed'] == [150, 100]
    assert spread['empty'] == []


def test_the_gap_clears_the_label_text(spread):
    """At font-size 10 a label is about 12 units tall; 11 was the old gap."""
    assert spread['gap'] >= LABEL_FONT + 3


def test_the_chart_places_its_labels_together_after_every_line():
    js = chart()
    assert 'spreadLabels(ends.map(e => e.y), TREND_LABEL_GAP' in js
    svg = js[js.index('<svg viewBox'):]
    assert svg.index("${lineFor('p','picks')}") < svg.index('${endLabels()}')
    assert 'labelSlots' not in js, 'the one-at-a-time nudge is back'


def test_every_graded_week_is_labelled_on_the_x_axis():
    js = chart()
    m = re.search(r'const weekTicks = accuracy\.weeks\.map\(\(w, i\) =>\s*`<text x="\$\{x\(i\)', js)
    assert m, 'the x-axis has no week labels'
    assert 'Wk ${w.week}' in js
    assert '${weekTicks}' in js[js.index('<svg viewBox'):]
