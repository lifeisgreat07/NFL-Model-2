"""
Stage 81 item 1: an issue while a QB override pull request is waiting to merge.

`gh` is replaced by the recorder from tests/test_alerts.py, so nothing here
reaches GitHub. The workflow is read as text: it must run on the pull
request's own events for the override folder, and run the BASE commit's code.

Run with: pytest tests/test_override_watch.py -v
"""
import re
from pathlib import Path

from src.sports.nfl import override_watch as ow
from tests.test_alerts import FakeGh

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / '.github' / 'workflows' / 'nfl-override-watch.yml').read_text(encoding='utf-8')
WEEK9 = 'data/nfl/qb_overrides/2026_week9.json'


def test_only_override_files_name_a_week():
    paths = [WEEK9, 'README.md', 'data/nfl/qb_overrides/notes.txt', 'data/nfl/qb_overrides/2026_week10.json']
    assert ow.override_weeks(paths) == [(2026, 9), (2026, 10)]
    assert ow.override_weeks(['src/sports/nfl/weekly_update.py']) == []


def test_the_file_name_matches_the_one_the_lock_reads(tmp_path):
    """The watch and load_qb_overrides must agree on the file name, or the watch
    would stay quiet about the very file the lock ignores."""
    from src.sports.nfl.weekly_update import load_qb_overrides
    (tmp_path / '2026_week9.json').write_text(
        '[{"team": "PHI", "player_id": "00-0038400", "player_name": "Tanner McKee", '
        '"source": "https://example.com"}]', encoding='utf-8')
    assert load_qb_overrides(2026, 9, directory=tmp_path)
    assert ow.override_weeks([f'data/nfl/qb_overrides/{p.name}' for p in tmp_path.iterdir()]) == [(2026, 9)]


def test_an_opened_pull_request_opens_an_issue_naming_the_lock():
    gh = FakeGh()
    lines = ow.handle('opened', 549, 'https://github.com/o/r/pull/549', False, [WEEK9], run=gh)
    assert gh.verbs() == ['issue list', 'issue create']
    args, body = gh.calls[-1]
    assert args[args.index('--title') + 1] == 'NFL: 2026 week 9 QB override waiting to merge'
    assert '#549' in body and 'Thursday 11:00 UTC' in body
    assert lines and lines[0].startswith('opened')


def test_a_second_pull_request_for_the_same_week_comments_rather_than_opening_a_twin():
    gh = FakeGh(open_issues=[{'number': 12, 'title': ow.title(2026, 9)}])
    ow.handle('reopened', 551, 'https://github.com/o/r/pull/551', False, [WEEK9], run=gh)
    assert gh.verbs() == ['issue list', 'issue comment']


def test_a_merge_closes_the_issue_with_a_comment_saying_so():
    gh = FakeGh(open_issues=[{'number': 12, 'title': ow.title(2026, 9)}])
    lines = ow.handle('closed', 549, 'u', True, [WEEK9], run=gh)
    assert gh.verbs() == ['issue list', 'issue comment', 'issue close']
    assert 'was merged' in gh.calls[1][1]
    assert gh.calls[2][0][2] == '12'
    assert lines == [f'closed: 12 ({ow.title(2026, 9)})']


def test_closing_without_merging_says_the_overrides_will_not_be_used():
    gh = FakeGh(open_issues=[{'number': 12, 'title': ow.title(2026, 9)}])
    ow.handle('closed', 549, 'u', False, [WEEK9], run=gh)
    assert 'without merging' in gh.calls[1][1]


def test_a_pull_request_with_no_override_file_does_nothing():
    gh = FakeGh()
    assert ow.handle('opened', 5, 'u', False, ['README.md'], run=gh) == []
    assert gh.calls == []


def test_the_workflow_runs_on_the_pull_requests_own_events_for_the_override_folder():
    assert re.search(r'pull_request:\s*\n\s*types: \[opened, reopened, closed\]', WORKFLOW)
    assert "- 'data/nfl/qb_overrides/**'" in WORKFLOW
    assert 'schedule:' not in WORKFLOW


def test_the_workflow_runs_the_base_commits_code_never_the_pull_requests():
    assert 'ref: ${{ github.event.pull_request.base.sha }}' in WORKFLOW
    assert 'head.sha' not in WORKFLOW
    assert 'python3 -m src.sports.nfl.override_watch' in WORKFLOW


def test_the_workflow_holds_no_write_scope_but_issues():
    perms = re.search(r'^permissions:\n((?:  .+\n)+)', WORKFLOW, re.M).group(1)
    writes = sorted(line.split(':')[0].strip() for line in perms.splitlines() if line.strip().endswith('write'))
    assert writes == ['issues']


# --- Stage 81 item 2: after the lock -----------------------------------------

def pr(number, *paths):
    return {'number': number, 'url': f'https://github.com/o/r/pull/{number}', 'files': [{'path': p} for p in paths]}


def test_an_open_override_for_a_locked_week_is_found(tmp_path):
    (tmp_path / '2026_week9.json').write_text('[]', encoding='utf-8')
    prs = [pr(560, WEEK9), pr(561, 'data/nfl/qb_overrides/2026_week10.json'), pr(562, 'README.md')]
    assert ow.locked_while_open(2026, prs, tmp_path) == [(9, 560, 'https://github.com/o/r/pull/560')]


def test_a_preview_is_not_a_lock(tmp_path):
    (tmp_path / 'preview').mkdir()
    (tmp_path / 'preview' / '2026_week9.json').write_text('[]', encoding='utf-8')
    assert ow.locked_while_open(2026, [pr(560, WEEK9)], tmp_path) == []


def test_after_the_lock_it_raises_one_issue_per_week(tmp_path):
    import json as _json
    from types import SimpleNamespace
    (tmp_path / '2026_week9.json').write_text('[]', encoding='utf-8')
    gh = FakeGh()
    real = gh.__call__

    def run(cmd, input=None, capture_output=True, text=True):
        if cmd[:3] == ['gh', 'pr', 'list']:
            return SimpleNamespace(returncode=0, stdout=_json.dumps([pr(560, WEEK9)]), stderr='')
        return real(cmd, input=input)
    lines = ow.after_lock(2026, run=run, pred_dir=tmp_path)
    assert gh.verbs() == ['issue list', 'issue create']
    args, body = gh.calls[-1]
    assert args[args.index('--title') + 1] == 'NFL: 2026 week 9 locked while its QB override was unmerged'
    assert '#560' in body and 'never rewritten' in body
    assert lines and lines[0].startswith('opened')


def test_the_weekly_update_asks_after_the_lock_and_cannot_fail_on_it():
    text = (ROOT / '.github' / 'workflows' / 'nfl-weekly-update.yml').read_text(encoding='utf-8')
    step = text[text.index('- name: Was a QB override still waiting at the lock?'):]
    step = step[:step.index('\n      - name:')]
    assert 'python -m src.sports.nfl.override_watch --after-lock' in step
    assert 'continue-on-error: true' in step
    names = re.findall(r'^      - name: (.+)$', text, re.M)
    assert names.index('Was a QB override still waiting at the lock?') > names.index("Generate/lock in this week's predictions")
