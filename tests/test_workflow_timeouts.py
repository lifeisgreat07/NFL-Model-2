"""Every job in every workflow has a timeout (Stage 24 item 7).

The 2026-09-28 audit: several workflows had no `timeout-minutes`, so a hung
step held a runner for GitHub's six-hour default. For the Weekly update that
also means a lock run stuck for hours instead of failing, opening its issue,
and leaving time to dispatch it again before kickoff. Enumerated from every
workflow file, not a list, so a new workflow is held too.

No PyYAML here, so jobs are read the way the other workflow tests read them:
the block after `jobs:`, split at two-space-indented keys.
"""
import re
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[1] / '.github' / 'workflows'


def jobs():
    """(workflow file, job name, job body) for every job in every workflow."""
    out = []
    for p in sorted(WORKFLOWS.glob('*.yml')):
        t = p.read_text(encoding='utf-8').replace('\r\n', '\n')
        block = t.split('\njobs:\n', 1)[1]
        parts = re.split(r'(?m)^  ([A-Za-z0-9_-]+):\s*$', block)
        out += [(p.name, name, body) for name, body in zip(parts[1::2], parts[2::2])]
    return out


def timeout(body):
    m = re.search(r'(?m)^    timeout-minutes:\s*(\d+)\s*$', body)
    return int(m.group(1)) if m else None


def test_the_scan_finds_the_jobs_it_must():
    """A scan that finds nothing passes every check below, so name some."""
    found = {(f, j) for f, j, _ in jobs()}
    for must in [('weekly-update.yml', 'weekly-update'), ('deploy-pages.yml', 'build'),
                 ('deploy-pages.yml', 'deploy'), ('booth-regression.yml', 'record'),
                 ('run-tests.yml', 'test')]:
        assert must in found, f'{must} not found by the job scan -- re-anchor it'


def test_every_job_has_a_timeout():
    missing = [f'{f}:{j}' for f, j, body in jobs() if not timeout(body)]
    assert not missing, f'jobs with no timeout-minutes: {missing}'


def test_the_weekly_lock_run_fails_well_inside_a_thursday():
    """The Thursday run starts at 11:00 UTC and locks the Thursday night game
    (Thanksgiving's early games are locked on Tuesday). A timeout is only
    useful if a failed run leaves time to dispatch it again before kickoff,
    so it is held to an hour at most."""
    body = next(b for f, j, b in jobs() if (f, j) == ('weekly-update.yml', 'weekly-update'))
    assert timeout(body) and timeout(body) <= 60, timeout(body)
