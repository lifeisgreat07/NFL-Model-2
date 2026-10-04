"""A PR that edits Booth's instructions must say a human reviews it (Stage 23).

Booth's workflow checks out the PR's head, and its prompt tells it to read
BOOTH_PROTOCOL.md there, so a PR editing either file is audited by its own
edited instructions. On the Claude app's token the action refused to run on a
PR whose workflow differed from main's; on GITHUB_TOKEN it ran (#176). The
preflight now fails such a PR unless its body has a line beginning
'Human review required:'.
"""
import inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from src.agents import scout_preflight as pf

LINE = "Human review required: this changes how Booth reads the diff.\n"


def check(body, changed):
    return pf.check_auditor_edits_need_a_human(body, changed)


def test_a_pr_not_touching_booths_instructions_passes():
    assert check('', ['src/pipeline/weekly_update.py', 'README.md']).ok


def test_editing_booths_workflow_without_the_line_fails():
    f = check('Stage 23 item 9.\n', ['.github/workflows/booth-pr-audit.yml'])
    assert not f.ok and 'booth-pr-audit.yml' in f.detail


def test_editing_the_protocol_without_the_line_fails():
    assert not check('Stage 23 item 9.\n', ['BOOTH_PROTOCOL.md', 'src/x.py']).ok


def test_the_line_lets_it_pass():
    assert check('Stage 23 item 9.\n\n' + LINE, ['BOOTH_PROTOCOL.md']).ok
    assert check('**Human review required:** yes.\n', ['BOOTH_PROTOCOL.md']).ok


def test_the_phrase_mid_sentence_is_not_the_line():
    """Discussing the rule is not declaring it: the line must start with it."""
    body = 'This PR does not need a line saying human review required: it is docs.\n'
    assert not check(body, ['BOOTH_PROTOCOL.md']).ok


def test_the_files_it_watches_exist():
    """A renamed file would leave the check watching nothing, and passing."""
    for rel in pf.AUDITOR_FILES:
        assert (ROOT / rel).exists(), f'{rel} does not exist -- update AUDITOR_FILES'


def test_preflight_runs_it_on_the_branch_diff_and_the_stripped_body():
    src = inspect.getsource(pf.preflight)
    assert 'check_auditor_edits_need_a_human(claims, changed_files(base, head))' in src


def test_a_line_quoted_in_a_code_fence_is_not_the_line():
    """Stage 30 item 6. Quoting the rule in a fenced block is not declaring
    it; preflight hands this check the quotation-stripped body, so the line
    inside the fence is gone before the check reads it."""
    body = ('Stage 30 item 6.\n\n```\n' + LINE + '```\n')
    assert check(body, ['BOOTH_PROTOCOL.md']).ok, 'fixture: the raw body does satisfy it'
    assert not check(pf.strip_quotations(body), ['BOOTH_PROTOCOL.md']).ok


def test_a_renamed_auditor_file_is_listed_under_its_old_name(monkeypatch):
    """Stage 30 item 6. With rename detection on, `git diff --name-only`
    lists only the new name, so renaming booth-pr-audit.yml slipped past."""
    calls = []
    monkeypatch.setattr(pf, '_git', lambda *a: calls.append(a) or '')
    pf.changed_files('main')
    assert calls and '--no-renames' in calls[0], (
        'changed_files lets git collapse a rename into its new name')
