"""One meaning per word: "points" are football points, a percentage gap is "pp".

Stage 14 (CLAUDE.md, "One meaning per number"). The Model Lab and
Methodology tables wrote accuracy differences as "+0.83pt" and "-2.39pt",
while the same page used "points" for a point spread and pick'em values: two
meanings for one abbreviation. Accuracy gaps now read "pp" (percentage
points), defined in the glossary; a spread is written by fmtPoints() with its
unit ("favourites by 6.5 points", where the card said "by 6.0").

These tests read every piece of text a reader can see -- the markup outside
comments, <style> and <script>, and the string and template literals inside
the script -- and fail on a bare "pt" or "pts".

Run with: pytest tests/test_units.py -v
"""
import json
import re
import shutil
import subprocess

import pytest
from page_source import page_source  # Model Lab's rows are rendered in at build time

from src.core.template_parts import JOINED_TEMPLATE

TEMPLATE = JOINED_TEMPLATE
NODE = shutil.which('node')
ABBR = re.compile(r'(?<![A-Za-z_$])pts?(?![A-Za-z_])')
CASES = [6, 6.5, 1, 0.96, 10.5, -3, 3.04, 0]


@pytest.fixture(scope='module')
def src():
    return page_source()


def markup_text(src):
    return re.sub(r'<!--.*?-->|<style[^>]*>.*?</style>|<script[^>]*>.*?</script>', ' ', src, flags=re.S)


def script_literals(src):
    """The text of every string and template literal in the page's scripts,
    with ${...} expressions and comments taken out."""
    out = []
    for body in re.findall(r'<script[^>]*>(.*?)</script>', src, re.S):
        body = re.sub(r'/\*.*?\*/', ' ', body, flags=re.S)
        body = re.sub(r'(?m)^\s*//.*$', ' ', body)
        for lit in re.findall(r'`(?:[^`\\]|\\.)*`|\'(?:[^\'\\\n]|\\.)*\'|"(?:[^"\\\n]|\\.)*"', body):
            out.append(re.sub(r'\$\{[^}]*\}', ' ', lit))
    return out


def test_no_bare_pt_or_pts_in_the_markup(src):
    text = markup_text(src)
    hits = [text[max(0, m.start() - 40):m.end() + 10].replace('\n', ' ') for m in ABBR.finditer(text)]
    assert not hits, f'a bare pt/pts a reader can see: {hits[:5]}'


def test_no_bare_pt_or_pts_in_script_text(src):
    lits = script_literals(src)
    assert len(lits) > 100, 'the literal extractor found almost nothing -- it has drifted'
    hits = [l[:80] for l in lits if ABBR.search(l)]
    assert not hits, f'script text that renders a bare pt/pts: {hits[:5]}'


def test_percentage_points_are_written_pp_and_defined(src):
    text = markup_text(src)
    assert len(re.findall(r'\d&nbsp;pp\b', text)) >= 10, 'accuracy gaps are no longer written "N pp"'
    assert re.search(r'<tr><td>Percentage points \(pp\)</td><td>', src), 'the glossary does not define pp'


@pytest.fixture(scope='module')
def points(src):
    if not NODE:
        pytest.skip('node not available')
    fn = re.search(r'function fmtPoints\(.*?\n\}\n', src.replace('\r\n', '\n'), re.S)
    assert fn, 'fmtPoints is not findable -- re-anchor this guard'
    js = fn.group(0) + f'\nprocess.stdout.write(JSON.stringify({json.dumps(CASES)}.map(fmtPoints)));'
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return dict(zip(map(str, CASES), json.loads(r.stdout)))


def test_a_spread_is_written_with_its_unit(points):
    assert points['6'] == '6 points'
    assert points['6.5'] == '6.5 points'
    assert points['10.5'] == '10.5 points'
    assert points['-3'] == '3 points', 'a spread is a size here; its sign is said by who is favoured'


def test_one_point_is_singular_and_rounding_is_to_a_tenth(points):
    assert points['1'] == '1 point'
    assert points['0.96'] == '1 point'
    assert points['3.04'] == '3 points'
    assert points['0'] == '0 points'

