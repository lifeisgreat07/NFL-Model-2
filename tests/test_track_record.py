"""Stage 90 item 1: the cross-sport track record on the home page.

Model B, the market and the base rate for each sport, log loss live beside
the backtest and the live Brier score, read from committed files by
src/site/track_record.py and drawn by the home page's trackRecord.

Run with: pytest tests/test_track_record.py -v
"""
import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

from src.site import home
from src.site import track_record as tr
from tests.js_source import function_source

ROOT = Path(__file__).resolve().parents[1]
HOME_JS = ROOT / 'src' / 'site' / 'home' / 'home.js'


def one_line(src, name):
    """A one-line `function name(...)` of the page script."""
    (line,) = [ln for ln in src.splitlines() if ln.startswith(f'function {name}(')]
    return line + '\n'


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding='utf-8')


def score(ll, b, n):
    return {'log_loss': ll, 'brier': b, 'games': n}


def day_fixture(root):
    write(root / 'results' / 'nhl' / 'forward_2026.json', {
        'season': 2026, 'through': '2026-11-03',
        'scores': {'model_b': score(0.64, 0.22, 170), 'market': score(0.65, 0.23, 170),
                   'base_rate': score(0.69, 0.25, 190)},
        'calibration': {'model_b': {'slope': {'value': 1.234, 'low': 0.5, 'high': 2.0}}}})
    write(root / tr.CONFIRMATION['nhl'], {'scores': {'model_b': score(0.67, 0.24, 2600),
                                                      'market': score(0.669, 0.238, 2600),
                                                      'base_rate': score(0.6896, 0.248, 2790)}})
    # A frozen copy beside it is not this season's live file (Stage 95 item 36).
    write(root / 'results' / 'nhl' / 'forward_2026_regular_season_final.json', {'season': 1999})


def test_a_day_sport_reads_its_forward_file_beside_its_confirmation_seasons(tmp_path):
    day_fixture(tmp_path)
    got = tr.day_sport('nhl', tmp_path)
    assert got['season'] == 2026 and got['through'] == '2026-11-03'
    assert [(r['label'], r['live']['log_loss'], r['backtest']['log_loss']) for r in got['rows']] == [
        ('Model B', 0.64, 0.67), ('Market', 0.65, 0.669), ('Base rate', 0.69, 0.6896)]
    assert got['rows'][2]['live']['games'] == 190 and got['rows'][0]['backtest']['games'] == 2600
    assert got['calibration'] == {'value': 1.23, 'low': 0.5, 'high': 2.0}


def test_before_a_forward_file_a_day_sport_has_no_record(tmp_path):
    assert tr.day_sport('nba', tmp_path) is None


def test_the_nfl_is_scored_from_its_graded_weeks(tmp_path):
    base = 0.55
    write(tmp_path / 'data' / 'nfl' / 'calibration.json', {
        'model_version': '2.4', 'backtest_seasons': [2022, 2025],
        'models': {'model_a': {'metrics': {'n': 1000}, 'decomposition': {'base_rate': base}},
                   'model_b': {'metrics': {'n': 1000, 'log_loss': 0.61, 'brier': 0.21}},
                   'market': {'metrics': {'n': 1000, 'log_loss': 0.62, 'brier': 0.22}}}})
    games = [{'actual_home_win': 1, 'model_b_home_win_prob': 0.8, 'market_prob_home': 0.7},
             {'actual_home_win': 0, 'model_b_home_win_prob': 0.4, 'market_prob_home': None},
             {'actual_home_win': None, 'model_b_home_win_prob': 0.9, 'market_prob_home': 0.9}]
    write(tmp_path / 'results' / 'nfl' / '2026_week1_graded.json', games)
    write(tmp_path / 'results' / 'nfl' / '2025_week18_graded.json', [{'actual_home_win': 1, 'model_b_home_win_prob': 0.01}])
    got = tr.nfl(tmp_path)
    rows = {r['key']: r for r in got['rows']}
    assert got['season'] == 2026 and got['through'] == 'week 1'
    assert rows['model_b']['live'] == {'log_loss': round((-math.log(0.8) - math.log(0.6)) / 2, 4),
                                       'brier': round((0.04 + 0.16) / 2, 4), 'games': 2}
    assert rows['market']['live']['games'] == 1, 'a game with no price is left out of the market row only'
    assert rows['base_rate']['live']['log_loss'] == round((-math.log(base) - math.log(1 - base)) / 2, 4)
    assert rows['base_rate']['backtest']['log_loss'] == round(-(base * math.log(base) + (1 - base) * math.log(1 - base)), 4)
    assert rows['model_b']['backtest'] == {'log_loss': 0.61, 'brier': 0.21, 'games': 1000}
    assert 'model v2.4' in got['note'] and got['backtest_label'] == 'the 2022-2025 seasons'


def test_the_committed_files_give_every_sport_a_record_that_matches_its_sources():
    got = tr.track_record()
    for sport in ('nhl', 'nba'):
        fwd = json.loads((ROOT / 'results' / sport / 'forward_2026.json').read_text(encoding='utf-8'))
        assert got[sport]['rows'][0]['live']['log_loss'] == round(fwd['scores']['model_b']['log_loss'], 4)
    cal = json.loads((ROOT / 'data' / 'nfl' / 'calibration.json').read_text(encoding='utf-8'))
    assert got['nfl']['rows'][1]['backtest']['log_loss'] == round(cal['models']['market']['metrics']['log_loss'], 4)
    assert home.facts()['track'] == got


@pytest.mark.skipif(shutil.which('node') is None, reason='node is not installed')
def test_the_home_page_draws_each_sport_and_nothing_without_figures():
    src = HOME_JS.read_text(encoding='utf-8')
    rec = tr.track_record()
    rec['nhl']['note'] = '<b>bold</b>'
    js = (one_line(src, 'esc') + "const SPORT_NAME = {nfl:'NFL', nhl:'NHL', nba:'NBA'};\n"
          + one_line(src, 'trackNum') + function_source(src, 'trackTable', at_line_start=True)
          + function_source(src, 'trackRecord', at_line_start=True)
          + f'process.stdout.write(JSON.stringify([trackRecord({json.dumps(rec)}), trackRecord({{}}), trackRecord(undefined)]));')
    out = json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True).stdout)
    page = out[0]
    for sport in ('NFL', 'NHL', 'NBA'):
        assert f'<h3>{sport} 2026</h3>' in page
    b = rec['nba']['rows'][0]
    assert f"<tr><th scope=\"row\">Model B</th><td>{b['live']['log_loss']:.3f}</td><td>{b['backtest']['log_loss']:.3f}</td>" in page
    assert '&lt;b&gt;bold&lt;/b&gt;' in page and '<b>bold</b>' not in page
    assert out[1] == '' and out[2] == '', 'no tables at all when there is nothing to show'


def test_the_section_is_hidden_until_there_is_something_to_show():
    page = (ROOT / 'src' / 'site' / 'home' / 'page.html').read_text(encoding='utf-8')
    assert '<section class="home-track" id="home-track" aria-labelledby="home-track-title" hidden>' in page
    src = HOME_JS.read_text(encoding='utf-8')
    assert "  if(tables){\n    document.getElementById('home-track-tables').innerHTML = tables;\n" \
           "    document.getElementById('home-track').hidden = false;\n  }\n" in src.replace('\r\n', '\n')
