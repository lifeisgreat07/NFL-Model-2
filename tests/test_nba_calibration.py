"""The NBA's reliability page shows its live picks' calibration (Stage 68 item 21).

The NHL's Accuracy page has "How sure, and how often right"; the NBA had
no calibration view at all (the audit's U39 was half right: the NHL had
one). The same table now leads the NBA's reliability page, and says plainly
when no pick has been graded yet. Run in node over the page's own script.

Run with: pytest tests/test_nba_calibration.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js').read_text(encoding='utf-8')
NODE = shutil.which('node')


def functions():
    start = JS.index('const CAL_BINS')
    return JS[start:JS.index('function renderReliability(){')]


def run(bd):
    src = f'const BD={json.dumps(bd)};function pct(x,d){{return (x*100).toFixed(d??0)+"%";}}' + functions() + \
        'process.stdout.write(calibrationHtml(gradedPicks()));'
    return subprocess.run([NODE, '-e', src], capture_output=True, text=True, check=True).stdout


@pytest.mark.skipif(NODE is None, reason='node is not installed')
def test_before_any_grade_it_says_so():
    out = run({'games': [{'id': '1', 'home': 'BOS', 'away': 'NY'}], 'picks': {}})
    assert 'No NBA pick has been graded yet' in out and '<table' not in out


@pytest.mark.skipif(NODE is None, reason='node is not installed')
def test_graded_picks_fall_in_their_bins():
    games = [{'id': str(i), 'home': 'BOS', 'away': 'NY'} for i in range(4)]
    picks = {'0': {'a': 0.62, 'b': None, 'by': 'model_a', 'pick': 'BOS', 'result': 'correct'},
             '1': {'a': 0.40, 'b': 0.38, 'by': 'model_b', 'pick': 'NY', 'result': 'wrong'},
             '2': {'a': 0.80, 'b': None, 'by': 'model_a', 'pick': 'BOS', 'result': 'correct'},
             '3': {'a': 0.70, 'b': None, 'by': 'model_a', 'pick': 'BOS', 'result': 'pending'}}
    out = run({'games': games, 'picks': picks})
    rows = dict(re.findall(r'<th scope="row">([^<]+)</th><td class="num">(\d+)</td>', out))
    assert rows == {'50% to 55%': '0', '55% to 60%': '0', '60% to 65%': '2', '65% to 70%': '0', '70% and up': '1'}
    assert 'With 3 graded picks' in out


def test_it_leads_the_reliability_page():
    body = JS[JS.index('function renderReliability(){'):]
    assert body.index('${calibrationHtml(gradedPicks())}') < body.index('Before anything was fitted')
