"""
src/core/alerts.py: one issue per problem, opened once and commented on
after. Until Stage 52 the NFL kept its own copy (src/pipeline/alerts.py) and
every behaviour test ran on both; Stage 52 deleted that copy, so they run on
the core's alone.

`gh` is replaced by a recorder, so nothing here reaches GitHub. What is
checked is the conversation the module has with `gh`: which commands it
runs, in which order, and what it refuses to do.

Run with: pytest tests/test_alerts.py -v
"""
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.core import alerts


class FakeGh:
    """Records every gh call; answers `issue list` from a fixed list."""

    def __init__(self, open_issues=(), fail_on=None, issue=None):
        self.open_issues = list(open_issues)
        self.fail_on = fail_on
        self.issue = issue if issue is not None else {'body': '', 'comments': []}
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
        if verb == 'issue view':
            return SimpleNamespace(returncode=0, stdout=json.dumps(self.issue), stderr='')
        return SimpleNamespace(returncode=0, stdout='', stderr='')

    def verbs(self):
        return [' '.join(args[:2]) for args, _ in self.calls]


def test_no_open_issue_means_one_is_opened():
    gh = FakeGh(open_issues=[{'number': 3, 'title': 'Something else'}])
    action, ref = alerts.open_or_comment('NFL: Nightly canary failing', 'body text', run=gh)
    assert (action, ref) == ('opened', 'https://github.com/o/r/issues/9')
    assert gh.verbs() == ['issue list', 'issue create']
    args, stdin = gh.calls[-1]
    assert args[args.index('--title') + 1] == 'NFL: Nightly canary failing'
    assert stdin == f"body text\n\n<!-- alert-key: {alerts.report_key('body text')} -->"


def test_an_open_issue_with_the_same_title_gets_a_comment_not_a_twin():
    gh = FakeGh(open_issues=[{'number': 7, 'title': 'NFL: Nightly canary failing'}])
    action, ref = alerts.open_or_comment('NFL: Nightly canary failing', 'again', run=gh)
    assert (action, ref) == ('commented', 7)
    assert gh.verbs() == ['issue list', 'issue view', 'issue comment']
    args, stdin = gh.calls[-1]
    assert args[2] == '7' and stdin.startswith('again\n\n<!-- alert-key: ')


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
    with pytest.raises(RuntimeError, match='failed 3 times: HTTP 403'):
        alerts.open_or_comment('t', 'b', run=gh)


# --- Stage 93 item 12: an alert is retried, then kept where the run shows it --

@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    """Every test here: the backoff is recorded, not slept."""
    waits = []
    monkeypatch.setattr(alerts, 'SLEEP', waits.append)
    return waits


class FlakyGh(FakeGh):
    """Fails one verb its first `times` calls, then answers like FakeGh."""

    def __init__(self, verb, times, **kw):
        super().__init__(**kw)
        self.verb, self.left = verb, times

    def __call__(self, cmd, input=None, capture_output=True, text=True):
        if ' '.join(cmd[1:3]) == self.verb and self.left:
            self.left -= 1
            self.calls.append((cmd[1:], input))
            return SimpleNamespace(returncode=1, stdout='', stderr='HTTP 502')
        return super().__call__(cmd, input, capture_output, text)


def test_a_gh_call_that_fails_twice_then_answers_opens_the_issue(no_waiting):
    gh = FlakyGh('issue create', 2)
    assert alerts.open_or_comment('NHL: daily run failed', 'b', run=gh) == ('opened', 'https://github.com/o/r/issues/9')
    assert gh.verbs() == ['issue list', 'issue create', 'issue create', 'issue create']
    assert no_waiting == list(alerts.BACKOFF)


def test_three_failures_keep_the_alert_in_the_summary_and_fail_the_step(tmp_path, monkeypatch, capsys, no_waiting):
    gh = FlakyGh('issue create', 3)
    real = alerts.open_or_comment
    monkeypatch.setattr(alerts, 'open_or_comment', lambda *a, **k: real(*a, run=gh, **k))
    summary = tmp_path / 'summary.md'
    monkeypatch.setenv('GITHUB_STEP_SUMMARY', str(summary))
    body = tmp_path / 'body.md'
    body.write_text('The NHL daily run failed. See run 5.', encoding='utf-8')
    assert alerts.main(['--title', 'NHL: daily run failed', '--body-file', str(body)]) == 1
    kept = summary.read_text(encoding='utf-8')
    assert kept.startswith('## Alert not raised: NHL: daily run failed')
    assert 'failed 3 times: HTTP 502' in kept and 'The NHL daily run failed. See run 5.' in kept
    assert '::error title=Alert not raised::NHL: daily run failed' in capsys.readouterr().out
    assert gh.verbs().count('issue create') == 3 and no_waiting == list(alerts.BACKOFF)


