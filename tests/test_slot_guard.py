"""A scheduled slot of the Weekly update is served once (Stage 42 item 3).

cron-job.org dispatches the Weekly update on time; GitHub's cron sends a
late copy of the same slot hours later (decision record 0005). The copy
must change nothing. `src/sports/nfl/slot_guard.py` decides; these tests hold
the decision on the slots that matter, the marker's round trip, and the
workflow's wiring, including that a broken guard fails open (the week
still runs) rather than costing a lock.

Run with: pytest tests/test_slot_guard.py -v
"""
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.sports.nfl import slot_guard as sg
from src.sports.nfl import weekly_update as wu

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'nfl-weekly-update.yml'
RUNS = sg.WORKFLOW_SLOTS['weekly-update']


def utc(s):
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


def test_the_slots_are_the_weekly_runs():
    """The lock decides from SCHEDULED_RUNS_UTC, which test_pick_lock_time
    holds equal to the cron lines; the guard must count the same slots."""
    assert RUNS == wu.SCHEDULED_RUNS_UTC


@pytest.mark.parametrize('now, slot', [
    ('2026-10-08 11:00:20', '2026-10-08T11:00Z'),   # the dispatched Thursday run
    ('2026-10-08 19:39:00', '2026-10-08T11:00Z'),   # GitHub's late copy, 8h39m on
    ('2026-10-08 10:59:59', '2026-10-06T11:00Z'),   # before Thursday's slot: still Tuesday's
    ('2026-10-06 11:00:00', '2026-10-06T11:00Z'),   # exactly on the slot
    ('2026-10-12 23:00:00', '2026-10-08T11:00Z'),   # Monday belongs to last Thursday
    ('2027-01-05 11:01:00', '2027-01-05T11:00Z'),   # across the year
])
def test_a_run_belongs_to_the_latest_slot_at_or_before_it(now, slot):
    assert sg.slot_key(sg.current_slot(utc(now), RUNS)) == slot


def test_a_new_slot_runs():
    run, why = sg.decide(utc('2026-10-08 11:00'), '2026-10-06T11:00Z', force=False)
    assert run and 'not yet served' in why


def test_nothing_served_yet_runs():
    assert sg.decide(utc('2026-10-08 11:00'), None, force=False)[0]


def test_the_same_slot_again_is_skipped():
    run, why = sg.decide(utc('2026-10-08 11:00'), '2026-10-08T11:00Z', force=False)
    assert not run and 'already served' in why


def test_force_runs_a_served_slot():
    assert sg.decide(utc('2026-10-08 11:00'), '2026-10-08T11:00Z', force=True)[0]


def test_marking_a_slot_makes_its_late_copy_skip(tmp_path):
    """The round trip the workflow makes: the on-time run marks, the late
    copy reads the marker back and changes nothing."""
    slot = sg.current_slot(utc('2026-10-08 11:00:20'), RUNS)
    path = sg.mark('weekly-update', sg.slot_key(slot), '123', folder=tmp_path)
    assert json.loads(path.read_text(encoding='utf-8')) == {'slot': '2026-10-08T11:00Z', 'run_id': '123'}
    served = sg.served_slot('weekly-update', show=lambda p: path.read_text(encoding='utf-8'))
    late = sg.current_slot(utc('2026-10-08 19:39'), RUNS)
    assert sg.decide(late, served, force=False)[0] is False


def test_the_marker_is_read_from_origin_main(monkeypatch):
    """The late copy's own checkout can predate the on-time run's commit, so
    the marker is read from a fresh fetch of origin/main."""
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        class R:
            returncode = 0
            stdout = '{"slot": "2026-10-08T11:00Z"}'
        return R()
    monkeypatch.setattr(sg.subprocess, 'run', fake_run)
    assert sg.served_slot('weekly-update') == '2026-10-08T11:00Z'
    assert ['git', 'fetch', '--quiet', '--depth=1', 'origin', 'main'] == calls[0]
    assert calls[1] == ['git', 'show', 'origin/main:data/nfl/run_slots/weekly-update.json']


def test_check_writes_the_outputs_the_workflow_reads(tmp_path, monkeypatch):
    out = tmp_path / 'out'
    monkeypatch.setenv('GITHUB_OUTPUT', str(out))
    monkeypatch.setenv('GITHUB_STEP_SUMMARY', str(tmp_path / 'summary'))
    sg.main(['check', '--workflow', 'weekly-update'], now=utc('2026-10-08 19:39'),
            show=lambda p: '{"slot": "2026-10-08T11:00Z"}')
    assert out.read_text(encoding='utf-8').splitlines() == ['run=false', 'slot=2026-10-08T11:00Z']
    assert 'Skipped' in (tmp_path / 'summary').read_text(encoding='utf-8')


# ---------------------------------------------------------------- the workflow

def _job(text, name):
    m = re.search(rf'^  {re.escape(name)}:\n(.*?)(?=^  \S|\Z)', text, re.M | re.S)
    assert m, f'no job {name}'
    return m.group(1)


def test_the_weekly_job_waits_for_the_guard_and_skips_only_on_false():
    text = WORKFLOW.read_text(encoding='utf-8')
    job = _job(text, 'weekly-update')
    assert 'needs: slot-guard' in job
    gate = re.search(r'^    if: (.+)$', job, re.M).group(1)
    assert "needs.slot-guard.outputs.run != 'false'" in gate
    assert '!cancelled()' in gate, 'without it a failed guard skips the week, which costs a lock'


def test_the_runs_queue_rather_than_cancel_each_other():
    text = WORKFLOW.read_text(encoding='utf-8')
    m = re.search(r'^concurrency:\n  group: weekly-update\n  cancel-in-progress: (\w+)', text, re.M)
    assert m and m.group(1) == 'false'


def test_the_slot_is_marked_after_the_work_and_before_the_commit():
    job = _job(WORKFLOW.read_text(encoding='utf-8'), 'weekly-update')
    names = re.findall(r'^      - name: (.+)$', job, re.M)
    assert names.index('Mark the slot served') > names.index('Generate/lock in this week\'s predictions')
    assert names.index('Mark the slot served') < names.index('Commit and push changes')
    step = job[job.index('- name: Mark the slot served'):]
    step = step[:step.index('\n      - name:')]
    assert 'success()' in step, 'a failed run must leave its slot open for a retry by hand'
    assert '--slot ${{ needs.slot-guard.outputs.slot }}' in step


def test_the_marker_is_inside_what_the_commit_takes():
    job = _job(WORKFLOW.read_text(encoding='utf-8'), 'weekly-update')
    pattern = re.search(r"file_pattern: '([^']+)'", job).group(1).split()
    assert 'data/nfl/**' in pattern
    assert str(sg.SLOT_DIR.relative_to(ROOT)).replace('\\', '/').startswith('data/')


def test_the_guard_job_alerts_and_offers_force():
    text = WORKFLOW.read_text(encoding='utf-8')
    guard = _job(text, 'slot-guard')
    assert 'python -m src.sports.nfl.slot_guard check --workflow weekly-update' in guard
    assert "inputs.force && '--force'" in guard
    assert re.search(r'- name: Alert that the guard failed\n        if: failure\(\)[\s\S]*src\.core\.alerts --title "NFL: Weekly update slot guard failed"', guard)
    assert re.search(r'workflow_dispatch:\n    inputs:\n      force:', text)
