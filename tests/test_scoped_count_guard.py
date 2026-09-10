"""The scoped-count check catches the sentence that actually shipped.

Booth has now found the same defect shape three times in one day, on three
different PRs:

  #51 claim 17  "--shadow-sm/md/lg still used in ten places"
                -- 9 token references, 10 box-shadow declarations
  #52 claim  5  "seven pairs sit between 14.9 and 15.25"
                -- the script printed nine; seven was read by eye off a
                   wider band that had been printed for a different purpose
  #54 claim  4  "test_workflow_churn_guard.py ... its 31 tests still pass"
                -- that file has 3; 31 was the true total of a three-file
                   run (3 + 20 + 8) quoted against a sentence about one file

The shape is one thing, and it is worth naming precisely because "be more
careful" does not describe it: **a number that is real output from a command
whose scope is not the sentence's scope.** Not one of the three was invented.
That is exactly why re-reading does not catch them -- the author remembers
running the command and getting the number, so it feels verified. The
unverified part is the attribution, and attribution is invisible to the person
who did the attributing.

Only the third is mechanically decidable in general, so that is the one
`check_scoped_test_counts` closes. The other two are covered by the rule the
docs now carry: put the command next to the number.

The first test below uses the failing sentence verbatim. If this file ever
stops catching it, the guard has rotted.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / 'src'))

from scout_preflight import check_scoped_test_counts, collected_count  # noqa: E402

# Verbatim from PR #54's description, as Booth found it.
THE_SENTENCE_THAT_SHIPPED = (
    "Confirmed this does not disturb the existing guard: "
    "`test_workflow_churn_guard` selects workflows that both regenerate *and* "
    "carry a `file_pattern`, so the new workflow is correctly outside its "
    "scope; its 31 tests still pass."
)


def test_it_catches_the_sentence_that_actually_shipped():
    f = check_scoped_test_counts(THE_SENTENCE_THAT_SHIPPED, skip_tests=False)
    assert not f.ok, (
        "the scoped-count check passed the exact sentence Booth flagged on "
        "PR #54 -- it is guarding nothing")
    assert 'test_workflow_churn_guard' in f.detail
    assert '31' in f.detail


def test_the_corrected_sentence_passes():
    """The fix must not be 'never mention a count beside a file name'."""
    real = collected_count('test_workflow_churn_guard')
    assert real is not None, "test_workflow_churn_guard.py is missing"
    body = (f"The new workflow is outside that guard's scope; "
            f"`test_workflow_churn_guard` has {real} tests and all pass.")
    assert check_scoped_test_counts(body, skip_tests=False).ok


def test_a_body_with_no_scoped_count_is_not_flagged():
    body = ("This PR adds a workflow and a test. The suite is 730 passing, "
            "1 skipped. Nothing else changed.")
    assert check_scoped_test_counts(body, skip_tests=False).ok


def test_quoted_output_is_not_treated_as_an_assertion():
    """Fenced blocks are quotation. Pasting a real run, or quoting the
    mistake to explain it, must not fail the check that explains it -- the
    same principle check_test_count already follows."""
    body = ("Correcting the earlier claim:\n\n"
            "```\n`test_workflow_churn_guard` -- 31 tests\n```\n\n"
            "The real figure is below.")
    assert check_scoped_test_counts(body, skip_tests=False).ok


def test_a_quoted_past_mistake_in_a_table_cell_is_not_an_assertion():
    """Booth ran this tool against the PR that shipped it, and it failed.

    That body explained the #54 defect in a markdown table -- neither a fenced
    block nor a blockquote, so the module name and the wrong number landed in
    one unstripped sentence and the guard fired on the correction rather than
    the error. A check against misquoted numbers that forbids quoting a
    misquoted number is not usable, so quotation marks now count as quotation.

    The row below is the one that tripped it, verbatim -- and the ellipsis is
    U+2026, not three periods, which is not a detail. An earlier draft of this
    test typed "..." instead. SENTENCE_SPLIT_RE breaks on a period, so the
    module name and the count fell into different sentences, the check never
    paired them, and the test passed no matter what strip_quotations did. The
    mutation corpus caught it: preflight-quote-marks-not-stripped SURVIVED
    against that draft. A test that passes for a reason unrelated to its name
    is worse than no test, and this one is one character away from being that.
    """
    row = ('| #54 claim 4 | "`test_workflow_churn_guard.py` … its 31 tests '
           'still pass" | 3 -- the 31 was a three-file run, 3 + 20 + 8 |')
    assert '…' in row and '...' not in row, (
        "the ellipsis was replaced with periods -- see this test's docstring; "
        "that change silently disarms it")
    assert check_scoped_test_counts(row, skip_tests=False).ok, (
        "quoting a past miscount to correct it still trips the guard")


def test_stripping_quotes_does_not_blind_the_check_inside_a_table():
    """The narrow fix has to stay narrow. Exempting whole table ROWS would
    blind the check where this repo most often puts real claims -- its
    verification tables. An unquoted false count in a table must still fail."""
    row = "| The new guard | `test_scoped_count_guard` | 99 tests passing |"
    assert not check_scoped_test_counts(row, skip_tests=False).ok, (
        "a table cell asserting a wrong count went unchecked")


def test_an_unpaired_quote_does_not_swallow_the_document():
    """A bounded, newline-free span, so stray quote marks cannot silently
    disable every check between them.

    The body below needs TWO quote marks with the claim between them. An
    earlier draft used one, which no regex can pair, so nothing was stripped
    under either version and the test passed vacuously -- the corpus caught
    that too (preflight-quote-span-unbounded SURVIVED). With a multiline,
    unbounded span the two marks below pair across the newlines and swallow
    the false claim; with the shipped newline-free one they cannot.
    """
    body = ('A note that opens a quote "here and never closes it on this line.\n'
            '`test_scoped_count_guard` has 99 tests.\n'
            'Then later some "other quoted thing" appears.')
    assert body.count('"') >= 2, "this test needs two quote marks to be meaningful"
    assert not check_scoped_test_counts(body, skip_tests=False).ok, (
        "quote marks on different lines swallowed the claim between them")


def test_an_unknown_module_is_ignored_rather_than_failed():
    """A body may discuss a test file that does not exist yet -- a plan, or a
    file a later phase adds. That is not a false claim about this branch."""
    body = "Phase 2 adds `test_not_written_yet` with 4 tests."
    assert check_scoped_test_counts(body, skip_tests=False).ok


def test_skip_tests_does_not_disable_it():
    """--skip-tests exists because running the whole suite is slow. Collection
    is a parse, so there is no reason to skip it, and skipping it would have
    let this exact defect through in CI."""
    f = check_scoped_test_counts(THE_SENTENCE_THAT_SHIPPED, skip_tests=True)
    assert not f.ok, "--skip-tests silently disabled the scoped-count check"


# Deliberately this very file. An earlier draft used a module that existed only
# on the branch it was written on, so the parametrized cases passed there and
# failed the moment the work moved to a branch off main -- a test coupled to
# another branch's contents. A file is always present alongside itself, and 99
# is never its real count.
@pytest.mark.parametrize('phrasing', [
    "`test_scoped_count_guard` has 99 tests",
    "tests/test_scoped_count_guard.py -- 99 tests",
    "`test_scoped_count_guard.py`: 99 tests, all passing",
    "we added 99 tests to `test_scoped_count_guard`",
])
def test_it_catches_both_word_orders_and_path_forms(phrasing):
    """The count comes before the file as often as after it."""
    assert not check_scoped_test_counts(phrasing, skip_tests=False).ok, (
        f"not caught: {phrasing!r}")


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