def test_the_daily_runs_success_path_alerts_cannot_skip_each_other():
    """A refused alert fails its step; the alerts after it must still run."""
    for wf in ('nhl-daily.yml', 'nba-daily.yml'):
        text = (WORKFLOWS / wf).read_text(encoding='utf-8')
        steps = [s for s in text.split('\n      - ')
                 if 'if: success()' in s and 'src.core.alerts --title' in s]
        assert len(steps) == 3, wf
        assert all('continue-on-error: true' in s for s in steps), wf


def test_an_empty_body_is_refused(tmp_path, capsys):
    body = tmp_path / 'body.md'
    body.write_text('   \n', encoding='utf-8')
    assert alerts.main(['--title', 't', '--body-file', str(body)]) == 1
    assert 'empty body' in capsys.readouterr().err



def test_an_alert_carries_the_last_lines_of_its_log(tmp_path):
    """Stage 81 item 5: a run's log needs a sign-in, so the cause goes in the issue."""
    log = tmp_path / 'nba-daily.log'
    log.write_text('\n'.join(f'line {i}' for i in range(1, 51)), encoding='utf-8')
    body = alerts.with_log_tail('The NBA daily run failed.', str(log))
    assert body.startswith('The NBA daily run failed.')
    assert 'line 50' in body and 'line 21' in body and 'line 20\n' not in body
    assert 'Last 30 lines of nba-daily.log' in body


def test_a_missing_log_is_said_not_skipped(tmp_path):
    body = alerts.with_log_tail('failed', str(tmp_path / 'nope.log'))
    assert 'No log was written (nope.log)' in body


def test_the_cli_passes_the_log_through(tmp_path, monkeypatch):
    sent = {}
    monkeypatch.setattr(alerts, 'open_or_comment',
                        lambda title, body, key=None: sent.update(body=body, key=key) or ('opened', 1))
    (tmp_path / 'b.md').write_text('body', encoding='utf-8')
    (tmp_path / 'x.log').write_text('Traceback: boom', encoding='utf-8')
    assert alerts.main(['--title', 't', '--body-file', str(tmp_path / 'b.md'), '--log', str(tmp_path / 'x.log')]) == 0
    assert 'Traceback: boom' in sent['body']
    # The log's tail is new every run; what makes two alerts the same is the report.
    assert sent['key'] == 'body'


#: Workflows whose failure alert used to carry only a link (Stage 81 item 5). Each
#: must tee its main step's output, stderr included, and hand that log to the alert.
LOGGED = {'nba-daily.yml': 'nba-daily.log', 'nhl-daily.yml': 'nhl-daily.log',
          'line-judge-digest.yml': 'digest.log', 'nightly-mutation.yml': 'slice.log',
          'nightly-random-order.yml': 'shuffled.log'}


def test_these_failure_alerts_carry_their_logs():
    for name, log in LOGGED.items():
        text = (WORKFLOWS / name).read_text(encoding='utf-8')
        assert f'2>&1 | tee {log}' in text, f'{name}: the main step does not keep its output, stderr included, in {log}'
        alert = [s for s in text.split('\n      - ') if 'if: failure()' in s and 'src.core.alerts' in s]
        assert alert and all(f'--log {log}' in s for s in alert), f'{name}: the failure alert does not carry {log}'


def test_closing_comments_then_closes_the_open_issue():
    """Stage 81 item 1: an alert whose cause ends by itself closes itself."""
    gh = FakeGh(open_issues=[{'number': 7, 'title': 'NFL: 2026 week 9 QB override waiting to merge'}])
    assert alerts.close_open_issue('NFL: 2026 week 9 QB override waiting to merge', 'merged', run=gh) == 7
    assert gh.verbs() == ['issue list', 'issue comment', 'issue close']
    assert gh.calls[1][1] == 'merged'


def test_closing_with_no_open_issue_creates_nothing():
    gh = FakeGh(open_issues=[{'number': 3, 'title': 'Something else'}])
    assert alerts.close_open_issue('NFL: 2026 week 9 QB override waiting to merge', 'merged', run=gh) is None
    assert gh.verbs() == ['issue list']


