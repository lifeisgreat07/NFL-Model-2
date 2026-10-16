"""The trend fills its box and Deep-Dive prints its scale (Stage 79 item 49, the 2026-10-13 UI/UX audit's N9 and N10).

Measured 2026-10-14 on the NFL page: Season Accuracy's trend was drawn 680
px wide in a 1072 px box at 1440 (716 at 800), and Team Deep-Dive's bars
printed no scale at all. The desktop trend is now drawn at its box's own
width and redrawn when that changes (the first time when the page is shown),
so it fills the box and one unit stays one pixel; a phone keeps its 300-unit
drawing. Deep-Dive says what its bars are scaled to, this team's own largest
net (not the league's), and prints the ends above the bar column, aligned
with it at every width. tests/browser/check_chart_text.py measures the
trend's fill at 1440 px.

Run with: pytest tests/test_trend_width_dive_scale.py -v
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'src' / 'dashboard' / 'app.js').read_text(encoding='utf-8')
CSS = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')


def fn(name):
    m = re.search(r'function %s\(.*?\n\}\n' % name, APP, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def test_the_desktop_trend_takes_its_boxs_width():
    body = fn('buildCumulativeTrendChart')
    assert 'const W = phone ? 300 : Math.max(TREND_MIN_W, Math.round(width || 680)),' in body
    assert '<div class="trend-plot" id="trend-plot" data-w="${W}"><svg class="chart" ' in body


def test_it_is_redrawn_when_the_box_changes_width():
    size = fn('sizeTrendChart')
    assert "if(!plot || chartIsPhone()) return;" in size, 'a phone keeps its own drawing'
    assert 'const w = Math.round(plot.clientWidth);' in size
    assert 'if(!w || w === Number(plot.dataset.w)) return;' in size, 'no redraw without a change, so no loop'
    assert 'tmp.innerHTML = buildCumulativeTrendChart(w);' in size
    assert "new ResizeObserver(sizeTrendChart).observe(plotBox)" in APP
    assert "const plotBox = document.getElementById('accuracy-content');" in APP


def test_deep_dive_prints_its_scale_above_the_bars():
    scale = fn('diveScaleHtml')
    assert "Each bar is scaled to this team's largest net in its own history, about ${scale} either way" in scale
    assert '<div class="net-axis dive-axis"><span class="ax-min">−${scale}</span><span class="ax-zero">0</span><span class="ax-max">+${scale}</span></div>' in scale
    assert '${splitNote}${diveScaleHtml(maxAbs)}${rowsHtml}' in fn('renderTeamDive')


def test_the_scale_sits_over_the_bar_column_at_every_width():
    assert '.net-axis.dive-axis{width:140px; flex-shrink:0;}' in CSS, "the axis is the bar's 140 px, not the Net column's 90"
    phone = CSS[CSS.index('    .dive-row .srs-bar-track{flex:1 1 0; min-width:48px;}'):]
    assert '    .dive-row .dive-axis{flex:1 1 0; min-width:48px;}' in phone[:400], 'on a phone the scale flexes with the bar'
