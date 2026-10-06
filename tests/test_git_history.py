"""tests/git_history.py follows a file through a move (ahead of Stage 52).

Built in a throwaway repository: a registry and a result are committed, then
both are moved the way Stage 52 moves the NFL's experiments. The helper must
still name the commit that first added the result and the path it had then,
and the registry beside it there.

Run with: pytest tests/test_git_history.py -v
"""
import subprocess

import pytest
from git_history import first_added, registry_beside


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, check=True).stdout


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / 'r'
    r.mkdir()
    git(r, 'init', '-q', '-b', 'main')
    git(r, 'config', 'user.email', 't@example.com')
    git(r, 'config', 'user.name', 't')
    stage = r / 'experiments' / 'stage5'
    (stage / 'results').mkdir(parents=True)
    (stage / 'registry.json').write_text('{"hypotheses": [{"id": "H1"}]}\n', encoding='utf-8')
    git(r, 'add', '-A')
    git(r, 'commit', '-q', '-m', 'register')
    (stage / 'results' / 'H1.json').write_text('{"answer": 1, "padding": "' + 'x' * 200 + '"}\n',
                                               encoding='utf-8')
    git(r, 'add', '-A')
    git(r, 'commit', '-q', '-m', 'answer')
    answered = git(r, 'rev-parse', 'HEAD').strip()
    (r / 'experiments' / 'nfl').mkdir()
    git(r, 'mv', 'experiments/stage5', 'experiments/nfl/stage5')
    git(r, 'commit', '-q', '-m', 'move')
    return r, answered


def test_a_moved_result_is_traced_to_the_commit_that_first_added_it(repo):
    r, answered = repo
    sha, path = first_added(r, 'experiments/nfl/stage5/results/H1.json')
    assert sha == answered
    assert path == 'experiments/stage5/results/H1.json'
    assert registry_beside(path) == 'experiments/stage5/registry.json'
    parent_registry = git(r, 'show', f'{sha}^:{registry_beside(path)}')
    assert '"H1"' in parent_registry


def test_a_file_never_committed_has_no_history(repo):
    r, _ = repo
    (r / 'new.json').write_text('{}', encoding='utf-8')
    assert first_added(r, 'new.json') is None


def test_the_registry_is_traced_through_the_move_too(repo):
    r, _ = repo
    registry = first_added(r, 'experiments/nfl/stage5/registry.json')
    assert registry is not None
    first_registry = git(r, 'rev-list', '--max-parents=0', 'HEAD').strip()
    assert registry == (first_registry, 'experiments/stage5/registry.json')
