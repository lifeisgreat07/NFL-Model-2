"""
src/alerts.py: one issue per problem, opened once and commented on after.

`gh` is replaced by a recorder, so nothing here reaches GitHub. What is
checked is the conversation the module has with `gh`: which commands it
runs, in which order, and what it refuses to do.

Run with: pytest tests/test_alerts.py -v
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import alerts  # noqa: E402


class FakeGh:
    """Records every gh call; answers `issue list` from a fixed list."""

    def __init__(self, open_issues=(), fail_on=None):
        self.open_issues = list(open_issues)
        self.fail_on = fail_on
        self.calls = []

    def __call__(self, cmd, input=None, capture_output=True, text=True):
        assert cmd[0] == 'gh'
        self.calls.append((cmd[1:], input))
        verb = ' '.join(cmd[1:3])
        if verb == self.fail_on:
            return SimpleNamespace(returncode=1, stdout='', stderr='HTTP 403')
        if verb == 'issue list':
            return SimpleNamespace(returncode=0, stdout=json.dumps(self.open_issues), stderr='')
        if verb == 'issue create':
            return SimpleNamespace(returncode=0, stdout='https://github.com/o/r/issues/9\n', stderr='')
        return SimpleNamespace(returncode=0, stdout='', stderr='')

    def verbs(self):
        return [' '.join(args[:2]) for args, _ in self.calls]


def test_no_open_issue_means_one_is_opened():
    gh = FakeGh(open_issues=[{'number': 3, 'title': 'Something else'}])
    action, ref = alerts.open_or_comment('Nightly canary failing', 'body text', run=gh)
    assert (action, ref) == ('opened', 'https://github.com/o/r/issues/9')
    assert gh.verbs() == ['issue list', 'issue create']
    args, stdin = gh.calls[-1]
    assert args[args.index('--title') + 1] == 'Nightly canary failing'
    assert stdin == 'body text'


def test_an_open_issue_with_the_same_title_gets_a_comment_not_a_twin():
    gh = FakeGh(open_issues=[{'number': 7, 'title': 'Nightly canary failing'}])
    action, ref = alerts.open_or_comment('Nightly canary failing', 'again', run=gh)
    assert (action, ref) == ('commented', 7)
    assert gh.verbs() == ['issue list', 'issue comment']
    args, stdin = gh.calls[-1]
    assert args[2] == '7' and stdin == 'again'


def test_the_title_match_is_exact():
    """A prefix is not the same problem: 'PR #10' must not land on 'PR #100'."""
    gh = FakeGh(open_issues=[{'number': 7, 'title': 'Booth audit failed: PR #100'}])
    action, _ = alerts.open_or_comment('Booth audit failed: PR #10', 'b', run=gh)
    assert action == 'opened'


def test_only_open_issues_are_searched():
    """Closing an issue is how a person says 'handled'. The search must ask
    for open issues only, or a closed one would swallow the next failure."""
    gh = FakeGh()
    alerts.open_or_comment('t', 'b', run=gh)
    args, _ = gh.calls[0]
    assert args[args.index('--state') + 1] == 'open'


def test_a_failing_gh_call_raises_rather_than_passing_quietly():
    gh = FakeGh(fail_on='issue create')
    with pytest.raises(RuntimeError, match='HTTP 403'):
        alerts.open_or_comment('t', 'b', run=gh)


def test_an_empty_body_is_refused(tmp_path, capsys):
    body = tmp_path / 'body.md'
    body.write_text('   \n', encoding='utf-8')
    assert alerts.main(['--title', 't', '--body-file', str(body)]) == 1
    assert 'empty body' in capsys.readouterr().err
