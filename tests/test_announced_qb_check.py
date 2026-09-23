"""
Which quarterback each weekly pick is made with: weekly_update.resolve_starters
and load_qb_overrides.

Precedence (decided 2026-09-22, v2.5): a sourced override, then the
schedule's listed starter, then last game's starter -- the last only when
nothing better exists, and never silently. The published backtest rates
each game's real starter; this is what makes the live pick match it.

The file keeps its original name because it was created for the first half
of this change (recording the listed starter); the guards below cover both.

Run with: pytest tests/test_announced_qb_check.py -v
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'src'))

from weekly_update import QBOverrideError, load_qb_overrides, resolve_starters  # noqa: E402

LAST = pd.DataFrame([
    {'posteam': 'NYG', 'passer_player_id': '00-0000001', 'passer_player_name': 'J.Winston'},
    {'posteam': 'TEN', 'passer_player_id': '00-0000002', 'passer_player_name': 'C.Ward'},
]).set_index('posteam')


def game(home_id='00-0000001', home_name='Jameis Winston', away_id='00-0000002', away_name='Cam Ward'):
    return pd.Series({'home_team': 'NYG', 'away_team': 'TEN', 'home_qb_id': home_id,
                      'home_qb_name': home_name, 'away_qb_id': away_id, 'away_qb_name': away_name})


OVERRIDE = {'NYG': {'team': 'NYG', 'player_id': '00-0000009', 'player_name': 'Russell Wilson',
                    'source': 'https://example.com/nyg'}}


# ---------------------------------------------------------------- precedence

def test_listed_starter_matching_last_game_is_used_quietly():
    per_side, fields, notes = resolve_starters(game(), LAST, {})
    assert per_side == {'home': ('00-0000001', 0), 'away': ('00-0000002', 0)}
    assert fields['home_qb_basis'] == fields['away_qb_basis'] == 'announced'
    assert notes == []


def test_a_different_listed_starter_is_what_the_pick_uses_and_is_flagged_as_a_change():
    per_side, fields, notes = resolve_starters(game(home_id='00-0000005', home_name='Jaxson Dart'), LAST, {})
    assert per_side['home'] == ('00-0000005', 1)
    assert fields['home_qb'] == 'Jaxson Dart' and fields['last_game_home_qb'] == 'J.Winston'
    assert len(notes) == 1 and notes[0].startswith('NYG:') and 'Jaxson Dart' in notes[0]


def test_an_override_beats_the_schedule_and_cites_its_source():
    per_side, fields, notes = resolve_starters(game(home_id='00-0000005', home_name='Jaxson Dart'), LAST, {}, OVERRIDE)
    assert per_side['home'] == ('00-0000009', 1)
    assert fields['home_qb_basis'] == 'override'
    assert fields['announced_home_qb_id'] == '00-0000005', "the schedule's claim is still recorded"
    assert 'https://example.com/nyg' in notes[0]


@pytest.mark.parametrize('missing', [None, np.nan, ''])
def test_nothing_listed_falls_back_to_last_game_says_so_and_keeps_the_old_flag(missing):
    per_side, fields, notes = resolve_starters(game(home_id=missing, home_name=missing), LAST, {'NYG': 1})
    assert per_side['home'] == ('00-0000001', 1), "the old live change flag is kept on the fallback"
    assert fields['home_qb_basis'] == 'last_game'
    assert fields['announced_home_qb_id'] is None
    assert any('no starter has been listed' in n for n in notes)


def test_a_team_with_no_history_and_no_listing_yields_no_quarterback():
    per_side, fields, notes = resolve_starters(game(away_id=None, away_name=None), LAST.drop('TEN'), {})
    assert per_side['away'] == (None, 0)


def test_the_notes_are_plain_english():
    _, _, notes = resolve_starters(game(home_id='00-0000005', home_name='Jaxson Dart', away_id=None), LAST, {}, OVERRIDE)
    assert len(notes) == 2
    for n in notes:
        for word in ('feature', 'qb_matchup', 'lagged', 'dropback', 'trailing', 'override'):
            assert word not in n.lower(), (word, n)


# ----------------------------------------------------------------- overrides

def write(tmp_path, entries):
    (tmp_path / '2026_week4.json').write_text(json.dumps(entries), encoding='utf-8')
    return tmp_path


def test_no_override_file_means_no_overrides(tmp_path):
    assert load_qb_overrides(2026, 4, tmp_path) == {}


def test_a_valid_override_file_loads_by_team(tmp_path):
    d = write(tmp_path, list(OVERRIDE.values()))
    assert load_qb_overrides(2026, 4, d) == OVERRIDE


@pytest.mark.parametrize('bad, message', [
    ({'source': ''}, 'missing'),
    ({'source': 'twitter said so'}, 'must be a link'),
    ({'player_id': 'R.Wilson'}, 'GSIS'),
    ({'player_name': None}, 'missing'),
])
def test_an_untrustworthy_override_fails_the_run(tmp_path, bad, message):
    entry = {**OVERRIDE['NYG'], **bad}
    with pytest.raises(QBOverrideError, match=message):
        load_qb_overrides(2026, 4, write(tmp_path, [entry]))


def test_two_overrides_for_one_team_fail(tmp_path):
    with pytest.raises(QBOverrideError, match='two overrides'):
        load_qb_overrides(2026, 4, write(tmp_path, [OVERRIDE['NYG'], OVERRIDE['NYG']]))


# -------------------------------------------------------------------- wiring

def _main_source():
    src = (ROOT / 'src' / 'weekly_update.py').read_text(encoding='utf-8')
    return src[src.index('def main(season, week):'):]


def test_main_predicts_with_the_resolved_starter_and_records_it():
    body = _main_source()
    assert body.count('qb_overrides = load_qb_overrides(season, week)') == 1
    assert body.count('resolve_starters(\n            g, current_starters_idx, current_qb_changed, qb_overrides)') == 1
    assert "qb['trailing_rating'](home_qb_id, qb_cutoff)" in body
    assert 'qb_change_diff = home_qb_changed - away_qb_changed' in body
    assert "current_starters_idx.loc[home, 'passer_player_id']" not in body, (
        "the pick is still rated off last game's quarterback"
    )
    append = body[body.index('predictions.append({'):]
    append = append[:append.index('})') + 2]
    assert '**qb_fields' in append, "who the pick was made with never reaches the prediction file"
