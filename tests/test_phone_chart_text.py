"""Chart text is readable on a phone (Stage 26 item 4).

The Season Accuracy trend chart was drawn 680 units wide and Model Lab's
reliability diagram 470, both shrunk to fit: on a 375px phone their text
came out about 4px and 6px tall. Below 640px each is now drawn about the
width it renders at (300 units for roughly 300px), with text sized for it,
and the trend chart's names at the line ends are dropped there, since the
legend above it names every line (Mark's choice from rendered side-by-sides,
2026-09-28). Desktop drawing is unchanged. Measured in a browser for the PR;
held here by source and by the arithmetic that makes the rule true.
"""
import re
from pathlib import Path

TEMPLATE = (Path(__file__).resolve().parents[1] / 'src' / 'pipeline' / 'dashboard_template.html').read_text(encoding='utf-8')
PHONE_RENDERED_PX = 300   # the chart's width on a 375px phone, measured 299
MIN_PX = 11


def fn(name):
    m = re.search(r'function ' + name + r'\(\)\{.*?\n\}\n', TEMPLATE, re.S)
    assert m, f'{name} is not findable -- re-anchor this test'
    return m.group(0)


def test_the_phone_width_is_the_pages_phone_width():
    assert "const CHART_PHONE = '(max-width:640px)';" in TEMPLATE
    assert "const ORIENTATION_PHONE = '(max-width:640px)';" in TEMPLATE, (
        'the page has two ideas of how wide a phone is')
    assert 'window.matchMedia(CHART_PHONE).matches' in fn('chartIsPhone')


def test_the_trend_chart_is_drawn_for_the_phone_with_readable_text():
    body = fn('buildCumulativeTrendChart')
    m = re.search(r'const W = phone \? (\d+) : 680, H = phone \? \d+ : 220, padL = phone \? \d+ : 36, padR = phone \? \d+ : 74;', body)
    assert m, 'the trend chart no longer has a phone drawing (or its desktop one moved)'
    w = int(m.group(1))
    fs = re.search(r'const fsTick = phone \? ([\d.]+) : 9, fsName = phone \? ([\d.]+) : 10;', body)
    assert fs, 'the trend chart text sizes are not set by width'
    for size in map(float, fs.groups()):
        assert size * PHONE_RENDERED_PX / w >= MIN_PX, f'{size} units in a {w}-unit chart renders under {MIN_PX}px'
    assert 'font-size="9"' not in body and 'font-size="10"' not in body, 'a fixed text size is left in the trend chart'
    assert 'max-width:${W}px;' in body


def test_the_trend_chart_drops_the_line_names_on_a_phone_only():
    body = fn('buildCumulativeTrendChart')
    assert re.search(r"function endLabels\(\)\{\s*if\(phone\) return '';", body)
    assert "const legend = seriesLegend(['a','b','market','picks']);" in body, (
        'the legend that names the lines on a phone is gone')


def test_the_reliability_diagram_is_drawn_for_the_phone_with_readable_text():
    body = fn('buildReliabilityDiagram')
    m = re.search(r'const W = phone \? (\d+) : 470, padL = phone \? \d+ : 48, padR = phone \? \d+ : 16, padT = 14;', body)
    assert m, 'the reliability diagram no longer has a phone drawing'
    w = int(m.group(1))
    fs = re.search(r'const fs = phone \? \{tick: ([\d.]+), note: ([\d.]+), axis: ([\d.]+)\} : \{tick: 10, note: 9\.5, axis: 10\.5\};', body)
    assert fs, 'the diagram text sizes are not set by width'
    for size in map(float, fs.groups()):
        assert size * PHONE_RENDERED_PX / w >= MIN_PX
    assert not re.search(r'font-size="[\d.]+"', body), 'a fixed text size is left in the reliability diagram'
    assert 'const PLOT = phone ? W - padL - padR : 390;' in body


def test_the_reliability_diagram_is_drawn_as_before_on_a_desktop():
    # Its first version derived the desktop plot from W too, growing it from
    # 390 to 406 units and the diagram about 4% taller; Booth caught it on #201.
    body = fn('buildReliabilityDiagram')
    assert 'const PLOT = phone ? W - padL - padR : 390;' in body
    assert 'const H = padT + PLOT + (phone ? 44 : 40);' in body
    assert ': {tick: 10, note: 9.5, axis: 10.5};' in body
