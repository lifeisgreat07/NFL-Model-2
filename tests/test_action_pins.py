"""Third-party actions that hold a write token are pinned to a commit SHA
(Stage 27 item 1, from the 2026-09-28 audit).

A tag such as `@v1` is a pointer the action's owner can move. The Claude Code
action runs with this repository's token and reads every PR; the auto-commit
action pushes to main with a write token. Whoever controls those tags
controls what runs with those tokens. A full commit SHA cannot be moved, so
each use of these two actions names one, with the release it was taken from
in a trailing comment so a reader and an update can see the version.

The SHAs were read from the GitHub API on 2026-09-28: each is the commit the
action's major tag (`v1`, `v5`) pointed at that day, which is also the commit
of the newest release in that major, so pinning changed nothing that runs.

checkout and setup-python follow in their own PR (item 1's second half).
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / '.github' / 'workflows'

PINNED = ('anthropics/claude-code-action', 'stefanzweifel/git-auto-commit-action')
USES = re.compile(r'^\s*(?:-\s*)?uses:\s*(\S+?)@(\S+)(.*)$', re.M)


def uses():
    out = []
    for p in sorted(WORKFLOWS.glob('*.yml')):
        for action, ref, rest in USES.findall(p.read_text(encoding='utf-8').replace('\r\n', '\n')):
            out.append((p.name, action, ref, rest))
    return out


def test_the_scan_finds_every_use_of_the_pinned_actions():
    found = [(f, a) for f, a, _, _ in uses() if a.lower() in PINNED]
    assert len([1 for _, a in found if a == PINNED[0]]) == 2, found
    assert len([1 for _, a in found if a == PINNED[1]]) == 3, found


def test_each_is_pinned_to_a_full_commit_sha():
    bad = [(f, a, r) for f, a, r, _ in uses()
           if a.lower() in PINNED and not re.fullmatch(r'[0-9a-f]{40}', r)]
    assert not bad, f'a write-token action is referenced by a movable ref: {bad}'


def test_each_pin_says_which_release_it_is():
    bad = [(f, a) for f, a, r, rest in uses()
           if a.lower() in PINNED and not re.fullmatch(r'\s+#\s+v\d+\.\d+\.\d+\s*', rest)]
    assert not bad, f'a pinned SHA has no "# vX.Y.Z" comment: {bad}'


def test_one_action_is_pinned_to_one_sha_everywhere():
    """Two workflows on two different commits of the same action is an update
    that stopped halfway."""
    shas = {}
    for f, a, r, _ in uses():
        if a.lower() in PINNED:
            shas.setdefault(a.lower(), set()).add(r)
    assert all(len(s) == 1 for s in shas.values()), shas
