"""A week nobody locked is recorded as skipped, and the next run moves on (Stage 24).

The 2026-09-28 audit, confirmed: determine_next_week() was "one past the
highest saved week", and main() refuses a week whose games have all kicked
off with nothing locked. So one missed lock (both scheduled runs failing)
made every later run pick the same week and refuse it, for the rest of the
season, and the only manual way out -- an empty picks file -- is a file the
Pages build refuses.

Now main() records the week in predictions/nfl/skipped/ before failing, and
determine_next_week() counts a recorded skip as done. The run still fails and
still opens its issue (Stage 4). Everything else that reads saved picks globs
predictions/nfl/*_week*.json without recursing, so a skip is invisible to it;
the last tests here hold that for the readers that matter.
"""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

from src.sports.nfl import weekly_update as wu

NOW = pd.Timestamp('2026-10-05 12:00', tz='UTC')


def picks(folder, *weeks, season=2026):
    folder.mkdir(parents=True, exist_ok=True)
    for w in weeks:
        (folder / f'{season}_week{w}.json').write_text('[]', encoding='utf-8')


# ---- determine_next_week ---------------------------------------------------

def test_nothing_saved_starts_at_week_one(tmp_path):
    assert wu.determine_next_week(2026, tmp_path, tmp_path / 'skipped') == 1


def test_one_past_the_highest_saved_week(tmp_path):
    picks(tmp_path, 1, 2, 3)
    assert wu.determine_next_week(2026, tmp_path, tmp_path / 'skipped') == 4


def test_a_recorded_skip_counts_as_done(tmp_path):
    """The audit's case: week 4 was never locked. Before Stage 24 this
    returned 4 on every run for the rest of the season."""
    picks(tmp_path, 1, 2, 3)
    wu.record_skipped_week(2026, 4, 'test', NOW, tmp_path / 'skipped')
    assert wu.determine_next_week(2026, tmp_path, tmp_path / 'skipped') == 5


def test_other_seasons_do_not_count(tmp_path):
    picks(tmp_path, 1, 2)
    picks(tmp_path, 17, season=2025)
    wu.record_skipped_week(2025, 18, 'test', NOW, tmp_path / 'skipped')
    assert wu.determine_next_week(2026, tmp_path, tmp_path / 'skipped') == 3


def test_the_defaults_are_the_real_folders():
    assert wu.SKIPPED_DIR == wu.PRED_DIR / 'skipped'


# ---- record_skipped_week ---------------------------------------------------

def test_the_record_says_what_and_when(tmp_path):
    path = wu.record_skipped_week(2026, 4, 'every game kicked off with nothing locked',
                                  NOW, tmp_path)
    assert path == tmp_path / '2026_week4.json'
    rec = json.loads(path.read_text(encoding='utf-8'))
    assert rec == {'season': 2026, 'week': 4,
                   'reason': 'every game kicked off with nothing locked',
                   'recorded_utc': '2026-10-05T12:00:00+00:00'}


def test_a_record_is_write_once(tmp_path):
    first = wu.record_skipped_week(2026, 4, 'first', NOW, tmp_path)
    wu.record_skipped_week(2026, 4, 'second', NOW + pd.Timedelta(days=2), tmp_path)
    assert json.loads(first.read_text(encoding='utf-8'))['reason'] == 'first'


def test_main_records_the_skip_before_it_fails():
    """The wiring: the refusal branch in main() must write the record, or
    determine_next_week() has nothing to count and the stall is back."""
    src = (ROOT / 'src' / 'sports' / 'nfl' / 'weekly_update.py').read_text(encoding='utf-8')
    branch = re.search(r'if decision\.started and not decision\.lock:(.*?)raise SystemExit', src, re.S)
    assert branch, 'the refusal branch in main() is not findable -- re-anchor this guard'
    assert 'record_skipped_week(' in branch.group(1), (
        'main() refuses an unlocked, fully kicked-off week without recording it as skipped')


# ---- the other readers of saved picks do not see a skip --------------------

def test_the_dashboard_does_not_load_a_skip_as_a_week(tmp_path, monkeypatch):
    from src.sports.nfl import generate_dashboard as gd
    picks(tmp_path, 1)
    wu.record_skipped_week(2026, 2, 'test', NOW, tmp_path / 'skipped')
    monkeypatch.setattr(gd, 'PRED_DIR', tmp_path)
    assert set(gd.load_all_predictions()) == {(2026, 1)}


def test_the_weekend_refresh_does_not_see_a_skip(tmp_path):
    from src.sports.nfl import weekend_refresh as wr
    results = tmp_path / 'results'
    results.mkdir()
    wu.record_skipped_week(2026, 2, 'test', NOW, tmp_path / 'skipped')
    assert wr.weeks_to_refresh(2026, tmp_path, results) == []


def test_the_weekly_grading_loop_does_not_recurse():
    """nfl-weekly-update.yml grades every predictions/nfl/*_week*.json. A recursive
    glob there would try to grade a skip record."""
    wf = (ROOT / '.github' / 'workflows' / 'nfl-weekly-update.yml').read_text(encoding='utf-8')
    assert 'for f in predictions/nfl/*_week*.json; do' in wf
    assert 'globstar' not in wf
