"""`src/session_start.py` -- the orientation tool, and its one honesty rule.

It exists because every staleness failure here has been a derivable fact typed
by hand. So the thing worth guarding is not its formatting, it is the promise
that everything it prints was computed: if it ever starts *asserting* something
it cannot check -- a pull-request status above all -- it becomes another source
of confident, unverified claims, which is the failure it was built to remove.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / 'src' / 'session_start.py'


@pytest.fixture(scope='module')
def output():
    r = subprocess.run([sys.executable, str(SCRIPT), '--skip-tests'],
                       cwd=REPO, capture_output=True, text=True)
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
    for doc in ('docs/context.md', 'CLAUDE.md', 'docs/index.md', 'memory/'):
        assert doc in output, f"the reading order no longer mentions {doc}"


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
    """The other half of that decision. CLAUDE.md is ~900 lines and mostly
    durable; dumping it every session would bury the twenty lines that changed
    under the eight hundred that did not."""
    claude = (REPO / 'CLAUDE.md').read_text(encoding='utf-8')
    long_lines = [l.strip() for l in claude.splitlines() if len(l.strip()) > 60]
    hits = sum(1 for l in long_lines[:200] if l in output)
    assert hits < 10, (
        f"{hits} lines of CLAUDE.md appear in the output; it is meant to be "
        f"pointed at, not printed")


def test_it_refuses_to_state_pull_request_status(output):
    """The honesty rule, and the only one worth failing a build over.

    There is no `gh` CLI on this machine, so the tool cannot know whether a PR
    is open, merged or audited. If someone later teaches it to print a status
    it cannot verify, this catches it: the disclaimer has to survive, and it
    has to keep saying why.
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


def test_the_wrapup_and_start_scripts_read_the_same_count_line():
    """They are two halves of one ritual. If they parsed CLAUDE.md's suite line
    differently, one could pass while the other failed on the same file --
    which is worse than either being wrong on its own."""
    start = SCRIPT.read_text(encoding='utf-8')
    wrap = (REPO / 'src' / 'session_wrapup.py').read_text(encoding='utf-8')
    pattern = r"COUNT_RE = re\.compile\((r'[^']+')\)"
    a = re.search(pattern, start)
    b = re.search(pattern, wrap)
    assert a and b, "one of the scripts no longer defines COUNT_RE"
    assert a.group(1) == b.group(1), (
        f"session_start and session_wrapup parse CLAUDE.md's suite line "
        f"differently:\n  start: {a.group(1)}\n  wrap:  {b.group(1)}")


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