# --- every scheduled job raises one ------------------------------------------

WORKFLOWS = Path(__file__).parent.parent / '.github' / 'workflows'


def scheduled_workflows(folder=WORKFLOWS):
    return sorted(p for p in folder.glob('*.yml')
                  if 'schedule:' in p.read_text(encoding='utf-8'))


def raises_an_alert_on_failure(text):
    """A step guarded by failure() that runs src.core.alerts."""
    steps = text.split('\n      - ')
    return any('if: failure()' in s and 'src.core.alerts' in s for s in steps)


#: Run by an event, not by a person, and writing something a person relies on (Stage 93 item 14, audit 7
#: R13): the Pages deploy runs on other workflows' data commits, and the QB override watch is what tells
#: Mark an override is waiting before the lock. booth-alert.yml is itself the alert for a failed audit.
EVENT_WRITERS = ('deploy-pages.yml', 'nfl-override-watch.yml')
NOT_ALERTED = ('booth-alert.yml',)


def unattended_workflows(folder=WORKFLOWS):
    """Every workflow that runs with nobody watching: on a schedule, on another workflow's
    completion, or one of the event-driven writers."""
    return sorted(p for p in folder.glob('*.yml')
                  if p.name not in NOT_ALERTED
                  and (re.search(r'(?m)^  (schedule|workflow_run):', p.read_text(encoding='utf-8'))
                       or p.name in EVENT_WRITERS))


def test_every_unattended_workflow_opens_an_issue_when_it_fails():
    found = unattended_workflows()
    assert {'deploy-pages.yml', 'nfl-override-watch.yml', 'nhl-daily.yml'} <= {p.name for p in found}
    silent = [p.name for p in found if not raises_an_alert_on_failure(p.read_text(encoding='utf-8'))]
    assert not silent, f'unattended workflows that fail silently: {silent}'


def test_every_job_of_the_pages_deploy_alerts():
    """Two jobs: a build that fails and a deploy that fails must each raise."""
    text = (WORKFLOWS / 'deploy-pages.yml').read_text(encoding='utf-8')
    jobs = re.split(r'(?m)^  (?=build:|deploy:)', text.split('\njobs:\n', 1)[1])[1:]
    assert [j.split(':')[0] for j in jobs] == ['build', 'deploy']
    assert all(raises_an_alert_on_failure(j) for j in jobs)


def test_every_scheduled_workflow_opens_an_issue_when_it_fails():
    """Stage 30 item 7. Stage 4's rule is that nothing unattended fails
    silently, and it was written into each workflow by hand -- so the nightly
    mutation slice, added in Stage 27, failed with only a red run and an
    email. Enumerate the class: anything on a schedule must alert."""
    found = scheduled_workflows()
    assert len(found) >= 4, f'the scan found only {[p.name for p in found]}'
    silent = [p.name for p in found if not raises_an_alert_on_failure(p.read_text(encoding='utf-8'))]
    assert not silent, f'scheduled workflows that fail silently: {silent}'


def test_a_silent_workflow_run_writer_is_in_the_class_and_is_caught(tmp_path):
    """Stage 93 item 14: the synthetic check, extended to a workflow_run sample."""
    (tmp_path / 'rebuild.yml').write_text(
        'on:\n  workflow_run:\n    workflows: ["x"]\n    types: [completed]\n'
        'jobs:\n  build:\n    steps:\n      - name: run\n        run: x\n', encoding='utf-8')
    (tmp_path / 'manual.yml').write_text('on:\n  workflow_dispatch: {}\n', encoding='utf-8')
    found = unattended_workflows(tmp_path)
    assert [p.name for p in found] == ['rebuild.yml']
    assert not raises_an_alert_on_failure(found[0].read_text(encoding='utf-8'))


def test_the_alert_check_can_tell_a_silent_workflow():
    """Synthetic, so the failing branch stays reachable while every real
    workflow alerts."""
    good = ("steps:\n      - name: run\n        run: x\n"
            "      - name: alert\n        if: failure()\n        run: python -m src.core.alerts --title t\n")
    silent = "steps:\n      - name: run\n        run: x\n"
    unguarded = "steps:\n      - name: alert\n        run: python -m src.core.alerts --title t\n"
    assert raises_an_alert_on_failure(good)
    assert not raises_an_alert_on_failure(good.replace('src.core.alerts', 'src.core.alarms'))
    assert not raises_an_alert_on_failure(silent)
    assert not raises_an_alert_on_failure(unguarded)



