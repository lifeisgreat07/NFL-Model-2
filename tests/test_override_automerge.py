"""Stage 90 item 4: a pull request that only adds or changes QB override files,
and passes the roster and source check, can merge itself -- once Mark turns it on.

Run with: pytest tests/test_override_automerge.py -v
"""
import json
from pathlib import Path

import pytest

from src.sports.nfl import override_automerge as am

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github' / 'workflows' / 'nfl-override-automerge.yml'


def f(name, status='added'):
    return {'filename': name, 'status': status}


def test_only_override_files_that_passed_the_check_merge():
    assert am.decide([f('data/nfl/qb_overrides/2026_week10.json')], 0, True) == (True, [])
    assert am.decide([f('data/nfl/qb_overrides/2026_week10.json', 'modified'),
                      f('data/nfl/qb_overrides/2026_week11.json')], 0, True)[0]


@pytest.mark.parametrize('files, check, same, says', [
    ([f('data/nfl/qb_overrides/2026_week10.json'), f('src/sports/nfl/weekly_update.py', 'modified')], 0, True,
     'src/sports/nfl/weekly_update.py is not a QB override file'),
    ([f('data/nfl/qb_overrides/2026_week10.json', 'removed')], 0, True, 'is removed, not added or modified'),
    ([f('data/nfl/qb_overrides/2026_week10.json', 'renamed')], 0, True, 'is renamed, not added or modified'),
    ([f('data/nfl/qb_overrides/notes.json')], 0, True, 'is not a QB override file'),
    ([f('data/nfl/qb_overrides/2026_week10.json')], 1, True, 'the override check did not pass'),
    ([f('data/nfl/qb_overrides/2026_week10.json')], 0, False, 'comes from a fork'),
    ([], 0, True, 'changes no file'),
], ids=['code-too', 'deleted', 'renamed', 'other-name', 'check-failed', 'fork', 'empty'])
def test_anything_else_is_left_for_a_person_and_says_why(files, check, same, says):
    merge, why = am.decide(files, check, same)
    assert merge is False and any(says in w for w in why), why


def test_the_cli_merges_or_leaves_by_its_exit_code(tmp_path, capsys):
    path = tmp_path / 'files.ndjson'
    path.write_text(json.dumps(f('data/nfl/qb_overrides/2026_week10.json')) + '\n', encoding='utf-8')
    assert am.main(['--files', str(path), '--check-exit', '0', '--same-repo', 'true']) == 0
    assert am.main(['--files', str(path), '--check-exit', '1', '--same-repo', 'true']) == 1
    assert 'LEAVE FOR A PERSON: the override check did not pass' in capsys.readouterr().out


def test_the_workflow_is_off_until_the_variable_is_set_and_runs_the_base_commits_code():
    t = WF.read_text(encoding='utf-8')
    assert "if: vars.AUTO_MERGE_OVERRIDES == 'true' && github.event.pull_request.head.repo.full_name == github.repository" in t
    assert 'ref: ${{ github.event.pull_request.base.sha }}' in t and 'persist-credentials: false' in t
    assert "      - 'data/nfl/qb_overrides/**'" in t


def test_it_merges_only_on_the_rule_and_only_the_commit_it_checked():
    t = WF.read_text(encoding='utf-8')
    check_at = t.index('python -m src.sports.nfl.override_check "$RUNNER_TEMP"/overrides/*.json')
    rule_at = t.index('python -m src.sports.nfl.override_automerge --files "$RUNNER_TEMP/files.ndjson"')
    merge_at = t.index('gh pr merge "$PR" --repo "$GITHUB_REPOSITORY" --merge --match-head-commit "$HEAD_SHA"')
    assert check_at < rule_at < merge_at
    assert 'if [ "$decision" = "0" ]; then' in t[rule_at:merge_at]
