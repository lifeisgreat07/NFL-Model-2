"""Stage 93 item 13 (audit 7, R9): a hung step fails, so its alert fires.

Every alert step is `if: failure()`. A job that runs into its own
timeout-minutes is CANCELLED, not failed, and failure() is false for it, so a
feed that answers slowly enough to hang the daily run past 30 minutes raised
no alert at all. Audit 7 proposed `failure() || cancelled()`; that would also
alert on every run cancelled because a newer one replaced it. Instead each
python or pip step of an alerting scheduled job carries its own
timeout-minutes, five under the job's (at least 3): a step that hangs is
killed and FAILS, and the job's failure() steps still have the time left to
keep the picks and raise the alert.

Run with: pytest tests/test_step_timeouts.py -v
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / '.github' / 'workflows'
GUARDED = re.compile(r'if: \$?\{?\{? ?(failure|always|cancelled)\(\)')


def jobs(text):
    body = text.replace('\r\n', '\n').split('\njobs:\n', 1)[1]
    parts = re.split(r'(?m)^  ([A-Za-z0-9_-]+):\n', body)
    return [(parts[i], parts[i + 1]) for i in range(1, len(parts), 2)]


def work_steps(job):
    """A job's run steps that call python or pip and are not themselves failure() steps."""
    out = []
    for step in job.split('\n      - ')[1:]:
        if GUARDED.search(step):
            continue
        run = step[step.find('run:'):] if 'run:' in step else ''
        if run and ('python' in run or 'pip ' in run):
            out.append(step)
    return out


def alerting_scheduled_jobs():
    for p in sorted(WORKFLOWS.glob('*.yml')):
        text = p.read_text(encoding='utf-8')
        if 'schedule:' not in text:
            continue
        for name, job in jobs(text):
            m = re.search(r'(?m)^    timeout-minutes: (\d+)', job)
            if m and any('failure()' in s and 'src.core.alerts' in s for s in job.split('\n      - ')):
                yield p.name, name, int(m.group(1)), job


def test_every_work_step_times_out_before_its_job():
    found = list(alerting_scheduled_jobs())
    assert len(found) >= 10, f'the scan found only {[(f, j) for f, j, _, _ in found]}'
    missing, late = [], []
    for wf, name, job_limit, job in found:
        for step in work_steps(job):
            label = f"{wf} {name}: {step.split(chr(10), 1)[0]}"
            m = re.search(r'(?m)^        timeout-minutes: (\d+)', step)
            if not m:
                missing.append(label)
            elif not 1 <= int(m.group(1)) <= max(3, job_limit - 5):
                late.append(f'{label} ({m.group(1)} of {job_limit})')
    assert not missing, 'steps that would hang into the job timeout, which no alert sees:\n' + '\n'.join(missing)
    assert not late, 'step timeouts that leave the alert steps no time:\n' + '\n'.join(late)


def test_the_daily_runs_are_among_them():
    names = {(wf, step.split('\n', 1)[0]) for wf, _, _, job in alerting_scheduled_jobs() for step in work_steps(job)}
    for wf, step in (('nhl-daily.yml', "name: Run the NHL's daily run"), ('nba-daily.yml', "name: Run the NBA's daily run"),
                     ('nfl-weekly-update.yml', "name: Generate/lock in this week's predictions")):
        assert (wf, step) in names


def test_a_step_without_its_timeout_is_found():
    job = ("    timeout-minutes: 30\n    steps:\n      - name: Run it\n        run: python -m src.x\n"
           "      - name: Alert\n        if: failure()\n        run: python -m src.core.alerts t b\n")
    assert [s.split('\n', 1)[0] for s in work_steps(job)] == ['name: Run it']