# --- Stage 83 item 1: an alert closes when its cause does --------------------

def test_resolve_closes_the_open_issue_and_creates_nothing(tmp_path, monkeypatch):
    closed = []
    monkeypatch.setattr(alerts, 'close_open_issue', lambda title, body: closed.append((title, body)) or 7)
    monkeypatch.setattr(alerts, 'open_or_comment', lambda *a, **k: pytest.fail('a resolve opened an issue'))
    (tmp_path / 'r.md').write_text('Recovered: run 1', encoding='utf-8')
    assert alerts.main(['--resolve', '--title', 'NBA: daily run failed', '--body-file', str(tmp_path / 'r.md')]) == 0
    assert closed == [('NBA: daily run failed', 'Recovered: run 1')]


def failure_titles(text):
    """Every title a failure alert in a workflow raises. Stage 93 item 15 took
    out the exemption for templated titles ("NBA: $source failing ..."): such a
    title has no fixed resolver, and #543 stayed open after its canary recovered."""
    titles = []
    for step in text.split('\n      - '):
        if 'if: failure()' in step and 'src.core.alerts' in step:
            titles += re.findall(r'--title "([^"]+)"', step)
    return titles


def test_no_failure_alert_has_a_templated_title():
    templated = [(p.name, t) for p in sorted(WORKFLOWS.glob('*.yml'))
                 for t in failure_titles(p.read_text(encoding='utf-8')) if '$' in t]
    assert not templated, f'a failure title nothing fixed can close: {templated}'


def test_the_nba_canary_raises_and_closes_one_fixed_title_per_source():
    from src.sports.nba import canary
    text = (WORKFLOWS / 'nba-canary.yml').read_text(encoding='utf-8')
    per_source = {f'NBA: {name} failing in the nightly canary' for name, _ in canary.CHECKS}
    raised = set(failure_titles(text)) - {'NBA: nightly canary failing'}
    assert raised == per_source
    for name, _ in canary.CHECKS:
        assert f"grep -qx '{name}' nba-canary-failed.txt" in text, name


def test_every_failure_alert_is_closed_by_the_next_success():
    """A failure issue whose run later succeeds used to stay open until a person
    closed it; 14 were open on 2026-11-02. Each fixed title must have a step,
    on success() and unable to fail the run, that resolves the same title."""
    found = 0
    for p in sorted(WORKFLOWS.glob('*.yml')):
        text = p.read_text(encoding='utf-8')
        for title in failure_titles(text):
            found += 1
            step = next((s for s in text.split('\n      - ')
                         if f'--resolve --title "{title}"' in s), None)
            assert step, f'{p.name}: nothing closes "{title}" when the run recovers'
            assert 'if: success()' in step and 'continue-on-error: true' in step, (
                f'{p.name}: the step closing "{title}" must run on success and never fail the run')
            raised_on = next(s for s in text.split('\n      - ')
                             if 'if: failure()' in s and f'--title "{title}"' in s)
            if "github.event_name == 'schedule'" in raised_on:
                assert "github.event_name == 'schedule'" in step, (
                    f'{p.name}: "{title}" is raised only by the nightly run, so only that run may close it')
    assert found >= 10, f'the scan found only {found} failure titles -- re-anchor it'


# --- Stage 83 item 1: a repeat failure counts instead of commenting ----------

RUN_A = 'https://github.com/o/r/actions/runs/111'
RUN_B = 'https://github.com/o/r/actions/runs/222'
AT = datetime(2026, 11, 4, 22, 40, tzinfo=UTC)


def report(run, finding='pypdf 6.19.0 has CVE-2026-113792'):
    """The shape of #540's comments: a sentence, a run link, a finding."""
    return f'pip-audit found known vulnerabilities.\n\nRun: {run}\n\n{finding}'


def posted(body, key=None):
    """A post as open_or_comment writes it."""
    return f"{body}\n\n<!-- alert-key: {alerts.report_key(key if key is not None else body)} -->"


def comment(body, cid=555):
    return {'body': body, 'url': f'https://github.com/o/r/issues/7#issuecomment-{cid}'}


def open7(**issue):
    return FakeGh(open_issues=[{'number': 7, 'title': 'Dependency audit found known vulnerabilities'}],
                  issue={'body': 'x', 'comments': [], **issue})


