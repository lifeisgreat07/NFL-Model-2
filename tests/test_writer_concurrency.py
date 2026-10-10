"""Every workflow that pushes to main runs one at a time (Stage 68 item 10).

The weekend refresh was the one writer with no concurrency group: its two
copies of a slot (cron-job.org's and GitHub's late one) could overlap the
next slot's run, and a second push to main is refused. A group with
cancel-in-progress false queues them; cancelling would drop a refresh.

Run with: pytest tests/test_writer_concurrency.py -v
"""
import re
from pathlib import Path

import pytest

WF = Path(__file__).resolve().parents[1] / '.github' / 'workflows'
WRITERS = sorted(p for p in WF.glob('*.yml')
                 if re.search(r'git push|git-auto-commit-action', p.read_text(encoding='utf-8')))


def test_the_writers_are_found():
    names = {p.name for p in WRITERS}
    assert {'nfl-weekend-refresh.yml', 'nfl-weekly-update.yml', 'nhl-daily.yml', 'nba-daily.yml'} <= names


@pytest.mark.parametrize('path', WRITERS, ids=lambda p: p.name)
def test_each_writer_queues_rather_than_overlaps(path):
    text = path.read_text(encoding='utf-8').replace('\r\n', '\n')
    m = re.search(r'^concurrency:\n  group: .+\n  cancel-in-progress: (\w+)$', text, re.M)
    assert m, f'{path.name} pushes to main with no workflow-level concurrency group'
    assert m.group(1) == 'false', f'{path.name} would cancel a run that may already have written'
