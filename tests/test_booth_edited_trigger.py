"""
Booth must re-audit a rewritten PR description, and must not bill a title tweak.

Those two requirements live in different parts of booth-pr-audit.yml -- the
`edited` trigger in `on:`, and a `github.event.changes.body` clause in the
audit job's `if:` -- and neither is any use without the other. `edited` alone
spends a full audit every time someone fixes a typo in a title. The `if:`
clause alone is dead code that reads as protection while the trigger it guards
does not exist. This file asserts the pairing so they cannot drift apart.

Why it matters: without `edited`, Booth never sees a description that changed
after its audit posted. That is the half of a PR a human approves on -- scope,
claims, evidence -- and the stale audit comment goes on sitting above it
looking current. On PR #28 (2026-09-07) that happened three times in one
session; two reports rendered findings against superseded descriptions, and the
only route to a current audit was to dispatch by hand and know to do so.

Booth CANNOT audit the PR that introduces this, because the Claude Code action
refuses to run when a PR's copy of its own workflow file differs from main's --
it skips with a success status. So this test is a substantial part of the
evidence for that change, and the rest is a live demonstration on the following
PR.

Parsed by line position rather than with PyYAML, matching
test_workflow_churn_guard.py: yaml is not installed on the machine this suite
runs on, and the assertions here are about which text is present and which
block it sits in -- which line positions capture exactly.

Run with: pytest tests/test_booth_edited_trigger.py -v
"""
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
WORKFLOW = REPO_ROOT / '.github' / 'workflows' / 'booth-pr-audit.yml'

TRIGGER = 'edited'
BODY_GUARD = 'github.event.changes.body'
ACTION_GUARD = "github.event.action != 'edited'"


def _lines():
    if not WORKFLOW.is_file():
        pytest.skip("booth-pr-audit.yml not present in this checkout")
    return WORKFLOW.read_text(encoding='utf-8').splitlines()


def _types_line(lines):
    """The `types:` list under on.pull_request, ignoring comments."""
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if stripped.startswith('types:'):
            return i, stripped
    return None, None


def _if_block(lines):
    """The audit job's `if:` condition, joined into one string.

    The condition is a YAML folded scalar (`if: >-`) spanning several lines,
    so a single-line search would miss it. Collects the continuation lines by
    indentation and drops comments.
    """
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if not stripped.startswith('if:'):
            continue
        indent = len(line) - len(line.lstrip())
        parts = [stripped[len('if:'):].strip()]
        for follow in lines[i + 1:]:
            if not follow.strip():
                continue
            follow_indent = len(follow) - len(follow.lstrip())
            if follow_indent <= indent:
                break
            if follow.strip().startswith('#'):
                continue
            parts.append(follow.strip())
        return ' '.join(p for p in parts if p and p != '>-')
    return None


def test_there_is_something_to_check():
    """Guard against the whole file vanishing and every assertion passing."""
    lines = _lines()
    assert lines, "booth-pr-audit.yml is empty"
    idx, types = _types_line(lines)
    assert types is not None, (
        "booth-pr-audit.yml has no `types:` list under on.pull_request -- "
        "this test can no longer check what it claims to check."
    )


def test_edited_is_a_trigger():
    """Without this, a rewritten description is never re-audited."""
    _, types = _types_line(_lines())
    assert TRIGGER in types, (
        f"booth-pr-audit.yml does not trigger on `{TRIGGER}`: {types}\n"
        "A description rewritten after an audit posts would never be "
        "re-audited, and the stale audit comment would go on looking current."
    )


def test_the_body_guard_is_present():
    """Without this, `edited` bills an audit for every title typo."""
    condition = _if_block(_lines())
    assert condition is not None, "no `if:` condition found on the audit job"
    assert BODY_GUARD in condition, (
        f"the audit job's `if:` does not mention `{BODY_GUARD}`:\n"
        f"  {condition}\n"
        "`edited` fires on title-only changes too, which cannot invalidate an "
        "audit. Without this clause every title tweak spends a full run."
    )
    assert ACTION_GUARD in condition, (
        f"the `if:` checks the body but not the action:\n  {condition}\n"
        f"Expected `{ACTION_GUARD}` so the body check applies ONLY to edited "
        "events -- otherwise pushes and opens, which carry no `changes` "
        "payload, would be filtered out and Booth would stop running at all."
    )


def test_the_pair_stays_together():
    """The real invariant: neither half is any use alone.

    Stated as an implication rather than as two independent facts, so that
    removing the trigger in a future edit fails here loudly instead of quietly
    leaving a guard that protects nothing.
    """
    lines = _lines()
    _, types = _types_line(lines)
    condition = _if_block(lines)
    has_trigger = TRIGGER in types
    has_guard = condition is not None and BODY_GUARD in condition
    assert has_trigger == has_guard, (
        f"`{TRIGGER}` trigger present: {has_trigger}; body guard present: "
        f"{has_guard}.\n"
        "These two must change together. `edited` without the guard bills an "
        "audit for every title edit; the guard without `edited` is dead code "
        "that reads as protection."
    )


def test_manual_dispatch_still_bypasses_the_draft_check():
    """The pre-existing escape hatch must survive the new clause.

    workflow_dispatch carries no pull_request payload, so `draft == false` is
    never true for it; the original condition relied on the `||` to let manual
    runs through. Wrapping that in parentheses to add the body guard is exactly
    the kind of edit that silently breaks it.
    """
    condition = _if_block(_lines())
    assert "github.event_name == 'workflow_dispatch'" in condition, (
        f"manual dispatch is no longer exempted:\n  {condition}\n"
        "Re-running an audit by hand is the documented recovery path when an "
        "audit is stale or was skipped; it must not require a push."
    )
