"""
src/schema_check.py: today's nflverse columns against the committed snapshot.

Run with: pytest tests/test_schema_check.py -v
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / 'src'))

import schema_check as sc  # noqa: E402
from data_loader import REQUIRED_PBP_COLS, REQUIRED_SCHEDULE_COLS  # noqa: E402

BASE = {'pbp': sorted(REQUIRED_PBP_COLS + ['air_yards', 'wind']),
        'schedule': sorted(REQUIRED_SCHEDULE_COLS + ['roof'])}


def current(pbp_drop=(), pbp_add=(), sched_drop=()):
    return {'pbp': sorted(set(BASE['pbp']) - set(pbp_drop) | set(pbp_add)),
            'schedule': sorted(set(BASE['schedule']) - set(sched_drop))}


def test_unchanged_columns_have_no_findings():
    assert sc.compare(BASE, current()).lines() == []


def test_losing_a_column_the_model_reads_is_an_error():
    report = sc.compare(BASE, current(pbp_drop=['qb_epa']))
    assert any("['qb_epa']" in e for e in report.errors)
    # It is reported once, as the error, not again as a plain loss.
    assert not any('qb_epa' in w for w in report.warnings)


def test_losing_a_required_schedule_column_is_an_error():
    report = sc.compare(BASE, current(sched_drop=['spread_line']))
    assert any('spread_line' in e for e in report.errors)


def test_other_changes_are_warnings():
    report = sc.compare(BASE, current(pbp_drop=['wind'], pbp_add=['new_col']))
    assert report.errors == []
    assert any("gained columns: ['new_col']" in w for w in report.warnings)
    assert any("does not read: ['wind']" in w for w in report.warnings)


def test_an_empty_snapshot_is_said_out_loud():
    """No snapshot to compare with must not read as 'no changes'."""
    report = sc.compare({}, current())
    assert len(report.warnings) == 2


def test_the_snapshot_round_trips(tmp_path):
    path = tmp_path / 'schema.json'
    sc.write_snapshot(current(), path=path, sources={'pbp_seasons': [2026]})
    assert sc.compare(sc.load_snapshot(path), current()).lines() == []


def test_the_committed_snapshot_exists_and_holds_every_required_column():
    """The canary compares against this file every night. Missing, it would
    fail every night; missing a required column, it would describe a data
    source the model cannot run on."""
    snap = json.loads(sc.SNAPSHOT.read_text(encoding='utf-8'))
    assert set(REQUIRED_PBP_COLS) <= set(snap['pbp'])
    assert set(REQUIRED_SCHEDULE_COLS) <= set(snap['schedule'])
    assert snap['sources']['pbp_seasons'], 'the snapshot does not say which seasons it read'
