"""Stage 91 item 1 (audit 7, R1): a writer never pushes a pull that did not apply.

`git pull --rebase --autostash` exits 0 when this run's uncommitted file
conflicts with a change on main, leaving the stash and conflict markers; the
commit step then pushed the markers to main. These tests build that state in
a real throwaway repository (an origin, a second clone that moves main, and
the runner's clone) and check `src.core.pull_check` refuses it, and that
every writer runs the check straight after its pull.

Run with: pytest tests/test_pull_check.py -v
"""
import re
import subprocess
from pathlib import Path

import pytest

from src.core import pull_check

ROOT = Path(__file__).resolve().parents[1]
ID = ['-c', 'user.name=t', '-c', 'user.email=t@example.com']
PULL = ['pull', '--rebase', '--autostash', 'origin', 'main']
WRITERS = ['nhl-daily.yml', 'nba-daily.yml', 'nfl-weekly-update.yml', 'nfl-weekend-refresh.yml', 'collect-agent-log.yml']


def git(cwd, *args):
    r = subprocess.run(['git', *ID, *args], cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0 or args[0] == 'pull', r.stdout + r.stderr
    return r


@pytest.fixture
def repos(tmp_path):
    """(the runner's clone, a clone that moves main), both at one commit of results/graded.json."""
    git(tmp_path, 'init', '-q', '--bare', '-b', 'main', str(tmp_path / 'origin.git'))
    git(tmp_path, 'clone', '-q', str(tmp_path / 'origin.git'), 'other')
    other = tmp_path / 'other'
    (other / 'results').mkdir()
    (other / 'results' / 'graded.json').write_text('{"n": 1}\n', encoding='utf-8')
    (other / 'results' / 'notes.json').write_text('{"m": 1}\n', encoding='utf-8')
    git(other, 'add', '.')
    git(other, 'commit', '-qm', 'one')
    git(other, 'push', '-q', 'origin', 'HEAD:main')
    git(tmp_path, 'clone', '-q', str(tmp_path / 'origin.git'), 'runner')
    return tmp_path / 'runner', other


def move_main(other, name, text):
    (other / 'results' / name).write_text(text, encoding='utf-8')
    git(other, 'commit', '-qam', 'main moves')
    git(other, 'push', '-q', 'origin', 'HEAD:main')


def test_a_conflicting_autostash_exits_0_and_the_check_refuses_it(repos, capsys):
    runner, other = repos
    (runner / 'results' / 'graded.json').write_text('{"n": 2}\n', encoding='utf-8')
    move_main(other, 'graded.json', '{"n": 3}\n')
    pulled = git(runner, *PULL)
    assert pulled.returncode == 0, 'git itself reports success: that is the hole this closes'
    assert '<<<<<<<' in (runner / 'results' / 'graded.json').read_text(encoding='utf-8')
    found = pull_check.problems(runner)
    assert any(p.startswith('a stash is left') for p in found)
    assert 'unmerged: results/graded.json' in found
    assert 'conflict markers in: results/graded.json' in found
    assert pull_check.main(runner) == 1
    assert 'PULL REFUSED' in capsys.readouterr().out


def test_a_clean_autostash_passes(repos, capsys):
    runner, other = repos
    (runner / 'results' / 'graded.json').write_text('{"n": 2}\n', encoding='utf-8')
    move_main(other, 'notes.json', '{"m": 2}\n')
    assert git(runner, *PULL).returncode == 0
    assert pull_check.problems(runner) == []
    assert pull_check.main(runner) == 0


def test_a_marker_alone_is_refused(repos):
    """A file can carry markers with no stash and nothing unmerged (a hand
    resolution that went wrong); it is still never committed."""
    runner, _ = repos
    (runner / 'results' / 'graded.json').write_text('<<<<<<< Updated upstream\n{}\n=======\n{}\n>>>>>>> Stashed changes\n',
                                                     encoding='utf-8')
    assert pull_check.problems(runner) == ['conflict markers in: results/graded.json']


def test_a_markdown_underline_is_not_a_marker():
    assert not pull_check.MARKER.search('Title\n=======\n')


@pytest.mark.parametrize('name', WRITERS)
def test_every_writer_checks_straight_after_its_pull(name):
    text = (ROOT / '.github' / 'workflows' / name).read_text(encoding='utf-8')
    pulls = list(re.finditer(r'pull --rebase --autostash origin main\n', text))
    assert pulls, f'{name} no longer pulls with --autostash; re-read this guard'
    for m in pulls:
        nxt = text[m.end():].split('\n', 1)[0]
        assert nxt.strip() == 'python -m src.core.pull_check', f'{name}: the line after the pull is {nxt!r}'
