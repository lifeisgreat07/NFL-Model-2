"""The backfill may only add, and the suite proves it rather than trusting it.

`predictions/` is write-once by design, and that refusal is what makes "saved
before kickoff" a claim anyone can trust. src/backfill_game_dates.py bends it
under a narrow exception -- three schedule facts, not model outputs -- and an
exception defended only by a docstring is an exception that widens.

So the property is executed against a temporary copy: only the three fields
may ever appear, no existing value may change, a saved value that DISAGREES
with the schedule is reported rather than overwritten, and an unmatched record
is reported rather than guessed at.

The schedule loader is injected. The suite has no network, and a backfill that
could only be tested by reaching nflverse would not be tested at all.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import backfill_game_dates as bf  # noqa: E402


def fake_loader(rows):
    """A stand-in for data_loader.load_schedule returning a DataFrame."""
    import pandas as pd

    def load(season):
        return pd.DataFrame(rows)
    return load


ROWS = [
    {'week': 1, 'home_team': 'SEA', 'away_team': 'NE',
     'gameday': '2026-09-09', 'gametime': '20:20', 'weekday': 'Wednesday'},
    {'week': 1, 'home_team': 'CIN', 'away_team': 'TB',
     'gameday': '2026-09-13', 'gametime': '13:00', 'weekday': 'Sunday'},
]


def write_week(tmp_path, records):
    path = tmp_path / '2026_week1.json'
    path.write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')
    return path


def test_it_adds_only_the_three_fields_and_changes_nothing_else(tmp_path):
    """The exception, stated as an assertion.

    Every original key must survive with its original value. This is the only
    thing standing between "a narrow, defensible amendment" and "a script that
    edits saved predictions", and the difference is not visible in a diff of
    sixteen records nobody reads line by line.
    """
    before = [
        {'season': 2026, 'week': 1, 'home': 'SEA', 'away': 'NE',
         'model_a_home_win_prob': 0.4431, 'confidence_rank': 7,
         'context_notes': [], 'why': {'qb_matchup': -0.2857}},
        {'season': 2026, 'week': 1, 'home': 'CIN', 'away': 'TB',
         'model_a_home_win_prob': 0.5102, 'confidence_rank': 3,
         'context_notes': ['a note'], 'why': {'qb_matchup': 0.1}},
    ]
    path = write_week(tmp_path, before)

    changed, notes = bf.run(False, load_schedule=fake_loader(ROWS),
                            pred_dir=tmp_path)
    after = json.loads(path.read_text(encoding='utf-8'))

    assert changed and not notes, notes
    assert len(after) == len(before)
    for b, a in zip(before, after):
        assert (a['home'], a['away']) == (b['home'], b['away']), 'order moved'
        for key, value in b.items():
            assert a[key] == value, (
                f'{key} changed from {value!r} to {a[key]!r}. The backfill may '
                'only ADD; anything else makes a saved prediction editable.')
        assert set(a) - set(b) == {'gameday', 'gametime_et', 'weekday'}
    assert after[0]['gameday'] == '2026-09-09'
    assert after[0]['gametime_et'] == '20:20'


def test_a_saved_value_that_disagrees_with_the_schedule_is_reported_not_fixed(tmp_path):
    """The case where overwriting would be the tempting thing to do.

    A record already carrying a different date means the schedule moved after
    the prediction was saved, or the join is wrong. Either is a finding about
    the data. Silently rewriting it to match today's schedule would destroy
    the evidence and look like a successful run.
    """
    path = write_week(tmp_path, [
        {'season': 2026, 'week': 1, 'home': 'SEA', 'away': 'NE',
         'gameday': '2026-09-08', 'model_a_home_win_prob': 0.44},
    ])

    changed, notes = bf.run(False, load_schedule=fake_loader(ROWS),
                            pred_dir=tmp_path)
    after = json.loads(path.read_text(encoding='utf-8'))

    assert after[0]['gameday'] == '2026-09-08', (
        'the backfill overwrote a saved value that disagreed with the '
        'schedule. That is the one thing it must never do.')
    assert any('already has' in n for n in notes), notes


def test_an_unmatched_record_is_reported_rather_than_guessed_at(tmp_path):
    path = write_week(tmp_path, [
        {'season': 2026, 'week': 1, 'home': 'XXX', 'away': 'YYY',
         'model_a_home_win_prob': 0.5},
    ])

    changed, notes = bf.run(False, load_schedule=fake_loader(ROWS),
                            pred_dir=tmp_path)
    after = json.loads(path.read_text(encoding='utf-8'))

    assert not changed
    assert 'gameday' not in after[0], 'a record with no schedule row was dated'
    assert any('no schedule row' in n for n in notes), notes


def test_check_mode_writes_nothing(tmp_path):
    """--check is what makes "the corpus is settled" a claim rather than a
    habit, so it has to be provably read-only."""
    path = write_week(tmp_path, [
        {'season': 2026, 'week': 1, 'home': 'SEA', 'away': 'NE',
         'model_a_home_win_prob': 0.44},
    ])
    original = path.read_text(encoding='utf-8')

    changed, _ = bf.run(True, load_schedule=fake_loader(ROWS),
                        pred_dir=tmp_path)

    assert changed, '--check should still report what it would do'
    assert path.read_text(encoding='utf-8') == original, '--check wrote to disk'


def test_running_it_twice_is_a_no_op(tmp_path):
    """Idempotence, because a backfill that keeps finding work is a backfill
    nobody can tell has finished."""
    path = write_week(tmp_path, [
        {'season': 2026, 'week': 1, 'home': 'SEA', 'away': 'NE',
         'model_a_home_win_prob': 0.44},
    ])

    bf.run(False, load_schedule=fake_loader(ROWS), pred_dir=tmp_path)
    settled = path.read_text(encoding='utf-8')
    changed, notes = bf.run(False, load_schedule=fake_loader(ROWS),
                            pred_dir=tmp_path)

    assert not changed, 'the second run still found fields to add'
    assert not notes, notes
    assert path.read_text(encoding='utf-8') == settled
