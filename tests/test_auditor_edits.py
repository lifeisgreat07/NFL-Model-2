"""A PR that edits Booth's instructions must say a human reviews it (Stage 23).

Booth's workflow checks out the PR's head, and its prompt tells it to read
BOOTH_PROTOCOL.md there, so a PR editing either file is audited by its own
edited instructions. On the Claude app's token the action refused to run on a
PR whose workflow differed from main's; on GITHUB_TOKEN it ran (#176). The
preflight now fails such a PR unless its body has a line beginning
'Human review required:'.
"""
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import scout_preflight as pf  # noqa: E402

LINE = "Human review required: this changes how Booth reads the diff.\n"


def check(body, changed):
    return pf.check_auditor_edits_need_a_human(body, changed)


def test_a_pr_not_touching_booths_instructions_passes():
    assert check('', ['src/weekly_update.py', 'README.md']).ok


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


def test_preflight_runs_it_on_the_branch_diff():
    src = inspect.getsource(pf.preflight)
    assert 'check_auditor_edits_need_a_human(body, changed_files(base, head))' in src
