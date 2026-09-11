"""No test may gate itself on the built artifact at COLLECTION time.

The hole this closes, found on 2026-09-11 while verifying an unrelated audit
finding by running the suite in a fresh git worktree:

  SKIPPED tests/test_accuracy_empty_states.py:112: index.html not built

That test carried `@pytest.mark.skipif(not BUILT.exists(), ...)`. pytest
evaluates a skipif condition at collection time, which is strictly BEFORE any
fixture runs -- so the root conftest's session build cannot satisfy it. While
index.html was committed the condition was always False and the decorator was
harmless. PR #58 untracked the file, and from that moment the test skipped on
every fresh checkout.

It never showed up locally, because a developer machine almost always has an
index.html lying around from an earlier build, so the condition is False there
and the test runs. CI checks out clean every time and has no such file. The
suite reported green in both places while quietly running one fewer assertion
in the one that matters.

Two things make this worth a structural guard rather than a one-line fix:

  * `tests/test_build_artifacts_exist.py` cannot catch it. That file asserts
    the conftest built the page, and the conftest did. The artifact exists;
    the decorator simply asked too early. A guard aimed at the build cannot
    see a timing bug in a collection-time predicate.
  * It is the exact failure mode PR #58 existed to eliminate -- a guard that
    turns into a green skip instead of a red failure -- surviving inside the
    change that eliminated it everywhere else.

So the rule is mechanical: a test that needs the built page asserts inside its
body, where the fixture has already run. It does not ask at import time.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / 'tests'

#: Names the tests use for the generated page and the printable-picks
#: directory. A collection-time predicate mentioning one of these is the
#: defect; mentioning anything else is somebody else's business.
ARTIFACT_TOKENS = ('index.html', "BUILT", 'DIST', 'dist')

#: Decorator forms pytest evaluates while collecting, before fixtures run.
COLLECTION_TIME = re.compile(
    r'@pytest\.mark\.skipif\((?P<cond>[^\n]*)\)'
    r'|pytestmark\s*=\s*pytest\.mark\.skipif\((?P<cond2>[^\n]*)\)')


def _test_files():
    """Every test module except this one.

    Excluded in the parametrize list rather than skipped inside the test,
    deliberately. A skip would be honest but it would also add a skipped case
    to a suite whose whole subject here is that a skip reads as green. This
    file has to spell the forbidden tokens out in order to forbid them, which
    is a property of the guard, not a finding about it.
    """
    return sorted(p for p in TESTS.glob('test_*.py')
                  if p.name != Path(__file__).name)


def _code_only(text):
    """Source with docstrings and comment lines removed.

    Necessary, and found the usual way: the first version of this guard
    flagged the very test it was written to fix, because that test's new
    docstring QUOTES the decorator it no longer carries in order to explain
    why. A guard that cannot tell a use from a mention forbids explaining the
    defect, which is the same mistake as wording a rule to dodge its own
    checker. This suite already hit it once, on the verify_model_colours
    shading guard.
    """
    text = re.sub(r'"""(?:.|\n)*?"""', '', text)
    text = re.sub(r"'''(?:.|\n)*?'''", '', text)
    return '\n'.join(ln for ln in text.splitlines()
                     if not ln.lstrip().startswith('#'))


@pytest.mark.parametrize('path', _test_files(), ids=lambda p: p.name)
def test_no_skipif_gates_on_the_built_artifact(path):
    text = _code_only(path.read_text(encoding='utf-8'))
    for m in COLLECTION_TIME.finditer(text):
        cond = m.group('cond') or m.group('cond2') or ''
        hit = next((t for t in ARTIFACT_TOKENS if t in cond), None)
        if hit:
            raise AssertionError(
                f'{path.name} gates on the built artifact at '
                f'collection time:\n    {m.group(0).strip()}\n'
                'pytest evaluates that condition BEFORE the root conftest '
                'builds the page, so on a fresh checkout -- which is what CI '
                'does -- the test skips and the suite still reports green. '
                'Assert inside the test body instead, where the build has '
                'already happened, so a missing page is a failure.')


def test_the_guard_would_notice_the_defect_it_was_written_for():
    """The shape that actually shipped, checked against this file's own regex.

    Without this, the test above passes on a repository that has no skipif
    left at all -- which is the state it is meant to maintain, and therefore
    indistinguishable from a regex that matches nothing.
    """
    shipped = ("@pytest.mark.skipif(not BUILT.exists(), "
               "reason='index.html not built')")
    m = COLLECTION_TIME.search(shipped)
    assert m, 'the pattern no longer matches the decorator that shipped'
    cond = m.group('cond') or ''
    assert any(t in cond for t in ARTIFACT_TOKENS), (
        'the pattern matches the decorator but no longer recognises the '
        'artifact it gates on, so the guard would let it through')


def test_a_skipif_on_something_else_is_left_alone():
    """The guard must stay narrow. Two skipifs in this suite gate on git
    history and on an unrelated fixture, and both are legitimate."""
    unrelated = "@pytest.mark.skipif(not has_git_history(), reason='shallow')"
    m = COLLECTION_TIME.search(unrelated)
    assert m, 'the pattern should still match the decorator form'
    cond = m.group('cond') or ''
    assert not any(t in cond for t in ARTIFACT_TOKENS), (
        'a skipif unrelated to the built page is being flagged, which would '
        'push people to work around the guard rather than with it')
