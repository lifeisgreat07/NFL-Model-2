"""Every scheduled run says how late it started (Stage 42 item 1).

`src/core/start_delay.py` reads a workflow's own cron lines, finds the slot
the run serves and writes the delay to the run's summary, with a warning
annotation at seven hours. This file holds the cron reading against fixed
clocks, the threshold against the Weekly update's lock slack, and that every
workflow with a `schedule:` runs it, on itself, before its real work.

Run with: pytest tests/test_start_delay.py -v
"""
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.core import start_delay as sd
from src.sports.nfl.weekly_update import LOCK_SLACK

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / '.github' / 'workflows'
REFRESH = (WORKFLOWS / 'nfl-weekend-refresh.yml').read_text(encoding='utf-8')


def at(s):
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


def test_the_workflows_own_cron_lines_are_read():
    assert sd.crons(REFRESH) == ['17 5 * * 5', '17 5 * * 6', '47 21 * * 0', '47 1 * * 1', '37 5 * * 1']


def test_a_run_dispatched_on_time_is_minutes_late():
    # Friday 2026-10-09, cron-job.org's dispatch at 05:17:06.
    line, warn = sd.report(REFRESH, at('2026-10-09T05:17:06'), 'workflow_dispatch')
    assert line == "Start delay: 0h 00m after the Fri 05:17 UTC slot (cron '17 5 * * 5'), started by workflow_dispatch."
    assert not warn


def test_the_latest_slot_of_several_is_the_one_served():
    # Monday 02:30: Monday's 01:47 slot, not Sunday's 21:47.
    line, _ = sd.report(REFRESH, at('2026-10-12T02:30:00'), 'schedule')
    assert "0h 43m after the Mon 01:47 UTC slot (cron '47 1 * * 1')" in line


def test_seven_hours_warns_and_a_minute_less_does_not():
    assert sd.report(REFRESH, at('2026-10-09T12:17:00'), 'schedule')[1]
    assert not sd.report(REFRESH, at('2026-10-09T12:16:00'), 'schedule')[1]


def test_a_hand_run_long_after_a_slot_is_not_called_late():
    line, warn = sd.report(REFRESH, at('2026-10-08T12:20:00'), 'workflow_dispatch')
    assert line.startswith('Start delay: none; started by workflow_dispatch') and not warn


def test_a_cron_run_is_always_measured_however_late():
    line, warn = sd.report(REFRESH, at('2026-10-09T18:00:00'), 'schedule')
    assert line.startswith('Start delay: 12h 43m') and warn


def test_a_dispatch_within_the_window_is_measured():
    assert sd.served_delay(sd.crons(REFRESH), at('2026-10-09T17:17:00'), 'workflow_dispatch') == timedelta(hours=12)
    assert sd.served_delay(sd.crons(REFRESH), at('2026-10-09T17:18:00'), 'workflow_dispatch') is None


def test_the_warning_comes_before_the_lock_slack():
    """At eight hours a Thursday run no longer locks before kickoff; the
    warning must come first."""
    assert timedelta(hours=sd.WARN_HOURS) < LOCK_SLACK


@pytest.mark.parametrize('expr, when, fires', [
    ('0 11 * * 2', '2026-10-13T11:00', True),     # Tuesday
    ('0 11 * * 2', '2026-10-14T11:00', False),
    ('0 14 * * *', '2026-10-14T14:00', True),
    ('*/15 * * * *', '2026-10-14T14:45', True),
    ('*/15 * * * *', '2026-10-14T14:50', False),
    ('0 6 1,15 * *', '2026-10-15T06:00', True),
    ('0 6 * * 0', '2026-10-11T06:00', True),      # Sunday as 0
    ('0 6 * * 7', '2026-10-11T06:00', True),      # and as 7
    ('0 6 1 * 1', '2026-10-12T06:00', True),      # day of month OR day of week
    ('30 9-17 * * 1-5', '2026-10-16T17:30', True),
    ('30 9-17 * * 1-5', '2026-10-17T17:30', False),  # Saturday
])
def test_cron_fields_read_as_github_reads_them(expr, when, fires):
    assert sd.Cron(expr).matches(at(when)) is fires


def test_a_bad_cron_line_is_refused_not_guessed():
    with pytest.raises(ValueError):
        sd.Cron('0 25 * * *')
    with pytest.raises(ValueError):
        sd.Cron('0 6 * *')


def test_the_summary_and_the_annotation_are_written(tmp_path, monkeypatch, capsys):
    wf = tmp_path / 'wf.yml'
    wf.write_text(REFRESH, encoding='utf-8')
    summary = tmp_path / 'summary.md'
    monkeypatch.setenv('GITHUB_STEP_SUMMARY', str(summary))
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'schedule')
    assert sd.main([str(wf)], now=at('2026-10-09T13:00:00')) == 0
    out = capsys.readouterr().out
    assert '::warning title=Late start::Start delay: 7h 43m' in out
    assert summary.read_text(encoding='utf-8').startswith('Start delay: 7h 43m')
    assert '**Late: 7 hours or more.**' in summary.read_text(encoding='utf-8')


SCHEDULED = sorted(p for p in WORKFLOWS.glob('*.yml') if re.search(r'^\s*schedule:', p.read_text(encoding='utf-8'), re.M))


def test_there_are_scheduled_workflows_to_check():
    assert len(SCHEDULED) >= 8


@pytest.mark.parametrize('path', SCHEDULED, ids=lambda p: p.name)
def test_every_scheduled_workflow_records_its_own_start_delay_first(path):
    text = path.read_text(encoding='utf-8')
    runs = re.findall(r'^\s*run:\s*(.+)$', text, re.M)
    assert runs, path.name
    want = f'python -m src.core.start_delay .github/workflows/{path.name}'
    assert want in runs, f'{path.name} does not record its start delay'
    first_job = text[text.index('jobs:'):]
    steps = re.findall(r'^\s*- (?:name|uses):\s*(.+)$', first_job, re.M)
    setup = next(i for i, s in enumerate(steps) if s.startswith('actions/setup-python@')
                 or s == 'Set up Python')
    assert steps[setup + 1] == 'Record the start delay', (
        f'{path.name}: the delay is recorded straight after Python is set up, before the work')
