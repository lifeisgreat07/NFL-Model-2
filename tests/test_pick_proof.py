"""Day-sport picks show the commit that put them in the public history (Stage 68 item 20).

Run with: pytest tests/test_pick_proof.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.core.pick_proof import proof

ROOT = Path(__file__).resolve().parents[1]
A, B = 'a' * 40, 'b' * 40
LOG = (f'@{A} 2026-10-06T18:08:30-04:00\n\nA\tpredictions/nhl/2026/1.json\nA\tpredictions/nhl/2026/2.json\n'
       f'@{B} 2026-10-07T21:02:55Z\n\nM\tpredictions/nhl/2026/1.json\nA\tpredictions/nhl/2026/3.json\n')


def fake(shallow='false', log=LOG):
    def git(args, cwd):
        if args[0] == 'rev-parse':
            return shallow + '\n'
        return log
    return git


def test_each_file_gets_the_commit_that_added_it_and_later_changes_are_counted(tmp_path):
    folder = tmp_path / 'predictions' / 'nhl' / '2026'
    folder.mkdir(parents=True)
    out = proof(folder, tmp_path, fake())
    assert out['1'] == {'sha': A, 'committed': '2026-10-06T22:08:30Z', 'changes': 1}
    assert out['2']['changes'] == 0 and out['3'] == {'sha': B, 'committed': '2026-10-07T21:02:55Z', 'changes': 0}


def test_a_shallow_clone_or_a_git_failure_gives_nothing(tmp_path):
    assert proof(tmp_path, tmp_path, fake(shallow='true')) == {}

    def broken(args, cwd):
        raise subprocess.CalledProcessError(128, 'git')
    assert proof(tmp_path, tmp_path, broken) == {}


@pytest.mark.parametrize('sport', ('nhl', 'nba'))
def test_every_committed_pick_entered_history_before_its_start_and_never_changed(sport):
    """Stage 96 item 52, the parity table's lock-proof row: the NFL's weeks
    are held by tests/test_lock_proof.py; this holds every NHL and NBA pick
    file in the repository's own history. Each was added by a commit made
    before the start its own file records (not the schedule's, which a
    postponed game leaves), and no later commit touched it. Skipped where
    there is no history to read (a shallow clone, no git)."""
    folder = ROOT / 'predictions' / sport / '2026'
    if shutil.which('git') is None or proof(folder) == {}:
        pytest.skip('no git history here')
    out = proof(folder)
    files = sorted(folder.glob('*.json'))
    assert files and {p.stem for p in files} <= set(out), 'a committed pick git cannot place'
    for p in files:
        start = json.loads(p.read_text(encoding='utf-8'))['start_utc']
        assert out[p.stem]['committed'] < start, f'{sport} {p.stem} entered history at or after its start'
        assert out[p.stem]['changes'] == 0, f'{sport} {p.stem} was changed after it was saved'


@pytest.mark.parametrize('sport', ('nhl', 'nba'))
def test_the_page_and_the_grades_carry_it(sport):
    site = (ROOT / 'src' / 'sports' / sport / 'site.py').read_text(encoding='utf-8')
    assert "'proof': pick_proof.proof(folder) if folder.exists() else {}," in site
    js = (ROOT / 'src' / 'sports' / sport / 'pages' / f'{sport}.js').read_text(encoding='utf-8')
    assert re.search(r'\$\{proofLine\(g, p, (DATA|BD)\.proof\)\}', js)
    assert "before ? 'before the start' : '<b>after the start</b>'" in js
    assert "if(!pr || !/^[0-9a-f]{40}$/.test(pr.sha)) return '';" in js
    # The grades come from the day sports' shared grade (Stage 87 item 2).
    daily = (ROOT / 'src' / 'sports' / sport / 'daily.py').read_text(encoding='utf-8')
    assert 'from src.core.day_picks import grade as grade' in daily or 'day_picks.grade(' in daily
    shared = (ROOT / 'src' / 'core' / 'day_picks.py').read_text(encoding='utf-8')
    assert "'saved_utc': pick.get('saved_utc')})" in shared
