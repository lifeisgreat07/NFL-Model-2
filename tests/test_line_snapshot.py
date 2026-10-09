"""log_line_snapshot must skip a game with no spread, not write it as null.

WHY THIS EXISTS

2026 week 3's snapshot was 16 rows of null spreads (PR #75, closed rather
than merged). The queued item recorded that as noise. Reproducing it on
2026-09-21 found the half nobody had written down, and it is the reason
these tests exist rather than a lint rule:

  `already_logged_today` is built from whatever is on disk carrying today's
  date. A null row written this morning therefore makes that game a
  duplicate for the rest of the day, so the afternoon run -- the one where
  the line finally exists -- skips it. The archive ends the day holding a
  null and no spread, and the line for that day is gone for good, because
  weekly_update never rewrites a past capture.

  The old code then printed "already captured today -- skipped duplicate",
  which names a cause that is not the cause. A reader chasing that message
  looks for a duplicate that was never there.

This matters more than a normal data-quality nit because the scheduled
weekly workflow writes this archive straight to `main`. There is no PR and
no reviewer between an early run and a week of dead rows -- #75 was caught
only because a human happened to read the diff.

WHAT THESE CHECK, AND WHAT THEY DO NOT

They check behaviour, by calling the real function against a temporary
archive directory: what lands on disk, and what is printed. They do not
check that nflreadpy ever returns a NaN spread -- that is upstream, and the
week-3 file is the evidence it does.
"""
import json

import pandas as pd
import pytest

from src.sports.nfl import weekly_update as wu


@pytest.fixture
def archive(tmp_path, monkeypatch):
    """Point the module's archive directory at a temporary one.

    monkeypatch, so a failing test cannot leave the real data/nfl/line_history
    redirected for whatever runs next in the same session.
    """
    monkeypatch.setattr(wu, 'LINE_HISTORY_DIR', tmp_path)
    return tmp_path


def _games(*rows):
    return pd.DataFrame([
        {'home_team': h, 'away_team': a, 'spread_line': s} for h, a, s in rows
    ])


def _rows(archive, season=2026, week=99):
    path = archive / f'{season}_week{week}_lines.json'
    return json.loads(path.read_text()) if path.exists() else []


NO_LINES = (('KC', 'BAL', float('nan')), ('SF', 'SEA', float('nan')))
REAL_LINES = (('KC', 'BAL', -3.5), ('SF', 'SEA', 2.0))


def test_the_harness_records_a_normal_capture(archive):
    """The vacuity companion, first rather than last.

    Every assertion below is of the form "nothing was written" or "this was
    written instead", and both are satisfied by a harness that silently
    writes nothing at all -- which would fail OPEN, looking like a pass. So
    prove the ordinary path reaches disk before trusting any of them.
    """
    wu.log_line_snapshot(2026, 99, _games(*REAL_LINES))
    rows = _rows(archive)
    assert len(rows) == 2, (
        f'the ordinary capture path wrote {rows}, so these tests are running '
        'against a harness that does not write and prove nothing')
    assert {r['spread_line'] for r in rows} == {-3.5, 2.0}


def test_a_game_with_no_spread_yet_is_not_written(archive):
    wu.log_line_snapshot(2026, 99, _games(*NO_LINES))
    rows = _rows(archive)
    assert rows == [], (
        f'a game with no spread posted was written anyway: {rows}. A null '
        'row carries no line to compare and blocks the real one from being '
        'captured later the same day.')


def test_a_missing_line_does_not_block_the_same_day_capture(archive):
    """The load-bearing one. This is the defect, not the null rows.

    Morning: no lines posted. Afternoon, same day: lines posted. The real
    spreads must reach the archive. Under the old code they did not, because
    the morning's nulls made both games duplicates for the day.
    """
    wu.log_line_snapshot(2026, 99, _games(*NO_LINES))
    wu.log_line_snapshot(2026, 99, _games(*REAL_LINES))

    rows = _rows(archive)
    captured = [r for r in rows if r['spread_line'] is not None]
    assert len(captured) == 2, (
        f'the afternoon run captured {len(captured)} of 2 real spreads: '
        f'{rows}. A morning run that found no lines has blocked the day, and '
        'weekly_update never rewrites a past capture, so that day is lost.')
    assert {r['spread_line'] for r in captured} == {-3.5, 2.0}


def test_a_real_spread_is_still_deduplicated_within_the_day(archive):
    """Skipping the empty case must not cost the dedupe it sits next to."""
    wu.log_line_snapshot(2026, 99, _games(*REAL_LINES))
    wu.log_line_snapshot(2026, 99, _games(*REAL_LINES))
    rows = _rows(archive)
    assert len(rows) == 2, (
        f'running twice in one day wrote {len(rows)} rows: {rows}. The '
        'same-day dedupe is gone, and the archive now double-counts every '
        'day the workflow is dispatched more than once.')


