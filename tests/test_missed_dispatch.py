"""
Stage 42 item 4: a slot cron-job.org never started is seen.

src/core/missed_dispatch.py runs in every workflow cron-job.org covers. On
a run GitHub's own cron started, it asks the Actions API whether a
`workflow_dispatch` run of the same workflow started near the slot; when
none did, it opens or comments on an alert issue. The NBA's 16:00 job and
the NFL's Saturday 05:17 job, both made on 2026-10-09, never fired, and
nothing said so for four days.

What is held here:
  - the verdict: covered, missed or too early, at the edges of its windows;
  - only a run GitHub's cron started, on a covered line, is judged, and
    only a missed slot raises an alert, titled per workflow and slot time;
  - the check never fails its run, whatever goes wrong inside it;
  - DISPATCHED and NOT_DISPATCHED account for every cron line of every
    workflow, and every covered workflow runs the step with what it needs.

Run with: pytest tests/test_missed_dispatch.py -v
"""
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.core import missed_dispatch as md
from src.core.start_delay import crons

WORKFLOWS = Path(__file__).parent.parent / '.github' / 'workflows'
SLOT = datetime(2026, 10, 13, 16, 0, tzinfo=UTC)
M = timedelta(minutes=1)


# --- the verdict -------------------------------------------------------------

@pytest.mark.parametrize('dispatch', [SLOT + 20 * timedelta(seconds=1), SLOT - M, SLOT + 15 * M])
def test_a_dispatch_near_the_slot_covers_it(dispatch):
    assert md.judge(SLOT, SLOT + 5 * 60 * M, [dispatch]) == 'covered'


@pytest.mark.parametrize('dispatch', [SLOT + 16 * M, SLOT - 3 * M, SLOT + 5 * 60 * M])
def test_a_dispatch_far_from_the_slot_does_not(dispatch):
    assert md.judge(SLOT, SLOT + 6 * 60 * M, [dispatch]) == 'missed'


def test_no_dispatch_and_a_late_github_run_is_a_miss():
    assert md.judge(SLOT, SLOT + 16 * M, []) == 'missed'


def test_github_on_time_is_not_judged():
    """A dispatch could still be on its way."""
    assert md.judge(SLOT, SLOT + 14 * M, []) == 'too early'


# --- what is judged, and what raises an alert -------------------------------

class Spy:
    def __init__(self, dispatches=(), fail=None):
        self.dispatches, self.fail = list(dispatches), fail
        self.fetched, self.alerts = [], []

    def fetch(self, workflow, slot):
        self.fetched.append((workflow, slot))
        if self.fail:
            raise self.fail
        return self.dispatches

    def alert(self, title, body):
        self.alerts.append((title, body))


def run(spy, event='schedule', cron='0 16 * * *', now=SLOT + timedelta(hours=4, minutes=52, seconds=50),
        workflow='nba-daily.yml'):
    return md.check(workflow, 'NBA daily run', event, cron, now, fetch=spy.fetch, alert=spy.alert)


def test_the_nba_16_00_run_of_2026_10_13_raises_the_alert():
    """The real case: GitHub's copy at 20:52:50 UTC, and no dispatch."""
    spy = Spy()
    line = run(spy)
    assert spy.fetched == [('nba-daily.yml', SLOT)]
    assert [t for t, _ in spy.alerts] == ['NBA daily run: cron-job.org did not start the 16:00 UTC run']
    body = spy.alerts[0][1]
    assert 'nba-daily.yml' in body and '0 16 * * *' in body and '4h 52m late' in body
    assert 'alert raised' in line


def test_a_covered_slot_raises_nothing():
    spy = Spy([SLOT + 30 * timedelta(seconds=1)])
    assert "GitHub's late copy" in run(spy)
    assert spy.alerts == []


@pytest.mark.parametrize('event', ['workflow_dispatch', None, 'push'])
def test_a_run_github_cron_did_not_start_is_not_judged(event):
    spy = Spy()
    assert 'not judged' in run(spy, event=event)
    assert spy.fetched == [] and spy.alerts == []


def test_a_cron_line_cron_job_org_does_not_cover_is_not_judged():
    spy = Spy()
    assert 'not judged' in run(spy, cron='15 7 * * *', workflow='nightly-random-order.yml')
    assert spy.fetched == [] and spy.alerts == []


def test_an_api_that_cannot_be_read_raises_nothing():
    spy = Spy(fail=RuntimeError('HTTP 403'))
    assert 'could not read the Actions API' in run(spy)
    assert spy.alerts == []


def test_main_never_fails_its_run(tmp_path, monkeypatch):
    wf = tmp_path / 'nba-daily.yml'
    wf.write_text("name: NBA daily run\non:\n  schedule:\n    - cron: '0 16 * * *'\n", encoding='utf-8')
    summary = tmp_path / 'summary.md'
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'schedule')
    monkeypatch.setenv('CRON_SCHEDULE', '0 16 * * *')
    monkeypatch.setenv('GITHUB_STEP_SUMMARY', str(summary))

    def broken_alert(title, body):
        raise RuntimeError('gh issue create failed')
    rc = md.main([str(wf)], now=SLOT + timedelta(hours=5), fetch=lambda w, s: [], alert=broken_alert)
    assert rc == 0
    assert 'failed (gh issue create failed)' in summary.read_text(encoding='utf-8')


# --- the table, against the workflows ---------------------------------------

def scheduled():
    return {f.name: crons(f.read_text(encoding='utf-8')) for f in sorted(WORKFLOWS.glob('*.yml'))
            if crons(f.read_text(encoding='utf-8'))}


def test_every_cron_line_is_either_covered_or_declared_left_to_github():
    have = scheduled()
    assert not set(md.DISPATCHED) & set(md.NOT_DISPATCHED)
    assert set(md.DISPATCHED) | set(md.NOT_DISPATCHED) == set(have)
    for name, lines in md.DISPATCHED.items():
        assert sorted(lines) == sorted(have[name]), name


def permissions(text):
    """The workflow-level permissions block, comments dropped."""
    lines = text.splitlines()
    start = lines.index('permissions:')
    block = []
    for line in lines[start + 1:]:
        if not line.startswith('  '):
            break
        if not line.strip().startswith('#'):
            block.append(line.strip())
    return block


def step_holding(text, run_line):
    """The lines of the one step whose `run:` is `run_line`, from its
    `- name:` to the run line, comments dropped."""
    lines = text.splitlines()
    at = [i for i, line in enumerate(lines) if line.strip() == f'run: {run_line}']
    assert len(at) == 1, (run_line, len(at))
    i = at[0]
    while not lines[i].lstrip().startswith('- name:'):
        i -= 1
    return [line.strip() for line in lines[i:at[0] + 1] if not line.strip().startswith('#')]


@pytest.mark.parametrize('name', sorted(md.DISPATCHED))
def test_every_covered_workflow_runs_the_check(name):
    text = (WORKFLOWS / name).read_text(encoding='utf-8')
    perms = permissions(text)
    assert 'actions: read' in perms and 'issues: write' in perms, (name, perms)
    step = step_holding(text, f'python -m src.core.missed_dispatch .github/workflows/{name}')
    assert "if: github.event_name == 'schedule'" in step, name
    assert 'CRON_SCHEDULE: ${{ github.event.schedule }}' in step, name
    assert 'GH_TOKEN: ${{ github.token }}' in step, name
