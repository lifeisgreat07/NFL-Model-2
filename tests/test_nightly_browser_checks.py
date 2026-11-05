"""
Stage 81 item 6 (the 2026-11-02 review): the browser checks run every night on
main and raise an issue there, and a pull request that changes any sport's data
runs them.

Several checks are about a state the real page passes through and then leaves.
Run only on pull requests, one that had gone stale with the season showed up on
whichever unrelated pull request came next: the NBA tip self-test was red on
every pull request from 2026-10-28 to 11-02 (fixed in #546).

Run with: pytest tests/test_nightly_browser_checks.py -v
"""
import re
from pathlib import Path

WORKFLOW = (Path(__file__).resolve().parents[1] / '.github' / 'workflows' / 'browser-checks.yml').read_text(
    encoding='utf-8')


def trigger(name):
    m = re.search(rf'^  {name}:\n((?:    .+\n|      .+\n)+)', WORKFLOW, re.M)
    assert m, f'browser-checks.yml has no {name} trigger'
    return m.group(1)


def test_it_runs_every_night():
    assert re.search(r"^\s+- cron: '\d+ \d+ \* \* \*'", trigger('schedule'), re.M)


def test_the_nightly_run_raises_an_issue_and_a_pull_request_does_not():
    step = WORKFLOW[WORKFLOW.index('- name: Raise an alert'):]
    assert "if: failure() && github.event_name == 'schedule'" in step
    assert 'python -m src.core.alerts' in step


def test_a_pull_request_that_changes_any_sports_data_runs_it():
    paths = re.findall(r"- '([^']+)'", trigger('pull_request'))
    for folder in ('data', 'predictions', 'results'):
        assert f'{folder}/**' in paths, f'a pull request changing {folder}/ of the NBA or NHL skips the checks'


def test_the_job_has_room_for_a_slow_install():
    """`playwright install --with-deps` fetches system packages with apt. On 2026-11-05 the mirror was slow
    enough that the install step took up to 980 s beside about 11 minutes of checks, and a job cut off at
    20 minutes was cancelled on its last checks three times (#647, #648)."""
    m = re.search(r'^  browser:\n(?:    .+\n)*?    timeout-minutes: (\d+)$', WORKFLOW, re.M)
    assert m, 'the browser job states no timeout'
    assert int(m.group(1)) >= 30
