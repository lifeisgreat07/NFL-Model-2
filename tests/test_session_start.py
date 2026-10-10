"""`src/agents/session_start.py` -- the orientation tool, and its one honesty rule.

It exists because every staleness failure here has been a derivable fact typed
by hand. So the thing worth guarding is not its formatting, it is the promise
that everything it prints was computed: if it ever starts *asserting* something
it cannot check -- a pull-request status above all -- it becomes another source
of confident, unverified claims, which is the failure it was built to remove.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / 'src' / 'agents' / 'session_start.py'


@pytest.fixture(scope='module')
def output():
    # Both ends of the pipe are pinned to UTF-8, and neither may be left to
    # the platform default. session_start prints docs/context.md verbatim and
    # that file is full of em dashes; on Windows the child encoded its stdout
    # as cp1252 and this end decoded it the same way, so every line carrying
    # one came back mangled and the comparison below failed -- but ONLY when
    # the suite was itself a subprocess of another Python process, which is
    # exactly how src/agents/scout_preflight.py runs it. Run directly the suite was
    # green, so the red was invisible where anyone would look for it, and
    # preflight reported the resulting count as a STALE FIGURE rather than as
    # a failure. Two defects, one root cause; this is the root cause.
    #
    # --offline: the suite never reads GitHub. The online section is tested
    # below with a fake API (github_state's `get`), not the real one.
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    r = subprocess.run([sys.executable, str(SCRIPT), '--skip-tests', '--offline'],
                       cwd=REPO, capture_output=True, text=True,
                       encoding='utf-8', env=env)
    assert r.returncode == 0, (
        f"session_start exited {r.returncode}. It is an orientation tool, not a "
        f"gate -- session_wrapup.py is the gate -- so it must never block a "
        f"session that is only trying to find out where it is.\n{r.stderr}")
    return r.stdout


def test_it_reports_the_branch_git_actually_reports(output):
    """The cheapest possible proof that it read the repository rather than
    printing something plausible."""
    branch = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                            cwd=REPO, capture_output=True, text=True).stdout.strip()
    assert branch in output, f"the tool does not name the current branch ({branch})"


def test_it_reads_the_documented_suite_count_from_claude_md(output):
    claimed = re.search(r'Suite:\s*\*\*([0-9,]+)\s+passing\*\*',
                        (REPO / 'CLAUDE.md').read_text(encoding='utf-8'))
    assert claimed, "CLAUDE.md no longer states a suite count for it to read"
    assert claimed.group(1) in output


def test_it_points_at_the_reading_order(output):
    """Read in the "Read next" list only. The whole output also carries
    docs/context.md verbatim, so any document that file happens to mention
    would satisfy a whole-output search with the list itself gone."""
    assert 'Read next' in output, "the output no longer has a 'Read next' list"
    reading = output.split('Read next', 1)[1]
    for doc in ('CLAUDE.md', 'docs/traps.md', 'docs/index.md', 'memory/'):
        assert doc in reading, f"the reading order no longer mentions {doc}"
    assert 'docs/context.md' in output, "the output never mentions docs/context.md"


def test_it_prints_the_context_file_rather_than_pointing_at_it(output):
    """One command should leave you knowing where things stand, not holding a
    reading list. context.md is capped at one screen for exactly this reason,
    so pointing at it was a pointless extra step.

    Checked by content, not by a heading: a section header saying it printed
    the file is precisely the sort of claim that outlives the behaviour.
    """
    context = (REPO / 'docs' / 'context.md').read_text(encoding='utf-8')
    substantive = [l.strip() for l in context.splitlines()
                   if l.strip() and not l.startswith('#') and len(l.strip()) > 40]
    assert substantive, "docs/context.md has no substantive lines to check against"
    missing = [l for l in substantive if l not in output]
    assert not missing, (
        f"{len(missing)} line(s) of docs/context.md are not in the output, so "
        f"the file is being referenced rather than shown. First: {missing[0][:80]!r}")


def test_it_does_not_print_claude_md_in_full(output):
    """The other half of that decision. CLAUDE.md is ~430 lines and mostly
    durable; dumping it every session would bury the twenty lines that changed
    under the four hundred that did not."""
    claude = (REPO / 'CLAUDE.md').read_text(encoding='utf-8')
    long_lines = [l.strip() for l in claude.splitlines() if len(l.strip()) > 60]
    hits = sum(1 for l in long_lines[:200] if l in output)
    assert hits < 10, (
        f"{hits} lines of CLAUDE.md appear in the output; it is meant to be "
        f"pointed at, not printed")


def test_it_refuses_to_state_pull_request_status(output):
    """The honesty rule, and the only one worth failing a build over.

    There is no `gh` CLI on this machine. Since Stage 49 item 21 the tool
    READS pull-request state from GitHub's public API; offline it cannot, so
    it must say so rather than print a status it cannot verify. The fixture
    runs --offline, so the disclaimer has to survive there, and keep saying why.
    """
    assert 'Pull-request state is NOT shown' in output, (
        "the tool no longer disclaims pull-request state. Either it has started "
        "claiming something it cannot check, or the disclaimer was dropped -- "
        "both leave a reader believing a status nobody verified")
    assert 'gh' in output, "the disclaimer no longer says WHY it cannot show PR state"


def test_the_stale_threshold_is_stated_as_a_judgement_not_a_measurement():
    """A magic number in a tool that judges staleness is itself a claim. It is
    three days because that survives a weekend, and the source says so rather
    than leaving the next reader to reverse-engineer it."""
    src = SCRIPT.read_text(encoding='utf-8')
    assert 'CONTEXT_STALE_DAYS' in src
    assert 'judgement, not a measurement' in src, (
        "the staleness threshold lost the comment explaining that it is a "
        "choice rather than something measured")


def test_the_wrapup_survives_a_detached_head_that_is_actually_pushed():
    """Booth's audit sandbox checks a PR out detached, and `session_wrapup.py`
    told it "commits exist only on this machine" about a commit that was sitting
    on origin under a branch name. The check's real question is whether the
    commit reached the remote, so it asks that rather than inferring it from a
    tracking branch -- which a detached checkout never has.

    Verified against this repository's own history rather than a fixture: any
    commit already on a remote branch must not be reported as unpushed.
    """
    src = (REPO / 'src' / 'agents' / 'session_wrapup.py').read_text(encoding='utf-8')
    assert "'branch', '-r', '--contains'" in src, (
        "check_nothing_unpushed no longer asks whether the commit is on a "
        "remote branch, so a detached checkout is reported as unpushed again")

    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO,
                          capture_output=True, text=True).stdout.strip()
    on_remote = subprocess.run(['git', 'branch', '-r', '--contains', head],
                               cwd=REPO, capture_output=True, text=True).stdout.strip()
    if not on_remote:
        pytest.skip('HEAD is not on a remote branch, so there is nothing to prove here')

    # The FUNCTION, not the script. Running session_wrapup.py as a subprocess
    # from inside the suite is the recursion its own docstring warns about --
    # it runs pytest, which runs this test, which runs it again. The first
    # draft of this test did exactly that and had to be killed.
    from src.agents import session_wrapup
    result = session_wrapup.check_nothing_unpushed()
    assert result.ok, (
        f"HEAD is on {on_remote.splitlines()[0].strip()} yet check_nothing_unpushed "
        f"reports: {result.detail}")


def test_the_date_checks_say_they_are_expected_at_session_start():
    """These two fail every morning by design -- the context file and the
    memory entry are written at the END of a session, so a fresh one starts
    with both red. Booth read that as a discrepancy against a PR claiming six
    passing checks, which is a fair reading of an unexplained failure.

    The failure text now says which kind of failure it is. A check that cannot
    be told apart from a regression will eventually be ignored like one.
    """
    src = (REPO / 'src' / 'agents' / 'session_wrapup.py').read_text(encoding='utf-8')
    assert src.count('EXPECTED at the start of a session') >= 2, (
        "the date-based checks no longer explain that failing at session start "
        "is the mechanism working rather than something being broken")


def test_the_wrapup_and_start_scripts_read_the_same_count_line():
    """They are two halves of one ritual. If they parsed CLAUDE.md's suite line
    differently, one could pass while the other failed on the same file --
    which is worse than either being wrong on its own."""
    start = SCRIPT.read_text(encoding='utf-8')
    wrap = (REPO / 'src' / 'agents' / 'session_wrapup.py').read_text(encoding='utf-8')
    pattern = r"COUNT_RE = re\.compile\((r'[^']+')\)"
    a = re.search(pattern, start)
    b = re.search(pattern, wrap)
    assert a and b, "one of the scripts no longer defines COUNT_RE"
    assert a.group(1) == b.group(1), (
        f"session_start and session_wrapup parse CLAUDE.md's suite line "
        f"differently:\n  start: {a.group(1)}\n  wrap:  {b.group(1)}")


# ------------------------------------------- the GitHub section (Stage 49 item 21)

def _session_start():
    sys.path.insert(0, str(REPO))
    from src.agents import session_start
    return session_start


def _run(event, start, conclusion='success'):
    return {'event': event, 'run_started_at': start, 'created_at': start,
            'status': 'completed', 'conclusion': conclusion}


def _fake_api(runs_by_workflow, pulls=(), issues=()):
    def get(url):
        if '/actions/workflows/' in url:
            wf = url.split('/actions/workflows/')[1].split('/')[0]
            return {'workflow_runs': runs_by_workflow.get(wf, [])}
        if '/pulls?' in url:
            return list(pulls)
        if '/issues?' in url:
            return list(issues)
        raise AssertionError(f'unexpected URL {url}')
    return get


NOW = '2026-10-05T16:00:00Z'


def test_a_schedule_run_after_a_requested_one_is_named_githubs_late_copy():
    """The 2026-10-05 canary: requested 06:00:52 by cron-job.org, GitHub's
    own copy 13:15:19. A session checking the slot must see which is which."""
    ss = _session_start()
    lines = ss.run_lines([_run('schedule', '2026-10-05T13:15:19Z'),
                          _run('workflow_dispatch', '2026-10-05T06:00:52Z')],
                         'Nightly data check', ss._utc(NOW))
    assert len(lines) == 2
    assert 'requested' in lines[0] and 'late copy' not in lines[0], "oldest first, the request"
    assert 'schedule' in lines[1] and "GitHub's late copy, 7h14m" in lines[1]


def test_a_schedule_run_with_no_request_before_it_is_not_called_a_copy():
    """The Weekly update has no cron-job.org job yet: its schedule run is the slot."""
    ss = _session_start()
    lines = ss.run_lines([_run('schedule', '2026-10-05T11:00:00Z')], 'NFL weekly update', ss._utc(NOW))
    assert len(lines) == 1 and 'late copy' not in lines[0]


def test_runs_outside_the_window_are_left_out_and_an_empty_window_says_so():
    ss = _session_start()
    old = _run('workflow_dispatch', '2026-10-03T06:00:00Z')
    lines = ss.run_lines([old], 'Nightly data check', ss._utc(NOW))
    assert lines == [f'  {"Nightly data check":<26} no run in the last {ss.RUN_WINDOW_HOURS} hours']


def test_the_section_names_its_source_and_every_watched_job(capsys):
    ss = _session_start()
    from src.sports.nfl.recent_runs import WATCHED
    get = _fake_api(
        {'nfl-nightly-canary.yml': [_run('workflow_dispatch', '2026-10-05T06:00:52Z')]},
        pulls=[{'number': 290, 'title': 'QB overrides: 2026 week 5', 'state': 'open',
                'merged_at': None, 'created_at': '2026-10-05T22:06:00Z',
                'head': {'ref': 'qb-overrides-2026-week5'}}],
        issues=[{'number': 300, 'title': 'Model drift detected', 'created_at': '2026-10-06T12:00:00Z'},
                {'number': 290, 'title': 'a pull request', 'created_at': 'x', 'pull_request': {}}])
    ss.github_state(get=get, now=ss._utc(NOW))
    out = capsys.readouterr().out
    assert 'read from the public API at 2026-10-05 16:00 UTC' in out
    for shown in WATCHED.values():
        assert shown in out, f'{shown} is missing from the unattended jobs'
    assert '#290 QB overrides: 2026 week 5' in out and 'open' in out
    assert '#300 Model drift detected' in out
    assert 'a pull request --' not in out, 'the issues list must not repeat pull requests'


def test_every_daily_sport_workflow_on_a_schedule_is_watched():
    """The NHL's and NBA's unattended jobs reach a session through the one
    list, recent_runs.WATCHED (Stage 68 item 12), and the session reads no
    second one. A new scheduled workflow left out of it would run unseen."""
    ss = _session_start()
    from src.sports.nfl.recent_runs import WATCHED
    folder = Path(__file__).parents[1] / '.github' / 'workflows'
    scheduled = {p.name for s in ('nhl', 'nba') for p in folder.glob(f'{s}-*.yml')
                 if 'schedule:' in p.read_text(encoding='utf-8')}
    assert len(scheduled) == 4 and scheduled <= set(WATCHED)
    assert not hasattr(ss, 'SPORT_WATCHED')


def test_a_failed_read_is_reported_and_does_not_raise(capsys):
    """An orientation tool must not die because GitHub was slow or the
    anonymous limit was spent: it says it could not read, and goes on."""
    ss = _session_start()

    def get(url):
        raise OSError('rate limited')
    ss.github_state(get=get, now=ss._utc(NOW))
    out = capsys.readouterr().out
    assert 'COULD NOT READ GitHub (OSError: rate limited)' in out


def test_the_suite_never_reads_github():
    """Every subprocess run of the tool in this file passes --offline: a test
    that reads the live API is slow, spends the anonymous limit Booth's
    runner shares, and fails for reasons that are not the code's."""
    src = Path(__file__).read_text(encoding='utf-8')
    runs = re.findall(r'subprocess\.run\(\[sys\.executable, str\(SCRIPT\)[^\]]*\]', src)
    assert runs, 'no subprocess run of session_start found to check'
    assert all("'--offline'" in r for r in runs), runs


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))


