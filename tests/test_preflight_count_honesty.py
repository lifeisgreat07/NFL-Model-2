"""Two ways scout_preflight could be wrong about a suite count, and one it was.

The one it was: `run_test_suite` read the passed figure and nothing else, so
a RED suite was reported in the words of the staleness failure -- "the body
claims N but a real run gives N-1" -- which names a cause that is not the
cause and sends the reader to edit the description instead of to the broken
test. CLAUDE.md had already recorded that defect for session_wrapup.py.
Recording it in one tool did not fix it in the other, which is the argument
for a test rather than a second entry.

The one it could not catch at all: a suite count in a COMMIT MESSAGE. A PR
body is editable and re-checked on every synchronize; a commit message is
fixed at the moment of writing, because amending it rewrites its SHA and
invalidates every Booth report referencing that SHA. Three of the four
discrepancies across PR #60's audits were counts in commit messages that were
correct when written and were falsified by the base moving. The only possible
guard is before the commit exists.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import scout_preflight as sp  # noqa: E402


# --- a red suite must not be described as a stale figure ---

def test_a_red_suite_is_reported_as_red(monkeypatch):
    """The exact scenario that cost a day: one test failing, the rest green."""
    monkeypatch.setattr(sp, 'run_test_suite', lambda: (893, 1, None))
    f = sp.check_test_count('the suite is 894 passed here', skip_tests=False)

    assert not f.ok
    assert 'RED' in f.detail, f.detail
    assert 'PR #21' not in f.detail, (
        'a red suite is being reported in the words of the staleness failure. '
        'That names a cause which is not the cause and sends the reader to '
        'the description instead of to the broken test: ' + f.detail)


def test_a_red_suite_is_reported_even_when_the_claimed_number_matches():
    """The nastier half. If the body happens to quote the passed figure of a
    red run, comparing counts alone reports PASS on a broken suite -- the
    check silently agreeing with a number taken from a run that failed."""
    import types
    sp_broken = types.SimpleNamespace()
    sp_broken.run = lambda: (893, 1, None)
    original = sp.run_test_suite
    try:
        sp.run_test_suite = sp_broken.run
        f = sp.check_test_count('exactly 893 passed', skip_tests=False)
    finally:
        sp.run_test_suite = original

    assert not f.ok, (
        'the body quoted the passed count of a RED run and the check agreed '
        'with it. A matching number is not a green suite.')


def test_a_green_suite_still_compares_the_claimed_count(monkeypatch):
    """The original behaviour has to survive the fix."""
    monkeypatch.setattr(sp, 'run_test_suite', lambda: (894, 0, None))
    assert sp.check_test_count('894 passed, 1 skipped', skip_tests=False).ok
    stale = sp.check_test_count('876 passed', skip_tests=False)
    assert not stale.ok and 'PR #21' in stale.detail


def test_the_summary_parser_reads_real_pytest_output():
    """Against the shapes pytest actually prints, not an invented one.

    These four lines are transcribed from real runs in this repository: a
    green suite, the red one that started all this, an all-errors run where
    the fixture blew up at setup, and a run with both.

    It is a separate function from run_test_suite() precisely so it can be
    tested: run_test_suite shells out, so every test that stubs it stubs the
    parsing too -- which is why the defect lived here unnoticed while the
    file's other checks were well covered.
    """
    green = '894 passed, 1 skipped, 10 warnings in 41.77s'
    red = '1 failed, 893 passed, 1 skipped, 10 warnings in 39.15s'
    errored = '5 errors in 0.15s'
    both = '2 failed, 3 errors, 100 passed in 1.00s'

    assert sp.parse_suite_summary(green) == (894, 0)
    assert sp.parse_suite_summary(red) == (893, 1)
    assert sp.parse_suite_summary(both) == (100, 5)
    assert sp.parse_suite_summary(errored) == (None, None), (
        'a run with no passed count at all cannot report a number; it has to '
        'say the suite could not be run')
    assert sp.parse_suite_summary('') == (None, None)


# --- a suite count in a commit message ---

def test_a_count_in_a_commit_message_is_rejected(monkeypatch):
    monkeypatch.setattr(sp, 'branch_commit_messages', lambda base, head: [
        ('abc1234', 'Add a guard',
         'Add a guard\n\nBody text.\n\nSuite: 751 passing, 1 skipped\n')])
    f = sp.check_no_suite_count_in_a_commit_message('main', 'HEAD')

    assert not f.ok
    assert 'abc1234' in f.detail, 'the offending commit is not named'
    assert 'cannot be corrected' in f.detail


def test_a_quoted_count_in_a_commit_message_is_allowed(monkeypatch):
    """Use versus mention, and the reason it has to be allowed.

    A commit that FIXES this defect has to be able to say which number was
    wrong. A rule worded to dodge its own checker is the mistake this repo
    has made three times; stripping quotation is the principled version, and
    it is what the body checks already do.
    """
    monkeypatch.setattr(sp, 'branch_commit_messages', lambda base, head: [
        ('def5678', 'Correct a stale trailer',
         'Correct a stale trailer\n\nThe trailer said "751 passing" and the '
         'branch had been rebased since.\n')])
    assert sp.check_no_suite_count_in_a_commit_message('main', 'HEAD').ok


def test_ordinary_english_about_tests_passing_is_not_forbidden(monkeypatch):
    """The floor this rule must not cross.

    A guard that cries wolf earns an allowlist entry and then gets ignored,
    which is worse than no guard -- already a trap entry here, written after
    a jargon check banned a term and missed its abbreviation. Two digits is
    the line: this repository's totals are in the hundreds.
    """
    monkeypatch.setattr(sp, 'branch_commit_messages', lambda base, head: [
        ('0000aaa', 'Fix the loader',
         'Fix the loader\n\nAll 3 tests still pass, and the new guard passes '
         'its own mutation case.\n')])
    assert sp.check_no_suite_count_in_a_commit_message('main', 'HEAD').ok


def test_the_commit_message_check_survives_skip_tests():
    """--skip-tests exists so CI need not re-run a suite another job ran. It
    must not disable a check that reads git log and costs nothing -- and this
    is the one check whose subject can never be corrected afterwards, so it is
    exactly the one that has to run everywhere."""
    findings, _ = sp.preflight('a body', base='HEAD', skip_tests=True,
                               head='HEAD')
    names = [f.check for f in findings]
    assert 'no count in a commit message' in names, names
