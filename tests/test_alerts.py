"""
src/pipeline/alerts.py and its core copy src/core/alerts.py: one issue per
problem, opened once and commented on after. Every behaviour test runs on
both until Stage 52 deletes the NFL's copy.

`gh` is replaced by a recorder, so nothing here reaches GitHub. What is
checked is the conversation the module has with `gh`: which commands it
runs, in which order, and what it refuses to do.

Run with: pytest tests/test_alerts.py -v
"""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.core import alerts as core_alerts
from src.pipeline import alerts as nfl_alerts

MODULES = pytest.mark.parametrize('alerts', [nfl_alerts, core_alerts])


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


@MODULES
def test_no_open_issue_means_one_is_opened(alerts):
    gh = FakeGh(open_issues=[{'number': 3, 'title': 'Something else'}])
    action, ref = alerts.open_or_comment('Nightly canary failing', 'body text', run=gh)
    assert (action, ref) == ('opened', 'https://github.com/o/r/issues/9')
    assert gh.verbs() == ['issue list', 'issue create']
    args, stdin = gh.calls[-1]
    assert args[args.index('--title') + 1] == 'Nightly canary failing'
    assert stdin == 'body text'


@MODULES
def test_an_open_issue_with_the_same_title_gets_a_comment_not_a_twin(alerts):
    gh = FakeGh(open_issues=[{'number': 7, 'title': 'Nightly canary failing'}])
    action, ref = alerts.open_or_comment('Nightly canary failing', 'again', run=gh)
    assert (action, ref) == ('commented', 7)
    assert gh.verbs() == ['issue list', 'issue comment']
    args, stdin = gh.calls[-1]
    assert args[2] == '7' and stdin == 'again'


@MODULES
def test_the_title_match_is_exact(alerts):
    """A prefix is not the same problem: 'PR #10' must not land on 'PR #100'."""
    gh = FakeGh(open_issues=[{'number': 7, 'title': 'Booth audit failed: PR #100'}])
    action, _ = alerts.open_or_comment('Booth audit failed: PR #10', 'b', run=gh)
    assert action == 'opened'


@MODULES
def test_only_open_issues_are_searched(alerts):
    """Closing an issue is how a person says 'handled'. The search must ask
    for open issues only, or a closed one would swallow the next failure."""
    gh = FakeGh()
    alerts.open_or_comment('t', 'b', run=gh)
    args, _ = gh.calls[0]
    assert args[args.index('--state') + 1] == 'open'


@MODULES
def test_a_failing_gh_call_raises_rather_than_passing_quietly(alerts):
    gh = FakeGh(fail_on='issue create')
    with pytest.raises(RuntimeError, match='HTTP 403'):
        alerts.open_or_comment('t', 'b', run=gh)


@MODULES
def test_an_empty_body_is_refused(alerts, tmp_path, capsys):
    body = tmp_path / 'body.md'
    body.write_text('   \n', encoding='utf-8')
    assert alerts.main(['--title', 't', '--body-file', str(body)]) == 1
    assert 'empty body' in capsys.readouterr().err


# --- every scheduled job raises one ------------------------------------------

WORKFLOWS = Path(__file__).parent.parent / '.github' / 'workflows'


def scheduled_workflows(folder=WORKFLOWS):
    return sorted(p for p in folder.glob('*.yml')
                  if 'schedule:' in p.read_text(encoding='utf-8'))


def raises_an_alert_on_failure(text):
    """A step guarded by failure() that runs src.pipeline.alerts or
    src.core.alerts."""
    steps = text.split('\n      - ')
    return any('if: failure()' in s and ('src.pipeline.alerts' in s or 'src.core.alerts' in s) for s in steps)


def test_every_scheduled_workflow_opens_an_issue_when_it_fails():
    """Stage 30 item 7. Stage 4's rule is that nothing unattended fails
    silently, and it was written into each workflow by hand -- so the nightly
    mutation slice, added in Stage 27, failed with only a red run and an
    email. Enumerate the class: anything on a schedule must alert."""
    found = scheduled_workflows()
    assert len(found) >= 4, f'the scan found only {[p.name for p in found]}'
    silent = [p.name for p in found if not raises_an_alert_on_failure(p.read_text(encoding='utf-8'))]
    assert not silent, f'scheduled workflows that fail silently: {silent}'


def test_the_alert_check_can_tell_a_silent_workflow():
    """Synthetic, so the failing branch stays reachable while every real
    workflow alerts."""
    good = ("steps:\n      - name: run\n        run: x\n"
            "      - name: alert\n        if: failure()\n        run: python -m src.pipeline.alerts --title t\n")
    silent = "steps:\n      - name: run\n        run: x\n"
    unguarded = "steps:\n      - name: alert\n        run: python -m src.pipeline.alerts --title t\n"
    assert raises_an_alert_on_failure(good)
    assert raises_an_alert_on_failure(good.replace('src.pipeline.alerts', 'src.core.alerts'))
    assert not raises_an_alert_on_failure(good.replace('src.pipeline.alerts', 'src.core.alarms'))
    assert not raises_an_alert_on_failure(silent)
    assert not raises_an_alert_on_failure(unguarded)
