"""
Two jobs: keep the mutation corpus from rotting, and prove the runner is honest.

WHY THE CORPUS NEEDS GUARDING

Running the mutations is expensive -- each is a pytest invocation -- so it is
an occasional command rather than part of this suite. But a corpus rots for
free: a refactor moves the line a case anchors to, the anchor stops matching,
and that case silently stops testing anything while still being counted in a
mutation table.

That is not hypothetical. While these cases still lived in throwaway scripts,
two anchors went stale in a single session -- one after a rename, one after a
parameter changed -- and both were noticed only because the script asserted its
own anchor count. These tests make that assertion permanent and free.

WHY THE RUNNER NEEDS GUARDING

A harness that reports CAUGHT unconditionally is worse than no harness: it
launders an untested guard into a confident table. So the runner is driven
against a fixture whose outcomes are known in advance, including the two ways
it must report failure -- a mutation nothing catches (SURVIVED), and one
caught by a different test than the case names (WRONG-GUARD).

That second one is the failure this repo has actually hit: a future-dated
release was caught by an ordering guard before the date guard could fire, so
the date guard passed while being entirely untested.

Run with: pytest tests/test_mutation_corpus.py -v
"""
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / 'tests' / 'mutation'))

import corpus as mc
import runner as mr

CASES = mc.load_corpus()
FIXTURE_SUBJECT = 'tests/mutation/selftest_fixtures/subject.py'
FIXTURE_TESTS = 'tests/mutation/selftest_fixtures/test_subject.py'


def _ids(cases):
    return [c['id'] for c in cases]


# --------------------------------------------------------------------------
# The corpus itself
# --------------------------------------------------------------------------

def test_the_corpus_is_not_empty():
    assert CASES, "no mutation cases -- the runner would pass trivially"


def test_case_ids_are_unique():
    dupes = mc.duplicate_ids()
    assert not dupes, f"duplicate case id(s): {dupes}"


@pytest.mark.parametrize('case', CASES, ids=_ids(CASES))
def test_every_anchor_still_matches_exactly_once(case):
    """Corpus rot, caught in the normal suite instead of the next time someone
    happens to run the mutations."""
    count, _find, _nl = mc.anchor_occurrences(case)
    assert count == 1, (
        f"{case['id']}: its anchor matches {count} time(s) in "
        f"{case['target']}. At 0 the mutation tests nothing and would be "
        f"reported BAD-ANCHOR; above 1 it would change more than intended.")


@pytest.mark.parametrize('case', CASES, ids=_ids(CASES))
def test_the_mutation_actually_changes_something(case):
    assert case['find'] != case['replace'], (
        f"{case['id']}: find and replace are identical, so this case applies "
        f"no mutation at all")


@pytest.mark.parametrize('case', CASES, ids=_ids(CASES))
def test_the_named_guard_exists(case):
    """A typo in expect_caught_by cannot be caught at run time -- it would just
    report WRONG-GUARD forever, looking like a real defect in the guard."""
    tests_file = REPO_ROOT / case['tests']
    assert tests_file.exists(), f"{case['id']}: no such test file {case['tests']}"
    src = tests_file.read_text(encoding='utf-8')
    assert re.search(rf'^def {re.escape(case["expect_caught_by"])}\(',
                     src, re.MULTILINE), (
        f"{case['id']}: {case['tests']} defines no test named "
        f"{case['expect_caught_by']!r}")


# --------------------------------------------------------------------------
# The runner's honesty
# --------------------------------------------------------------------------

def _fixture_case(**overrides):
    case = {
        'id': 'selftest',
        'why': 'runner self-test',
        'target': FIXTURE_SUBJECT,
        'tests': FIXTURE_TESTS,
        # Chosen so it flips exactly ONE of the fixture's two assertions:
        # is_positive(-1) becomes True (that test fails) while is_positive(1)
        # stays True (that one still passes). An earlier version used
        # `n >= 0`, which changes the answer for neither input -- an inert
        # mutation, which the runner correctly reported as SURVIVED and which
        # is exactly the sort of case that would silently pad a real corpus.
        'find': '    return n > 0',
        'replace': '    return n > -5',
        'expect_caught_by': 'test_is_positive_says_no_to_minus_one',
    }
    case.update(overrides)
    return case


def test_the_runner_reports_caught_when_a_guard_really_catches_it():
    r = mr.run_case(_fixture_case())
    assert r['status'] == mr.CAUGHT, r['detail']


def test_the_runner_reports_survived_when_nothing_catches_it():
    """The load-bearing self-test. A harness that cannot report failure turns
    every untested guard into a confident line in a mutation table."""
    r = mr.run_case(_fixture_case(
        find='    return n * 2',
        replace='    return n * 3',
        expect_caught_by='test_unguarded_is_not_asserted_about'))
    assert r['status'] == mr.SURVIVED, (
        f"a mutation nothing tests was not reported as surviving: {r}")


def test_the_runner_reports_wrong_guard_when_a_different_test_fires():
    """The failure this repo has actually hit: a mutation caught by a guard
    other than the one it was aimed at, leaving the intended guard untested
    while the table records a pass.

    Same mutation as the CAUGHT case, but attributed to the wrong test. The
    suite still goes red; the runner must not call that a pass.
    """
    r = mr.run_case(_fixture_case(
        expect_caught_by='test_unguarded_is_not_asserted_about'))
    assert r['status'] == mr.WRONG_GUARD, (
        f"a mutation caught by a different test than the case names was "
        f"reported as {r['status']}: {r['detail']}")
    assert 'test_is_positive_says_no_to_minus_one' in r['caught_by']


def test_the_runner_reports_a_stale_anchor_rather_than_a_pass():
    r = mr.run_case(_fixture_case(find='    return this line does not exist'))
    assert r['status'] == mr.BAD_ANCHOR, r


def test_the_runner_restores_the_file_byte_for_byte():
    """Every case mutates real committed source. A harness that leaves the
    tree dirty would be worse than the problem it solves."""
    target = REPO_ROOT / FIXTURE_SUBJECT
    before = target.read_bytes()
    mr.run_case(_fixture_case())
    assert target.read_bytes() == before, (
        f"{FIXTURE_SUBJECT} was not restored byte-for-byte after a mutation")


def test_the_runner_restores_even_when_the_mutation_survives():
    """The restore is in a finally block for a reason -- the failure paths are
    exactly when a dirty tree would be least expected and most damaging."""
    target = REPO_ROOT / FIXTURE_SUBJECT
    before = target.read_bytes()
    mr.run_case(_fixture_case(find='    return n * 2', replace='    return n * 3',
                              expect_caught_by='test_unguarded_is_not_asserted_about'))
    assert target.read_bytes() == before


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
