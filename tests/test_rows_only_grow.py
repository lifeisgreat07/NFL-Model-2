"""A collector's stored history only ever gains rows (audit 8, finding S5).

Run with: pytest tests/test_rows_only_grow.py -v
"""
from types import SimpleNamespace

from src.core import rows_only_grow as g


def fake(status, numstat):
    def run(cmd, **kwargs):
        return SimpleNamespace(stdout=numstat if '--numstat' in cmd else status)
    return run


def test_added_files_and_appended_rows_pass(capsys):
    run = fake('A\tdata/ncaam/history/games_2025.csv\nM\tdata/ncaam/history/games_2026.csv\n',
               '6300\t0\tdata/ncaam/history/games_2025.csv\n29\t0\tdata/ncaam/history/games_2026.csv\n')
    assert g.main(['data/ncaam/history'], run) == 0
    assert 'rows only grow: 2 files' in capsys.readouterr().out


def test_a_removed_or_rewritten_row_or_a_deleted_file_fails_naming_each(capsys):
    run = fake('M\tdata/ncaam/history/games_2026.csv\nD\tdata/ncaam/history/games_2024.csv\n',
               '1\t1\tdata/ncaam/history/games_2026.csv\n0\t6292\tdata/ncaam/history/games_2024.csv\n')
    assert g.main(['data/ncaam/history'], run) == 1
    out = capsys.readouterr().out
    assert 'M data/ncaam/history/games_2026.csv (1 lines removed)' in out and 'D data/ncaam/history/games_2024.csv' in out


def test_the_workflow_guards_the_history_before_committing_and_commits_after_a_listed_failure():
    from pathlib import Path
    wf = (Path(__file__).resolve().parent.parent / '.github' / 'workflows' / 'ncaam-collect.yml').read_text(
        encoding='utf-8')
    commit = wf[wf.index('- name: Commit the collected results'):]
    assert commit.index('python -m src.core.rows_only_grow data/ncaam/history') < commit.index('commit -q')
    assert "if: ${{ !cancelled() }}" in commit.split('- name:')[1]
