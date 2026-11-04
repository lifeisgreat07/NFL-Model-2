"""Stage 84 item 7: the NHL's held-out table gains the registered Brier column,
from one renderer both sports share.

The NHL registration names Brier as its secondary metric
(experiments/nhl/stage56/registry.json, "secondary_metric") and its results
file carries it, but the Model Lab table printed only log loss and accuracy.
Both pages now render the held-out scores through heldOutTable, identical in
nhl.js and nba.js, and every figure in each results file is on its page.

Run with: pytest tests/test_heldout_table.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGES = {'nhl': ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js',
         'nba': ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js'}
RESULTS = {'nhl': ROOT / 'experiments' / 'nhl' / 'stage56' / 'results' / 'confirmation.json',
           'nba': ROOT / 'experiments' / 'nba' / 'stage61' / 'results' / 'confirmation.json'}
NODE = shutil.which('node')


def function(sport):
    js = PAGES[sport].read_text(encoding='utf-8').replace('\r\n', '\n')
    m = re.search(r'function heldOutTable\(scores, names, sport\)\{.*?\n\}\n', js, re.S)
    assert m, f'heldOutTable is not findable in {sport}.js -- re-anchor this guard'
    return m.group(0)


def names(sport):
    """The rows each page asks for, read from its renderModelLab call."""
    js = PAGES[sport].read_text(encoding='utf-8').replace('\r\n', '\n')
    body = js[js.index('function renderModelLab(){'):]
    if sport == 'nhl':
        arg = re.search(r"\$\{heldOutTable\(s, (\[\[.*?\]\]), 'nhl'\)\}", body).group(1)
        return json.loads(arg.replace("'", '"'))
    assert "${heldOutTable(B.scores, FORECASTS, 'nba')}" in body
    block = re.search(r'const FORECASTS = (\[.*?\]);', js, re.S).group(1)
    return json.loads(re.sub(r'\s+', ' ', block).replace("'", '"').replace(', ]', ']'))


def render(sport):
    scores = json.loads(RESULTS[sport].read_text(encoding='utf-8'))['scores']
    prog = function(sport) + (f'process.stdout.write(heldOutTable({json.dumps(scores)}, '
                              f'{json.dumps(names(sport))}, {json.dumps(sport)}));')
    return scores, subprocess.run([NODE, '-e', prog], capture_output=True, text=True, check=True,
                                  encoding='utf-8').stdout


def test_both_pages_carry_the_same_function():
    assert function('nhl') == function('nba')


def test_the_nhl_registration_names_brier_and_its_file_has_it():
    reg = json.loads((ROOT / 'experiments' / 'nhl' / 'stage56' / 'registry.json').read_text(encoding='utf-8'))
    assert 'brier' in json.dumps(reg).lower()
    scores = json.loads(RESULTS['nhl'].read_text(encoding='utf-8'))['scores']
    assert all('brier' in scores[k] for k in ('model_a', 'base_rate', 'model_b', 'market'))


@pytest.mark.skipif(NODE is None, reason='node not installed')
@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_every_held_out_figure_is_on_the_page_with_brier(sport):
    scores, html = render(sport)
    assert '<th scope="col" class="num">Brier</th>' in html
    rows = names(sport)
    assert len(rows) >= 4
    for label, key in rows:
        v = scores[key]
        cells = (f'<tr><th scope="row">{label}</th><td class="num">{v["games"]:,}</td>'
                 f'<td class="num">{v["log_loss"]:.4f}</td><td class="num">{v["brier"]:.4f}</td>'
                 f'<td class="num">{v["accuracy"] * 100:.1f}%</td></tr>')
        assert cells in html, f'{sport} {key}: {cells}'
