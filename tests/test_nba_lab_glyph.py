"""The NBA's and NHL's Model Labs read as the NFL's does (Stage 79 item 51, the 2026-10-13 UI/UX audit's B4;
audit 9, finding D10).

The NBA printed its decisions as bold text and its intervals as figures
only; the NFL's Model Lab shows a neutral pill and draws each interval
against zero (Stage 18). The NBA's page is built in the browser, so the
glyph is a port of generate_dashboard.interval_glyph, which lived in nba.js
and since audit 9 lives in src/core/day_board.js, which both day boards load: the
NHL had kept printing bare intervals and bold words under a column headed Label.
This runs the port under node and holds it to the Python original, number by number.

Run with: pytest tests/test_nba_lab_glyph.py -v
"""
import html
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.sports.nfl.generate_dashboard import interval_glyph
from tests.optional import require_tool

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'src' / 'core' / 'day_board.js').read_text(encoding='utf-8')
BOARDS = {s: (ROOT / 'src' / 'sports' / s / 'pages' / f'{s}.js').read_text(encoding='utf-8') for s in ('nhl', 'nba')}
NFL_BODY = (ROOT / 'src' / 'dashboard' / 'body.html').read_text(encoding='utf-8')
NODE = shutil.which('node')
CASES = [(-0.0905, -0.1086, -0.0719), (0.0008, 0.0002, 0.0015), (-0.0109, -0.0319, 0.0096), (0.0, -0.00001, 0.00004),
         (0.001, 0.0, 0.002)]   # an interval ending exactly at zero includes it


def js_glyphs():
    require_tool('node')
    code = ''.join(re.search(rf'function {n}\(.*?\n\}}\n', JS, re.S).group(0) for n in ('plainSigned', 'intervalGlyph'))
    code += 'console.log(JSON.stringify(%s.map(([d, lo, hi]) => intervalGlyph(d, lo, hi))));' % json.dumps(CASES)
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def shape(svg):
    """The glyph's label and every number in its markup, so 5 and 5.0 compare equal."""
    svg = html.unescape(svg).replace('−', '-')
    label = re.search(r'aria-label="([^"]+)"', svg).group(1)
    numbers = [float(v) for v in re.findall(r'="(-?\d+(?:\.\d+)?)"', svg)]
    classes = re.findall(r'class="([^"]+)"', svg)
    return label, numbers, classes


def test_the_port_draws_what_the_nfl_draws():
    for (d, lo, hi), svg in zip(CASES, js_glyphs()):
        js_label, js_numbers, js_classes = shape(svg)
        py_label, py_numbers, py_classes = shape(interval_glyph({'diff': d, 'ci': [lo, hi]}))
        assert (js_label, js_classes) == (py_label, py_classes), (d, lo, hi)
        # Python rounds a half to even (37.25 -> 37.2) and JavaScript up (37.3),
        # so a coordinate may differ by one tenth of a unit in a 96-unit glyph.
        assert len(js_numbers) == len(py_numbers)
        assert all(abs(a - b) <= 0.11 for a, b in zip(js_numbers, py_numbers)), (d, lo, hi, js_numbers, py_numbers)


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_each_question_shows_the_glyph_and_its_decision_as_a_pill(sport):
    body = BOARDS[sport][BOARDS[sport].index('function renderModelLab(){'):]
    row = body[:body.index('.join(\'\');')]
    assert '<span class="lab-lead">${intervalGlyph(q.diff, q.low, q.high)}</span>' in row
    assert '<span class="lab-tags"><span class="conf-tag tag-neutral">${escapeHtml(q.label)}</span></span>' in row
    assert '<b>${q.label}</b>' not in row


def test_the_glyph_is_drawn_from_one_place():
    for sport, src in BOARDS.items():
        assert 'function intervalGlyph(' not in src and 'function plainSigned(' not in src, sport


def test_every_model_labs_decision_column_is_headed_decision():
    head = '<th scope="col" class="num">Interval</th><th scope="col">Decision</th>'
    for sport, src in BOARDS.items():
        assert head in src and '<th scope="col">Label</th>' not in src, sport
    assert '<th scope="col">Result</th><th scope="col">Decision</th>' in NFL_BODY
