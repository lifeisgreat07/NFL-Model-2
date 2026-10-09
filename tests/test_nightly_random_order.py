"""The nightly shuffled suite (Stage 48 item 17): what its header promises,
held to the workflow.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = (ROOT / '.github' / 'workflows' / 'nightly-random-order.yml').read_text(
    encoding='utf-8').replace('\r\n', '\n')
RUN = WF.split('- name: Run the suite in tonight\'s order', 1)[1].split('- name:', 1)[0]


def test_it_runs_every_night_and_by_hand():
    assert re.search(r"^  schedule:\n    - cron: '15 7 \* \* \*'\n", WF, re.M)
    assert 'workflow_dispatch:' in WF


def test_it_shuffles_across_every_file_with_the_date_as_the_seed():
    """Global bucket: the order dependence worth finding is usually between
    files (a module-level cache one file fills and another reads). The date
    seed makes any night replayable."""
    assert 'seed="$(date -u +%Y%m%d)"' in RUN
    assert '--random-order-bucket=global' in RUN
    assert '--random-order-seed="$seed"' in RUN
    assert 'python -m pytest' in RUN


def test_the_plugin_is_pinned_and_installed_in_this_job_only():
    """Nowhere else may shuffle: every other run of the suite stays in file
    order, so a count quoted from one run is the count of the next."""
    assert re.search(r'pip install pytest-random-order==\d+\.\d+\.\d+\n', WF)
    assert 'random-order' not in (ROOT / 'requirements-dev.txt').read_text(encoding='utf-8')
    assert 'random-order' not in (ROOT / 'requirements.txt').read_text(encoding='utf-8')


def test_a_failure_raises_the_alert_with_the_replay_command():
    alert = WF.split('- name: Raise an alert', 1)[1]
    assert 'if: failure()' in alert
    assert 'python -m src.core.alerts --title "Nightly shuffled suite failing"' in alert
    assert 'Replay: python -m pytest -q -p no:cacheprovider --random-order-bucket=global --random-order-seed=%s' in alert


def test_it_cannot_write_to_the_repository():
    perms = WF.split('\npermissions:\n', 1)[1].split('\n\n', 1)[0]
    assert 'contents: read' in perms and 'contents: write' not in perms
