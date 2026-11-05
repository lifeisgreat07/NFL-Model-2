"""Stage 93 item 21: a daily run's commit may add picks and nothing else.

Against a real throwaway git repository: a committed pick, then a staged
change of each kind.

Run with: pytest tests/test_picks_only_grow.py -v
"""
import re
import subprocess
from pathlib import Path

import pytest

from src.core import picks_only_grow

ROOT = Path(__file__).resolve().parents[1]


def git(repo, *args):
    subprocess.run(['git', '-C', str(repo), '-c', 'user.name=t', '-c', 'user.email=t@t', *args],
                   check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    git(tmp_path, 'init', '-q')
    picks = tmp_path / 'predictions' / 'nhl' / '2026-11-04'
    picks.mkdir(parents=True)
    (picks / '2026020200.json').write_text('{"home_prob": 0.55}\n', encoding='utf-8')
    git(tmp_path, 'add', '-A')
    git(tmp_path, 'commit', '-q', '-m', 'one pick')
    monkeypatch.chdir(tmp_path)
    return tmp_path


def run_check():
    return picks_only_grow.main(['predictions/nhl'])


def test_a_new_pick_passes(repo, capsys):
    (repo / 'predictions/nhl/2026-11-04/2026020201.json').write_text('{}\n', encoding='utf-8')
    git(repo, 'add', '-A')
    assert run_check() == 0
    assert 'picks only grow: 1 added under predictions/nhl' in capsys.readouterr().out


def test_nothing_staged_passes(repo):
    assert run_check() == 0


@pytest.mark.parametrize('change, status', [('modify', 'M'), ('delete', 'D'), ('rename', 'D')])
def test_a_rewritten_removed_or_moved_pick_fails_the_step(repo, capsys, change, status):
    pick = repo / 'predictions/nhl/2026-11-04/2026020200.json'
    if change == 'modify':
        pick.write_text('{"home_prob": 0.45}\n', encoding='utf-8')
    elif change == 'delete':
        pick.unlink()
    else:
        pick.rename(pick.with_name('2026020299.json'))
    git(repo, 'add', '-A')
    assert run_check() == 1
    out = capsys.readouterr().out
    assert out.startswith('PICKS CHANGED') and f'  {status} predictions/nhl/2026-11-04/2026020200.json' in out


def test_a_change_outside_the_picks_is_not_its_business(repo):
    (repo / 'results').mkdir()
    (repo / 'results/grades.json').write_text('{}\n', encoding='utf-8')
    git(repo, 'add', '-A')
    assert run_check() == 0


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_each_daily_run_checks_after_staging_and_before_committing(sport):
    text = (ROOT / '.github' / 'workflows' / f'{sport}-daily.yml').read_text(encoding='utf-8')
    step = next(s for s in text.split('\n      - ') if s.startswith(f"name: Commit the {sport.upper()}'s picks"))
    check = f'python -m src.core.picks_only_grow predictions/{sport}'
    assert check in step
    assert step.index(f'git add predictions/{sport}') < step.index(check) < step.index('commit -q -m')
    assert not re.search(r'picks_only_grow[^\n]*\|\|', step), 'the check must be able to fail the step'
