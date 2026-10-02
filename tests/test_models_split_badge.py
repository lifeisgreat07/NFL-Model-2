""""Models split" means the two models pick different teams (2026-09-29).

The Week Board card's badge and the Model Disagreement filter tested a
12-point gap between Model A and Model B. On 2026 week 3 that put "Models
agree" on TEN@NYG (Model A TEN 53%, Model B NYG 55%) and on MIN@TB, directly
above the card's own line "Model A picks TEN; Model B and the market pick
NYG." -- and would have called two models 12 points apart on the SAME team a
split. The badge's comment already said it states WHETHER the models
disagree, not by how much. Now the badge, the filter and the card's line all
use one test, modelsSplit(), executed here over the cases that matter.

Run with: pytest tests/test_models_split_badge.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'src' / 'pipeline' / 'dashboard_template.html'
NODE = shutil.which('node')

# Home-side percentages, as the page stores them.
CASES = {
    # 2026 week 3, TEN at NYG: different teams, 8 points apart.
    'ten_nyg': {'home': 'NYG', 'away': 'TEN', 'fbA_home': 47, 'mktB_home': 55},
    # 2026 week 3, MIN at TB: different teams, just under 12 points apart.
    'min_tb': {'home': 'TB', 'away': 'MIN', 'fbA_home': 57.6, 'mktB_home': 46},
    # Same team, far apart: not a split.
    'same_team_far': {'home': 'KC', 'away': 'LV', 'fbA_home': 55, 'mktB_home': 80},
    # One model within the even band: it has picked nobody.
    'one_even': {'home': 'KC', 'away': 'LV', 'fbA_home': 50.5, 'mktB_home': 30},
    # A missing Model B (no line): nothing to disagree with.
    'no_b': {'home': 'KC', 'away': 'LV', 'fbA_home': 40, 'mktB_home': None},
}


def template():
    return TEMPLATE.read_text(encoding='utf-8')


def function_source(src, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


@pytest.fixture(scope='module')
def split():
    if not NODE:
        pytest.skip('node not available')
    t = template()
    band = re.search(r'const CARD_EVEN_BAND = [\d.]+;', t)
    assert band, 'CARD_EVEN_BAND is not findable -- re-anchor this guard'
    js = (band.group(0) + function_source(t, 'cardSide') + function_source(t, 'modelsSplit')
          + f'\nconst C={json.dumps(CASES)};const o={{}};'
            'for(const k in C)o[k]=modelsSplit(C[k]);'
            'process.stdout.write(JSON.stringify(o));')
    r = subprocess.run([NODE, '-e', js], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_different_teams_are_a_split_however_close(split):
    assert split['ten_nyg'] is True, (
        "TEN@NYG, where Model A picks TEN and Model B picks NYG, is not a split")
    assert split['min_tb'] is True


def test_the_same_team_is_never_a_split_however_far_apart(split):
    assert split['same_team_far'] is False


def test_a_model_that_calls_it_even_does_not_split(split):
    assert split['one_even'] is False
    assert split['no_b'] is False


def test_the_badge_the_filter_and_the_card_line_share_the_one_test():
    t = template()
    assert "(modelsSplit(g) ? 'Models split' : 'Models agree')" in t, (
        "the badge no longer asks modelsSplit")
    assert "if(currentFilter==='divergent') return modelsSplit(g);" in t, (
        "the Model Disagreement filter no longer asks modelsSplit, so it can "
        "hide cards whose badge says the models split")
    assert re.search(r'function cardDisagreement\(g\)\{\n  if\(!modelsSplit\(g\)\) return', t)
    assert 'diverge >= 12' not in t