def test_each_outcome_says_which_one_it_was(archive, capsys):
    """Three outcomes, three messages, and the middle one is the point.

    "Nothing was written" has two causes -- already captured, or no line
    exists yet -- and they want opposite responses: the first is fine, the
    second means come back later. Collapsing them is how the old code
    reported a duplicate that did not exist.
    """
    wu.log_line_snapshot(2026, 99, _games(*NO_LINES))
    no_line_msg = capsys.readouterr().out
    assert 'no spread posted yet' in no_line_msg, no_line_msg
    assert 'duplicate' not in no_line_msg, (
        f'a run that found no lines reported a duplicate: {no_line_msg!r}. '
        'That names a cause that is not the cause.')

    wu.log_line_snapshot(2026, 99, _games(*REAL_LINES))
    logged_msg = capsys.readouterr().out
    assert 'Logged 2 line snapshot' in logged_msg, logged_msg

    wu.log_line_snapshot(2026, 99, _games(*REAL_LINES))
    dup_msg = capsys.readouterr().out
    assert 'duplicate' in dup_msg, dup_msg


def test_a_partly_priced_week_logs_what_it_has_and_says_what_it_skipped(archive):
    """The realistic case: some games priced, some not."""
    wu.log_line_snapshot(2026, 99, _games(
        ('KC', 'BAL', -3.5), ('SF', 'SEA', float('nan'))))
    rows = _rows(archive)
    assert len(rows) == 1 and rows[0]['home'] == 'KC', (
        f'a partly priced week wrote {rows}; it should carry the priced game '
        'and leave the unpriced one out entirely')


# NOT GUARDED, on purpose, and recorded so the next reader does not add it:
# the float() around the stored spread. A test asserting the value is a
# plain float cannot fail, because numpy.float64 subclasses Python float --
# isinstance passes either way, and json.dump serialises both. The call is
# an explicit no-op kept for intent, not a fix, and a guard over it would be
# the "comment claims more than the code delivers" shape this repository has
# shipped five times.


# --- Stage 37 item 4: a row per move, with the moment it was read ----------

from datetime import UTC, datetime


def _at(s):
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


def test_an_unmoved_line_is_not_written_again_the_next_day(archive):
    """One row per day per game wrote the same spread every day it did not
    move; the archive is for movement."""
    wu.log_line_snapshot(2026, 99, _games(*REAL_LINES), now=_at('2026-10-06 11:00'))
    wu.log_line_snapshot(2026, 99, _games(*REAL_LINES), now=_at('2026-10-08 11:00'))
    assert len(_rows(archive)) == 2


def test_a_move_within_the_same_day_is_written(archive):
    """The per-day rule missed this: a line that moved between two runs on
    one day kept the morning's value for the day."""
    wu.log_line_snapshot(2026, 99, _games(('KC', 'BAL', -3.5)), now=_at('2026-10-08 05:00'))
    wu.log_line_snapshot(2026, 99, _games(('KC', 'BAL', -4.0)), now=_at('2026-10-08 11:00'))
    rows = _rows(archive)
    assert [r['spread_line'] for r in rows] == [-3.5, -4.0]
    assert [r['captured_utc'] for r in rows] == ['2026-10-08T05:00:00Z', '2026-10-08T11:00:00Z']


def test_a_line_that_moves_back_is_a_move(archive):
    for when, spread in (('2026-10-06 11:00', -3.0), ('2026-10-07 11:00', -3.5), ('2026-10-08 11:00', -3.0)):
        wu.log_line_snapshot(2026, 99, _games(('KC', 'BAL', spread)), now=_at(when))
    assert [r['spread_line'] for r in _rows(archive)] == [-3.0, -3.5, -3.0]


def test_rows_from_before_captured_utc_still_count_as_the_last_line(archive):
    """The 2026 files written before this change carry captured_date only;
    their last spread still decides whether a new row is a move."""
    (archive / '2026_week99_lines.json').write_text(json.dumps(
        [{'captured_date': '2026-10-01', 'home': 'KC', 'away': 'BAL', 'spread_line': -3.5}]))
    wu.log_line_snapshot(2026, 99, _games(('KC', 'BAL', -3.5)), now=_at('2026-10-06 11:00'))
    assert len(_rows(archive)) == 1
    wu.log_line_snapshot(2026, 99, _games(('KC', 'BAL', -2.5)), now=_at('2026-10-06 12:00'))
    rows = _rows(archive)
    assert len(rows) == 2 and rows[-1]['captured_utc'] == '2026-10-06T12:00:00Z'
    assert rows[-1]['captured_date'] == '2026-10-06'


def test_a_duplicated_game_in_one_read_is_written_once(archive):
    """A schedule that lists one game twice (a data error upstream) must not
    record a move from a line to itself."""
    wu.log_line_snapshot(2026, 99, _games(('KC', 'BAL', -3.5), ('KC', 'BAL', -3.5)), now=_at('2026-10-06 11:00'))
    assert len(_rows(archive)) == 1
