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

from tests.optional import in_ci

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


@pytest.mark.skipif(NODE is None and not in_ci(), reason='node is not installed')
def test_before_any_grade_it_says_so():
    out = run({'games': [{'id': '1', 'home': 'BOS', 'away': 'NY'}], 'picks': {}})
    assert 'No NBA pick has been graded yet' in out and '<table' not in out


@pytest.mark.skipif(NODE is None and not in_ci(), reason='node is not installed')
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


def test_it_is_on_the_accuracy_page_and_not_the_checks_page():
    """Stage 104 item 1: the live record, the accuracy component and this table
    are the Season Accuracy page's, as on the NHL's pages."""
    acc = JS[JS.index('function renderAccuracy(){'):JS.index('function renderReliability(){')]
    assert acc.index('${accuracyHtml(accGames(graded))}') < acc.index('${calibrationHtml(graded)}')
    rel = JS[JS.index('function renderReliability(){'):]
    assert 'calibrationHtml(' not in rel and 'accuracyHtml(' not in rel
    init = JS[JS.index('installFavStars(renderBoard);'):]
    assert 'renderAccuracy();' in init[:200], 'the page is built at load, as every other page is'


def run_accuracy(bd):
    """renderAccuracy under node, with the shared parts it calls stubbed: what
    matters here is the record line, the rows and what is left out."""
    stubs = ('const out = {}; const document = {getElementById: () => out};'
             'function stateHtml(k, t, x){ return `STATE ${t}: ${x}`; }'
             'function accuracyHtml(){ return "ACC"; } function accGames(g){ return g; }'
             'function escapeHtml(s){ return String(s); } function dayDate(d){ return new Date(d + "T12:00:00Z"); }'
             'const FMT_MONTHDAY = new Intl.DateTimeFormat("en-US", {month: "short", day: "numeric", timeZone: "UTC"});')
    src = f'const BD={json.dumps(bd)};function pct(x,d){{return (x*100).toFixed(d??0)+"%";}}' + stubs + functions() + \
        'renderAccuracy(); process.stdout.write(out.innerHTML);'
    return subprocess.run([NODE, '-e', src], capture_output=True, text=True, check=True).stdout


@pytest.mark.skipif(NODE is None and not in_ci(), reason='node is not installed')
def test_the_accuracy_page_counts_only_graded_picks():
    games = [{'id': str(i), 'home': 'BOS', 'away': 'NY', 'day': '2026-11-0' + str(i + 1)} for i in range(3)]
    picks = {'0': {'a': 0.62, 'b': None, 'by': 'model_a', 'pick': 'BOS', 'result': 'correct'},
             '1': {'a': 0.40, 'b': 0.38, 'by': 'model_b', 'pick': 'NY', 'result': 'wrong'},
             '2': {'a': 0.70, 'b': None, 'by': 'model_a', 'pick': 'BOS', 'result': 'pending'}}
    out = run_accuracy({'games': games, 'picks': picks})
    assert '<b>1 of 2</b> picks right (50.0%)' in out and 'small sample' in out
    assert out.count('<tr><td>') == 2, 'one row per graded pick; the pending one is not listed'
    assert 'Nov 3' not in out, 'the pending game has no row'


@pytest.mark.skipif(NODE is None and not in_ci(), reason='node is not installed')
def test_the_accuracy_page_says_so_before_any_grade():
    out = run_accuracy({'games': [{'id': '1', 'home': 'BOS', 'away': 'NY', 'day': '2026-11-01'}],
                        'picks': {'1': {'a': 0.6, 'b': None, 'by': 'model_a', 'pick': 'BOS', 'result': 'pending'}}})
    assert out.startswith('STATE Nothing graded yet: 1 pick saved.')