def raise_(gh, body, **kw):
    return alerts.open_or_comment('Dependency audit found known vulnerabilities', body, run=gh,
                                  now=lambda: AT, **kw)


def edited(gh):
    """The text of the one edit made: the PATCHed comment or the new issue body."""
    args, stdin = gh.calls[-1]
    return json.loads(stdin)['body'] if args[0] == 'api' else stdin


def test_a_repeat_of_the_latest_post_counts_on_it_instead_of_commenting():
    gh = open7(comments=[comment(posted(report(RUN_A)))])
    assert raise_(gh, report(RUN_B)) == ('counted', 7)
    assert gh.verbs() == ['issue list', 'issue view', 'api --method']
    args, _ = gh.calls[-1]
    assert args[args.index('--method') + 1] == 'PATCH'
    assert args[args.index('--method') + 2] == 'repos/{owner}/{repo}/issues/comments/555'
    text = edited(gh)
    assert text.startswith(posted(report(RUN_A))), 'the first report is kept as it was'
    assert text.endswith(f'Seen again with the same report once; the latest: {RUN_B} (2026-11-04 22:40 UTC).')


def test_the_count_climbs_on_one_line():
    gh = open7(comments=[comment(posted(report(RUN_A)))])
    raise_(gh, report(RUN_B))
    once = edited(gh)
    gh = open7(comments=[comment(once)])
    raise_(gh, report('https://github.com/o/r/actions/runs/333'))
    twice = edited(gh)
    assert twice.count('Seen again') == 1
    assert 'Seen again with the same report 2 times; the latest: https://github.com/o/r/actions/runs/333 ' in twice
    gh = open7(comments=[comment(twice)])
    raise_(gh, report(RUN_B))
    assert 'same report 3 times' in edited(gh)


def test_a_different_report_is_a_new_comment():
    gh = open7(comments=[comment(posted(report(RUN_A)))])
    assert raise_(gh, report(RUN_B, finding='pypdf 6.19.0 has CVE-2026-119204'))[0] == 'commented'
    assert gh.verbs()[-1] == 'issue comment'


def test_a_person_writing_after_the_alert_means_the_next_one_is_a_comment():
    """The count goes on the latest post only: an edit above a person's reply
    would be news no one sees."""
    gh = open7(comments=[comment(posted(report(RUN_A)), 1), comment('Looking at this tonight.', 2)])
    assert raise_(gh, report(RUN_B))[0] == 'commented'


def test_a_repeat_on_an_issue_with_no_comments_counts_on_its_body():
    gh = open7(body=posted(report(RUN_A)), comments=[])
    assert raise_(gh, report(RUN_B)) == ('counted', 7)
    assert gh.verbs()[-1] == 'issue edit'
    assert gh.calls[-1][0][2] == '7'
    assert 'same report once' in edited(gh)


def test_a_post_from_before_the_count_is_followed_by_a_comment():
    """#540's 23 comments carry no key; the next report after this ships is a
    comment that does, and the ones after that count on it."""
    gh = open7(comments=[comment(report(RUN_A))])
    assert raise_(gh, report(RUN_B))[0] == 'commented'


def test_a_comment_whose_id_cannot_be_read_is_not_edited():
    gh = open7(comments=[{'body': posted(report(RUN_A)), 'url': ''}])
    assert raise_(gh, report(RUN_B))[0] == 'commented'


def test_the_key_ignores_run_links_and_nothing_else():
    assert alerts.report_key(report(RUN_A)) == alerts.report_key(report(RUN_B))
    assert alerts.report_key(report(f'{RUN_A}/job/9')) == alerts.report_key(report(RUN_B))
    assert alerts.report_key(report(RUN_A)) != alerts.report_key(report(RUN_A, finding='pypdf 6.19.1'))
    assert alerts.report_key('Run 41 failed') != alerts.report_key('Run 42 failed')


def test_a_log_tail_that_differs_does_not_make_a_new_report():
    """The CLI keys on the report without its log, so a nightly failure whose
    log carries a new timestamp each run still counts."""
    gh = open7(comments=[comment(posted(report(RUN_A) + '\n\n22:40:01 boom', key=report(RUN_A)))])
    assert raise_(gh, report(RUN_B) + '\n\n22:41:07 boom', key=report(RUN_B))[0] == 'counted'
