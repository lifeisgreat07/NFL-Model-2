"""The day sports' grading at its edges (Stage 96 item 44, audit 7 T8).

`grade` turns each saved pick into correct, wrong, cancelled or pending, and
its output is the record the page and the forward test count. The suite held
the four ordinary cases; these are the ones a real season produces and none
had pinned: a final game whose score is not in yet, a pick whose game has left
the schedule, and a game postponed and then replayed under the same id.

Run with: pytest tests/test_grade_edges.py -v
"""
import json

import pandas as pd
import pytest

from src.sports.nba import daily as nba_daily
from src.sports.nhl import daily as nhl_daily

DAILY = {'nhl': nhl_daily, 'nba': nba_daily}


def picks(folder, *pairs):
    for gid, pick in pairs:
        (folder / f'{gid}.json').write_text(json.dumps({'game_id': gid, 'pick': pick}), encoding='utf-8')


def game(gid, status, home_win, home='TBL', away='PHI'):
    return {'game_id': gid, 'home': home, 'away': away, 'status': status, 'home_win': home_win}


def results(sport, folder, rows):
    return {r['game_id']: r['result'] for r in DAILY[sport].grade(folder, pd.DataFrame(rows))}


@pytest.mark.parametrize('sport', DAILY)
@pytest.mark.parametrize('missing', [pd.NA, float('nan'), None], ids=['NA', 'nan', 'None'])
def test_a_final_game_with_no_result_is_pending_not_a_crash(sport, missing, tmp_path):
    picks(tmp_path, ('1', 'TBL'), ('2', 'TBL'))
    got = results(sport, tmp_path, [game('1', 'final', missing), game('2', 'final', 1)])
    assert got == {'1': 'pending', '2': 'correct'}


@pytest.mark.parametrize('sport', DAILY)
def test_a_pick_whose_game_left_the_schedule_is_pending(sport, tmp_path):
    picks(tmp_path, ('1', 'TBL'), ('9', 'BOS'))
    assert results(sport, tmp_path, [game('1', 'final', 0)]) == {'1': 'wrong', '9': 'pending'}


@pytest.mark.parametrize('sport', DAILY)
def test_a_postponed_game_is_pending_and_graded_once_replayed(sport, tmp_path):
    picks(tmp_path, ('1', 'PHI'))
    assert results(sport, tmp_path, [game('1', 'postponed', pd.NA)]) == {'1': 'pending'}
    assert results(sport, tmp_path, [game('1', 'final', 0)]) == {'1': 'correct'}


@pytest.mark.parametrize('sport', DAILY)
def test_a_cancelled_game_is_cancelled_whatever_its_score_says(sport, tmp_path):
    picks(tmp_path, ('1', 'TBL'))
    assert results(sport, tmp_path, [game('1', 'cancelled', 1)]) == {'1': 'cancelled'}
