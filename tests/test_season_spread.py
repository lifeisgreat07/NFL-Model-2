"""Stage 85 item 3: the drift baseline's season-to-season spread is printed
beside it, from a file the backtest's own walk-forward wrote, tied to the
registered baseline.

Run with: pytest tests/test_season_spread.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from src.core import season_spread

ROOT = Path(__file__).resolve().parents[1]
FILES = {'nhl': ROOT / 'experiments' / 'nhl' / 'stage56' / 'results' / 'model_a_by_season.json',
         'nba': ROOT / 'experiments' / 'nba' / 'stage61' / 'results' / 'model_a_by_season.json'}
REGISTRIES = {'nhl': ROOT / 'experiments' / 'nhl' / 'stage56' / 'registry.json',
              'nba': ROOT / 'experiments' / 'nba' / 'stage61' / 'registry.json'}
PAGES = {'nhl': ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js',
         'nba': ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js'}
NODE = shutil.which('node')


def doc(sport):
    return json.loads(FILES[sport].read_text(encoding='utf-8'))


# --- the helper ---------------------------------------------------------------------------------

def test_the_helper_scores_each_season_and_pools_the_confirmation_seasons():
    table = pd.DataFrame({'game_id': list('abcdef'), 'season': [2022, 2022, 2023, 2024, 2024, 2025]})
    loss = {'a': 0.6, 'b': 0.7, 'c': 0.5, 'd': 0.66, 'e': 0.68, 'f': 0.7}
    wf = lambda t, cols, seasons: pd.Series({g: 0.5 for g in t.loc[t['season'].isin(seasons), 'game_id']})
    sc = lambda p, t: {'games': len(p), 'log_loss': sum(loss[g] for g in p.index) / len(p)}
    out = season_spread.spread(wf, sc, table, ['x'], [2022, 2023], [2024, 2025], baseline=(0.66 + 0.68 + 0.7) / 3)
    assert [(r['label'], r['role'], r['games']) for r in out['seasons']] == [
        ('2022-23', 'validation', 2), ('2023-24', 'validation', 1), ('2024-25', 'confirmation', 2),
        ('2025-26', 'confirmation', 1)]
    assert out['baseline']['pooled_confirmation'] == pytest.approx(0.68) and out['baseline']['agrees'] is True
    assert out['spread'] == {'low': 0.5, 'high': 0.7, 'range': pytest.approx(0.2)}


def test_a_pooled_figure_that_misses_the_baseline_says_so():
    table = pd.DataFrame({'game_id': ['a'], 'season': [2024]})
    wf = lambda t, cols, seasons: pd.Series({'a': 0.5}) if 2024 in seasons else pd.Series(dtype=float)
    sc = lambda p, t: {'games': len(p), 'log_loss': 0.7 if len(p) else 0.0}
    out = season_spread.spread(wf, sc, table, ['x'], [], [2024], baseline=0.69)
    assert out['baseline']['agrees'] is False


# --- the committed files ----------------------------------------------------------------------

@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_the_file_covers_the_registered_seasons_and_gives_back_the_baseline(sport):
    d = doc(sport)
    p = json.loads(REGISTRIES[sport].read_text(encoding='utf-8'))['protocol']
    assert [r['season'] for r in d['seasons']] == [*p['validation_seasons'], *p['confirmation_seasons']]
    baseline = json.loads((ROOT / 'data' / sport / 'drift_baseline.json').read_text(encoding='utf-8'))['baseline']['value']
    assert d['baseline']['value'] == baseline and d['baseline']['agrees'] is True
    assert abs(d['baseline']['pooled_confirmation'] - baseline) < 1e-9
    conf = [r for r in d['seasons'] if r['role'] == 'confirmation']
    assert sum(r['games'] for r in conf) == d['baseline']['games']


@pytest.mark.parametrize('sport, key', [('nhl', 'K_shots'), ('nba', 'lambda')])
def test_the_settings_are_the_ones_validation_chose(sport, key):
    stage = 'stage56' if sport == 'nhl' else 'stage61'
    chosen = json.loads((ROOT / 'experiments' / sport / stage / 'results' / 'tuning.json').read_text(encoding='utf-8'))['chosen']
    assert doc(sport)['settings'] == {'H_days': chosen['H_days'], key: chosen[key]}


# --- the pages ----------------------------------------------------------------------------------

def function(sport):
    js = PAGES[sport].read_text(encoding='utf-8').replace('\r\n', '\n')
    m = re.search(r'function spreadHtml\(s, sport\)\{.*?\n\}\n', js, re.S)
    assert m, f'spreadHtml is not findable in {sport}.js -- re-anchor this guard'
    return m.group(0), js


def test_both_pages_carry_the_same_function():
    assert function('nhl')[0] == function('nba')[0]


@pytest.mark.skipif(NODE is None, reason='node not installed')
@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_every_season_in_the_file_is_on_the_page(sport):
    fn, _ = function(sport)
    d = doc(sport)
    html = subprocess.run([NODE, '-e', fn + f'process.stdout.write(spreadHtml({json.dumps(d)}, {json.dumps(sport)}));'],
                          capture_output=True, text=True, check=True, encoding='utf-8').stdout
    for r in d['seasons']:
        assert f"{r['label']} {r['log_loss']:.4f}" in html, r['label']
    assert f"a range of {d['spread']['range']:.4f}" in html
    assert f"The baseline pools the last two ({d['baseline']['pooled_confirmation']:.4f})" in html


@pytest.mark.parametrize('sport, data, reader, stage', [('nhl', 'DATA', '_read', 'stage56'), ('nba', 'BD', '_maybe', 'stage61')])
def test_the_checks_page_shows_it_under_the_drift_check(sport, data, reader, stage):
    _, js = function(sport)
    body = js[js.index('function renderReliability(){'):]
    assert f"${{spreadHtml({data}.spread, '{sport}')}}" in body
    assert body.index(f"${{spreadHtml({data}.spread, '{sport}')}}") < body.index('The forward test so far')
    site = (ROOT / 'src' / 'sports' / sport / 'site.py').read_text(encoding='utf-8')
    assert f"'spread': {reader}(PATHS.experiments / '{stage}' / 'results' / 'model_a_by_season.json')," in site
