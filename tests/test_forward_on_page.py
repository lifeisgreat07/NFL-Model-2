"""Stage 84 item 2: the forward test is shown on each sport's checks page, tied
to the file the daily run writes.

Both pages render results/<sport>/forward_<season>.json through one function,
forwardHtml, identical in nhl.js and nba.js until Stage 87 shares the pages'
code. The function is run in node over a file src/core/forward_test.py itself
wrote, and every figure in the file must appear on the page as the file has it.

Run with: pytest tests/test_forward_on_page.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from src.core import forward_test as ft
from tests.optional import in_ci
from tests.page_script import day_script

ROOT = Path(__file__).resolve().parents[1]
PAGES = {'nhl': ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js',
         'nba': ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js'}
NODE = shutil.which('node')


def function(sport):
    """forwardHtml and the calibrationTable it calls (Stage 84 item 5)."""
    js = day_script(sport).replace('\r\n', '\n')
    out = []
    for name in ('forwardHtml', 'calibrationTable'):
        m = re.search(rf'function {name}\(f, sport(, level)?\)\{{.*?\n\}}\n', js, re.S)
        assert m, f'{name} is not findable in {sport}.js -- re-anchor this guard'
        out.append(m.group(0))
    return ''.join(out)


def render(sport, f):
    prog = function(sport) + f'process.stdout.write(forwardHtml({json.dumps(f)}, {json.dumps(sport)}));'
    return subprocess.run([NODE, '-e', prog], capture_output=True, text=True, check=True, encoding='utf-8').stdout


def a_file(sport='nba'):
    """A forward-test file written by the module, over twelve days of picks."""
    picks, fin = [], []
    for i in range(36):
        priced = i % 4 != 0
        picks.append({'game_id': str(i), 'model_a': 0.45 + (i % 7) / 30, 'model_b': (0.5 + (i % 5) / 25) if priced else None,
                      'market_source': 'espn' if priced else None,
                      **({'market': {'home_prob': 0.48 + (i % 3) / 20}} if priced else {})})
        fin.append((str(i), f'2026-10-{10 + i // 3}', float(i % 3 != 1)))
    frame = ft.rows(picks, pd.DataFrame(fin, columns=['game_id', 'slate', 'home_win']),
                    {f'2026-10-{10 + d}': 0.54 for d in range(12)})
    return json.loads(json.dumps(ft.report(frame, sport, 2026, f'experiments/{sport}/stage65/registry.json')))


def signed(x):
    return ('&minus;' if x < 0 else '+') + f'{abs(x):.4f}'


def test_both_pages_carry_the_same_function():
    assert function('nhl') == function('nba')


@pytest.mark.skipif(NODE is None and not in_ci(), reason='node not installed')
@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_every_figure_in_the_file_is_on_the_page(sport):
    f = a_file(sport)
    html = render(sport, f)
    assert f"{f['graded_picks']} of them through {f['through']}" in html
    assert f"<code>{f['registered']}</code>" in html
    for name, s in f['scores'].items():
        row = re.search(r'<tr><th scope="row">[^<]+</th>' + ''.join(
            rf'<td class="num">{re.escape(v)}</td>' for v in (
                str(s['games']), f"{s['log_loss']:.4f}", f"{s['brier']:.4f}", f"{s['accuracy'] * 100:.1f}%")), html)
        assert row, f'{name}: its scores are not a row on the page'
    for name, c in f['comparisons'].items():
        # Stage 95 item 37: under 20 game days the game-level interval is printed under it.
        few = c.get('few_days')
        games = (f'<br><span class="forward-games">games [{signed(few["game_low"])}, {signed(few["game_high"])}]</span>'
                 if few else '')
        cells = (f'<td class="num">{c["games"]}</td><td class="num">{c["days"]}</td>'
                 f'<td class="num">{signed(c["diff"])}</td><td class="num">[{signed(c["low"])}, {signed(c["high"])}]{games}</td>')
        assert cells in html, f'{name}: {cells}'
    assert f"{f['interval_rule']['level'] * 100:.2f}% interval" in html
    assert f'class="{sport}-lede"' in html and f'metrics-table {sport}-table' in html


@pytest.mark.skipif(NODE is None and not in_ci(), reason='node not installed')
def test_nothing_graded_says_so_and_a_thin_comparison_says_why():
    assert 'nothing to score' in render('nhl', None)
    assert 'nothing to score' in render('nhl', {'graded_picks': 0})
    f = a_file()
    f['comparisons']['model_b_minus_market'] = {'games': 1, 'days': 1, 'note': 'too few games to resample'}
    assert '<td colspan="2">too few games to resample</td>' in render('nba', f)


@pytest.mark.skipif(NODE is None and not in_ci(), reason='node not installed')
def test_the_page_judges_nothing():
    html = render('nba', a_file())
    assert not re.search(r'ACCEPT|REJECT|INCONCLUSIVE|significant', html)
    assert 'reported, not judged' in html


@pytest.mark.parametrize('sport, data', [('nhl', 'DATA'), ('nba', 'BD')])
def test_the_checks_page_renders_it_from_the_file_the_build_passes(sport, data):
    js = day_script(sport)
    body = re.search(r'function renderReliability\(\)\{.*?\n\}\n', js, re.S).group(0)
    assert '<h2 class="section-title">The forward test so far</h2>' in body
    assert f"${{forwardHtml({data}.forward, '{sport}')}}" in body
    site = (ROOT / 'src' / 'sports' / sport / 'site.py').read_text(encoding='utf-8')
    reader = '_read' if sport == 'nhl' else '_maybe'
    assert f"'forward': {reader}(PATHS.results / f'forward_{{season}}.json')," in site