def test_it_survives_a_stdout_that_cannot_encode_the_context_file():
    """The orientation tool must not die on the contents of the file it shows.

    session_start prints docs/context.md verbatim. On Windows a REDIRECTED
    stdout defaults to cp1252, which has no arrow -- so on 2026-09-12 a single
    '->' typed as a real arrow in a DOCUMENT crashed the first command of the
    session with a UnicodeEncodeError, partway through printing, after several
    screens of correct output. The document was fine; the tool was not.

    The module fixture above pins PYTHONIOENCODING=utf-8 at both ends, which
    is precisely why it could never catch this: it is more careful than the
    environment it stands in for. This test does the opposite on purpose --
    it forces the narrowest plausible encoding and asserts the tool still
    exits cleanly.

    Guarding the tool rather than the document is the deliberate choice. A
    rule saying "no typographic characters in context.md" would be one more
    thing to remember, enforced by nothing, in a file anyone may edit.
    """
    env = {**os.environ, 'PYTHONIOENCODING': 'cp1252'}
    r = subprocess.run([sys.executable, str(SCRIPT), '--skip-tests', '--offline'],
                       cwd=REPO, capture_output=True, env=env)

    assert b'UnicodeEncodeError' not in r.stderr, (
        'session_start.py died encoding its own output. It must reconfigure '
        'stdout rather than inherit a code page that cannot represent '
        'docs/context.md:\n' + r.stderr.decode('ascii', 'replace')[-600:])
    assert r.returncode == 0, (
        f'exit {r.returncode} under PYTHONIOENCODING=cp1252; it exits 0 '
        f'always by design:\n' + r.stderr.decode('ascii', 'replace')[-600:])
    # It must not bail early and call that success: the context file is the
    # last thing printed, so reaching the footer proves it got all the way.
    assert b'Read next' in r.stdout, (
        'exited 0 without reaching the end of its own output')
