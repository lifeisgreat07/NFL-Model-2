"""Each Week Board card says where its game stands (Stage 15).

The weekend refresh (src/weekend_refresh.py) writes a snapshot per unfinished
week to data/game_status/. src/generate_dashboard.py joins it onto each game,
and the template's cardStatusLine() turns it into one line under the kickoff.
The line is generated prose over data that can go stale -- Monday morning's
snapshot still calls Monday night's game upcoming when Tuesday grades it -- so
it is executed here over each state, stale ones included, rather than read.

Run with: pytest tests/test_card_status.py -v
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'src' / 'dashboard_template.html'
sys.path.insert(0, str(ROOT / 'src'))

import generate_dashboard as gd  # noqa: E402

NODE = shutil.which('node')

BASE = {'away': 'ATL', 'home': 'GB', 'graded': False}
CASES = {
    'final_ungraded': dict(BASE, status='final', away_score=35, home_score=14),
    'final_graded': dict(BASE, status='final', away_score=35, home_score=14, graded=True),
    'final_zero': dict(BASE, status='final', away_score=0, home_score=3),
    'final_one_score': dict(BASE, status='final', away_score=35, home_score=None),
    'started': dict(BASE, status='started', away_score=None, home_score=None),
    'started_but_graded': dict(BASE, status='started', graded=True),
    'upcoming': dict(BASE, status='upcoming'),
    'upcoming_but_graded': dict(BASE, status='upcoming', graded=True),
    'no_snapshot': dict(BASE, status=None),
}


def template():
    return TEMPLATE.read_text(encoding='utf-8')


def function_source(src, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


@pytest.fixture(scope='module')
def lines():
    if not NODE:
        pytest.skip('node not available')
    js = function_source(template(), 'cardStatusLine') + \
        f'\nconst C={json.dumps(CASES)};const o={{}};for(const k in C)o[k]=cardStatusLine(C[k]);' \
        'process.stdout.write(JSON.stringify(o));'
    # utf-8 explicitly: the line carries a middle dot, and Windows would
    # otherwise decode node's output as cp1252 and fail on a correct line.
    r = subprocess.run([NODE, '-e', js], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_a_final_score_is_away_first_like_the_card(lines):
    assert lines['final_graded'] == 'Final: ATL 35, GB 14'


def test_an_ungraded_final_is_just_the_score(lines):
    """It said "· picks graded on Tuesday" too until 2026-09-28, when Mark
    called that redundant; the graded tag says it once grading happens."""
    assert lines['final_ungraded'] == 'Final: ATL 35, GB 14'
    assert '· picks graded on Tuesday' not in template()


def test_a_shutout_score_of_zero_is_still_a_score(lines):
    """0 is falsy in JavaScript; a truthiness check would drop a real final."""
    assert lines['final_zero'] == 'Final: ATL 0, GB 3'


def test_half_a_score_is_not_a_final(lines):
    assert lines['final_one_score'] == ''


def test_a_started_game_says_the_score_is_not_in(lines):
    assert lines['started'] == 'Kicked off · final score not in yet'


def test_a_stale_snapshot_never_contradicts_the_graded_tag(lines):
    assert lines['started_but_graded'] == ''
    assert lines['upcoming_but_graded'] == ''


def test_upcoming_or_no_snapshot_adds_nothing_to_the_kickoff_line(lines):
    assert lines['upcoming'] == '' and lines['no_snapshot'] == ''


def test_the_line_sits_under_the_kickoff_and_never_replaces_it():
    """The board is sorted by kickoff; the kickoff line must stay on the card."""
    body = function_source(template(), 'renderGames')
    kick = body.find('<div class="card-kickoff">')
    status = body.find('<div class="card-status">')
    assert kick != -1 and status != -1 and kick < status


def test_the_status_line_wears_no_graded_colour():
    rule = re.search(r'\.card-status\{[^}]*\}', template())
    assert rule and '--good' not in rule.group(0) and '--warn' not in rule.group(0)


def test_snapshots_are_joined_onto_their_own_games(tmp_path):
    folder = tmp_path / 'game_status'
    folder.mkdir()
    (folder / '2026_week3.json').write_text(json.dumps({'games': [
        {'away': 'ATL', 'home': 'GB', 'status': 'final', 'away_score': 35, 'home_score': 14,
         'spread_line': 4.5}]}), encoding='utf-8')
    (folder / 'notes.json').write_text('{}', encoding='utf-8')
    status = gd.load_game_status(folder)
    assert list(status) == [(2026, 3)]
    preds = [{'away': 'ATL', 'home': 'GB', 'model_a_home_win_prob': 0.25},
             {'away': 'LAC', 'home': 'BUF', 'model_a_home_win_prob': 0.6}]
    games = gd.build_games_js(preds, {}, status[(2026, 3)])
    assert (games[0]['status'], games[0]['away_score'], games[0]['home_score']) == ('final', 35, 14)
    assert (games[1]['status'], games[1]['away_score'], games[1]['home_score']) == (None, None, None)


def test_no_snapshot_folder_means_no_status_and_says_so(tmp_path, capsys):
    assert gd.load_game_status(tmp_path / 'missing') == {}
    assert 'no weekend refresh has run yet' in capsys.readouterr().out
    games = gd.build_games_js([{'away': 'ATL', 'home': 'GB', 'model_a_home_win_prob': 0.25}], {})
    assert games[0]['status'] is None
