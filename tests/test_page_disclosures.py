"""Three things the NHL's and NBA's pages now say (Stage 68 item 26).

From the 2026-10-09 audit: both tuned settings sit at the top of the grid
their registration searched (E21); a neutral-site game keeps the home edge
in hockey and basketball, where the NFL has a declared rule since v2.6
(E23); and the NBA's drift baseline was measured with the players who
actually played, so the check leans toward flagging (E20). The grid-edge
note is worked out from the results file, in node, here.

Run with: pytest tests/test_page_disclosures.py -v
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')
JS = {'nhl': ROOT / 'src/sports/nhl/pages/nhl.js', 'nba': ROOT / 'src/sports/nba/pages/nba.js'}
TUNING = {'nhl': ('experiments/nhl/stage56/results/tuning.json', 'K_shots'),
          'nba': ('experiments/nba/stage61/results/tuning.json', 'lambda')}


def edge_note(sport, tuning):
    js = JS[sport].read_text(encoding='utf-8')
    fn = js[js.index('function edgeNote('):js.index('function renderMethod(')]
    key = TUNING[sport][1]
    src = fn + f'process.stdout.write(edgeNote({json.dumps(tuning)}, {json.dumps(key)}, "x"));'
    return subprocess.run([NODE, '-e', src], capture_output=True, text=True, check=True).stdout


@pytest.mark.skipif(NODE is None, reason='node is not installed')
@pytest.mark.parametrize('sport', JS)
def test_the_grid_edge_is_said_of_the_real_tuning(sport):
    tuning = json.loads((ROOT / TUNING[sport][0]).read_text(encoding='utf-8'))
    out = edge_note(sport, tuning)
    assert 'At the edge of the grid.' in out and 'is the largest the registered grid searched' in out


@pytest.mark.skipif(NODE is None, reason='node is not installed')
@pytest.mark.parametrize('sport', JS)
def test_it_is_not_said_of_a_setting_inside_the_grid(sport):
    tuning = json.loads((ROOT / TUNING[sport][0]).read_text(encoding='utf-8'))
    key = TUNING[sport][1]
    inside = sorted({g[key] for g in tuning['grid']})[-2]
    assert edge_note(sport, dict(tuning, chosen=dict(tuning['chosen'], **{key: inside}))) == ''


@pytest.mark.parametrize('sport', JS)
def test_methodology_says_neutral_sites_keep_the_home_edge(sport):
    js = JS[sport].read_text(encoding='utf-8')
    assert '<b>Neutral sites.</b>' in js and 'still gives the listed home' in js


def test_the_nba_says_its_drift_check_leans():
    js = JS['nba'].read_text(encoding='utf-8')
    assert '<b>The drift check leans toward flagging.</b>' in js and '${(-Q.M1.diff).toFixed(3)} (M1)' in js


def test_the_nhl_page_carries_its_tuning():
    assert "'tuning': _read(PATHS.experiments / 'stage56' / 'results' / 'tuning.json')," in (
        ROOT / 'src/sports/nhl/site.py').read_text(encoding='utf-8')
