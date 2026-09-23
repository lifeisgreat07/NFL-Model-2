"""
weekly_update.announced_qb_check: record the schedule's announced starters
beside the model's, and flag a game where they differ.

It exists for two reasons (its docstring has the full version): the 2026
forward test of Stage 5's H1 needs to know what was announced on the day
each pick was locked, which only a write-once prediction file can record;
and a game where the model is rating last week's quarterback instead of this
week's starter is exactly where a pick is least trustworthy, so it gets a
note. It changes nothing the model computes.

Run with: pytest tests/test_announced_qb_check.py -v
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'src'))

from weekly_update import announced_qb_check  # noqa: E402

STARTERS = pd.DataFrame([
    {'posteam': 'NYG', 'passer_player_id': '00-W', 'passer_player_name': 'J.Winston'},
    {'posteam': 'TEN', 'passer_player_id': '00-C', 'passer_player_name': 'C.Ward'},
]).set_index('posteam')


def game(home_id='00-W', home_name='Jameis Winston', away_id='00-C', away_name='Cam Ward'):
    return pd.Series({'home_team': 'NYG', 'away_team': 'TEN', 'home_qb_id': home_id,
                      'home_qb_name': home_name, 'away_qb_id': away_id, 'away_qb_name': away_name})


def test_matching_starters_record_both_and_say_nothing():
    fields, notes = announced_qb_check(game(), STARTERS)
    assert notes == []
    assert fields == {
        'model_home_qb_id': '00-W', 'model_home_qb': 'J.Winston',
        'announced_home_qb_id': '00-W', 'announced_home_qb': 'Jameis Winston',
        'model_away_qb_id': '00-C', 'model_away_qb': 'C.Ward',
        'announced_away_qb_id': '00-C', 'announced_away_qb': 'Cam Ward',
    }


def test_a_different_announced_starter_is_flagged_on_that_side_only():
    fields, notes = announced_qb_check(game(home_id='00-D', home_name='Jaxson Dart'), STARTERS)
    assert len(notes) == 1
    assert notes[0].startswith('NYG:')
    assert 'J.Winston' in notes[0] and 'Jaxson Dart' in notes[0]
    assert fields['announced_home_qb_id'] == '00-D'
    assert fields['model_home_qb_id'] == '00-W'


@pytest.mark.parametrize('missing', [None, np.nan, ''])
def test_an_announcement_not_published_yet_is_absent_not_different(missing):
    fields, notes = announced_qb_check(game(home_id=missing, home_name=missing), STARTERS)
    assert notes == []
    assert fields['announced_home_qb_id'] is None
    assert fields['announced_home_qb'] is None


def test_a_team_the_model_has_no_starter_for_is_recorded_as_none_without_a_note():
    fields, notes = announced_qb_check(game(), STARTERS.drop('TEN'))
    assert notes == []
    assert fields['model_away_qb_id'] is None and fields['model_away_qb'] is None
    assert fields['announced_away_qb_id'] == '00-C'


def test_the_note_is_plain_english():
    _, notes = announced_qb_check(game(home_id='00-D', home_name='Jaxson Dart'), STARTERS)
    for word in ('feature', 'qb_matchup', 'lagged', 'dropback', 'trailing'):
        assert word not in notes[0].lower(), word


def _main_source():
    src = (ROOT / 'src' / 'weekly_update.py').read_text(encoding='utf-8')
    start = src.index('def main(season, week):')
    return src[start:]


def test_main_calls_it_for_every_game_and_writes_both_halves():
    body = _main_source()
    assert body.count('announced_qb_check(g, current_starters_idx)') == 1
    assert re.search(r'context_notes = context_notes \+ qb_notes', body), (
        "the notes are computed and then dropped"
    )
    append = body[body.index('predictions.append({'):]
    append = append[:append.index('})') + 2]
    assert '**qb_fields' in append, "the announced and model starters never reach the prediction file"
