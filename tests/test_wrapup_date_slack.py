"""The two date checks that must agree, and the one direction they must not.

Booth's audit of PR #45 found the gate and the guard disagreeing:
tests/test_workflow_docs.py allowed docs/context.md's stamp to sit one day in
the future, while src/session_wrapup.py's check_context_is_current() demanded
an exact string match against today. Its words: "merging this PR today ships a
session-end gate that will fail on its own author's branch."

That was a real disagreement, not a wording one. The agent writing
docs/context.md runs on UTC; session_wrapup.py runs on the machine, on US
local time. On the evening this was written they read 09-09 and 09-08 -- so a
context file written and stamped inside one session could fail that same
session's wrap-up, which is precisely the spurious hard failure this project's
traps section warns about.

The resolution is one-directional slack, and the direction is the whole point:

  tomorrow  -> PASS. That is a timezone.
  yesterday -> FAIL. That is a context file nobody rewrote, which is the only
               thing this check was ever for.

Symmetric slack would be the easy fix and the wrong one: it would buy the
timezone case at the cost of letting a genuinely stale file through, gutting
the check. So both directions are asserted here. A future edit that "fixes"
the timezone complaint by widening the window in both directions fails this
file.

These call the check functions directly. Running session_wrapup.py as a
subprocess would run pytest, which would run this test, which would run
session_wrapup.py -- the recursion its own module docstring warns about, and
which has already had to be killed by hand once.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))

import session_wrapup  # noqa: E402

TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)


@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    """A throwaway repo root, so these tests never depend on -- or disturb --
    the real docs/context.md, whose stamp changes every session."""
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'memory').mkdir()
    monkeypatch.setattr(session_wrapup, 'REPO', tmp_path)
    return tmp_path


def _stamp(root, day):
    (root / 'docs' / 'context.md').write_text(
        f"# Context\n\nLast updated: {day.isoformat()}\n", encoding='utf-8')


@pytest.mark.parametrize('day,should_pass', [
    (TODAY, True),
    (TOMORROW, True),
    (YESTERDAY, False),
    (TODAY - timedelta(days=3), False),
])
def test_context_stamp_slack_is_one_day_forward_only(fake_repo, day, should_pass):
    _stamp(fake_repo, day)
    result = session_wrapup.check_context_is_current()
    assert result.ok is should_pass, (
        f"a context.md stamped {day.isoformat()} (today is {TODAY.isoformat()}) "
        f"{'should' if should_pass else 'should not'} pass the wrap-up gate. "
        f"Got: {result.detail}")


@pytest.mark.parametrize('day,should_pass', [
    (TODAY, True),
    (TOMORROW, True),
    (YESTERDAY, False),
])
def test_session_memory_slack_is_one_day_forward_only(fake_repo, day, should_pass):
    """Same rule, same reason: the file is named by the clock of whichever
    machine wrote it, so a UTC-named file must satisfy a local-time check --
    but a file from a previous session must not satisfy this one."""
    (fake_repo / 'memory' / f'{day.isoformat()}.md').write_text('x', encoding='utf-8')
    result = session_wrapup.check_session_memory_written()
    assert result.ok is should_pass, (
        f"a memory file named {day.isoformat()}.md (today is {TODAY.isoformat()}) "
        f"{'should' if should_pass else 'should not'} satisfy the wrap-up gate. "
        f"Got: {result.detail}")


def test_the_gate_and_the_pytest_guard_do_not_disagree_about_tomorrow():
    """The specific pairing Booth caught. tests/test_workflow_docs.py tolerates
    a stamp up to one day in the future; the gate must tolerate the same one,
    or the project ships two checks that contradict each other and only one of
    them runs at the moment it matters."""
    guard = (REPO / 'tests' / 'test_workflow_docs.py').read_text(encoding='utf-8')
    assert '.days <= 1' in guard, (
        "tests/test_workflow_docs.py no longer bounds the stamp to one day "
        "ahead; this test's premise is gone and the pair needs re-reading "
        "together rather than one of them being quietly widened")
    gate = (REPO / 'src' / 'session_wrapup.py').read_text(encoding='utf-8')
    assert 'timedelta(days=1)' in gate, (
        "src/session_wrapup.py no longer grants the one-day forward slack the "
        "pytest guard grants. That is the exact disagreement Booth found on "
        "PR #45")


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
