"""Tests for the mutation runner's fixture subject.

These pass normally and are collected by the ordinary suite. Their purpose is
to give the runner's self-test something real to fail: one test that a
specific mutation breaks, and one unrelated test that the same mutation must
NOT break -- which is how WRONG-GUARD detection is proved.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from subject import is_positive, unguarded


def test_is_positive_says_yes_to_one():
    assert is_positive(1) is True


def test_is_positive_says_no_to_minus_one():
    """The unrelated guard. A mutation aimed at the one above must not be
    reported as caught by this."""
    assert is_positive(-1) is False


def test_unguarded_is_not_asserted_about():
    """Deliberately vacuous. `unguarded` has no behavioural test, so a
    mutation to it survives -- proving the runner can report SURVIVED."""
    assert callable(unguarded)
