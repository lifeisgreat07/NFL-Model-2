"""The actions that run with this repository's tokens are pinned to commit
SHAs (Stage 27 item 1, from the 2026-09-28 audit).

A tag such as `@v1` is a pointer the action's owner can move, so whoever
controls it controls what runs. The Claude Code action reads every PR with
this repository's token; the auto-commit action pushes to main; checkout and
setup-python run first in every job, with the job's token in reach. A full
commit SHA cannot be moved, so each use of these four names one, with the
release it was taken from in a trailing comment for readers and updates.

The SHAs were read from the GitHub API on 2026-09-28: each is the commit the
action's major tag (`v1`, `v4`, `v5`, `v6`) pointed at that day, which was
also the commit of the newest release in that major, so pinning changed
nothing that runs. checkout and setup-python are on two majors each (some
workflows moved to v6 and some did not); pinning keeps each where it was.

Stage 45 item 1 pinned the rest: setup-node, cache, upload- and
download-artifact and the two Pages actions (deploy-pages runs with
`pages: write` and `id-token: write`). Their SHAs were read with
`git ls-remote` on 2026-10-06, again the commit each major tag pointed at,
with the newest release on that commit in the comment. The scan now covers
every `uses:` in every workflow, so a new action arriving on a tag fails here
rather than waiting for someone to add it to a list.

Stage 88 item 1 moved every action that still ran on Node 20 (checkout v4,
setup-python v5, setup-node v4, cache v4, upload-artifact v4, download-artifact
v4, deploy-pages v4, upload-pages-artifact v3, git-auto-commit v5) to the
first major of each that runs on Node 24 (checkout to v6, where three
workflows already were, rather than v5), with SHAs read with `git ls-remote`
on 2026-11-05, and `test_every_pin_is_on_a_node_24_major` keeps them there.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / '.github' / 'workflows'

# action -> how many uses the scan must find
PINNED = {
    'anthropics/claude-code-action': 4,
    'stefanzweifel/git-auto-commit-action': 3,
    'actions/checkout': 44,  # with nfl-override-check.yml (Stage 88 item 4), deploy-pages' alert job (Stage 93 item 14), nfl-override-automerge.yml (Stage 90 item 4) and mlb-data-probe.yml (Stage 97 item 1)
    'actions/setup-python': 38,
    'actions/setup-node': 4,
    'actions/cache': 1,
    'actions/upload-artifact': 8,
    'actions/download-artifact': 5,
    'actions/upload-pages-artifact': 1,
    'actions/deploy-pages': 1,
}
# action -> the majors it may be pinned to: the ones whose action.yml says
# `using: node24` (or composite, for claude-code-action, whose steps the action
# itself pins). Read from each release's action.yml on 2026-11-05 (Stage 88
# item 1). GitHub retires Node 20 on its runners, and an action still on it
# either fails or is forced onto 24 untested, so a pin back on a Node 20 major
# (checkout v4, setup-python v5, upload-artifact v5, ...) fails here.
NODE24_MAJORS = {
    'anthropics/claude-code-action': {'v1'},
    'stefanzweifel/git-auto-commit-action': {'v7'},
    'actions/checkout': {'v5', 'v6', 'v7'},
    'actions/setup-python': {'v6', 'v7'},
    'actions/setup-node': {'v5', 'v6', 'v7'},
    'actions/cache': {'v5', 'v6'},
    'actions/upload-artifact': {'v6', 'v7'},
    'actions/download-artifact': {'v7', 'v8'},
    'actions/upload-pages-artifact': {'v5'},
    'actions/deploy-pages': {'v5'},
}
USES = re.compile(r'^\s*(?:-\s*)?uses:\s*(\S+?)@(\S+)(.*)$', re.M)
VERSION = re.compile(r'\s+#\s+(v\d+)\.\d+\.\d+\s*')


def uses():
    """Every `uses:` in every workflow, pinned list or not."""
    out = []
    for p in sorted(WORKFLOWS.glob('*.yml')):
        for action, ref, rest in USES.findall(p.read_text(encoding='utf-8').replace('\r\n', '\n')):
            out.append((p.name, action.lower(), ref, rest))
    return out


def test_every_action_in_every_workflow_is_on_the_list():
    unlisted = sorted({(f, a) for f, a, _, _ in uses() if a not in PINNED})
    assert not unlisted, f'an action no test counts: {unlisted}'


def test_the_scan_finds_every_use_of_the_pinned_actions():
    counts = {a: 0 for a in PINNED}
    for _, a, _, _ in uses():
        counts[a] = counts.get(a, 0) + 1
    assert counts == PINNED, counts


def test_each_is_pinned_to_a_full_commit_sha():
    bad = [(f, a, r) for f, a, r, _ in uses() if not re.fullmatch(r'[0-9a-f]{40}', r)]
    assert not bad, f'an action is referenced by a movable ref: {bad}'


def test_each_pin_says_which_release_it_is():
    bad = [(f, a) for f, a, _, rest in uses() if not VERSION.fullmatch(rest)]
    assert not bad, f'a pinned SHA has no "# vX.Y.Z" comment: {bad}'


def test_every_pin_is_on_a_node_24_major():
    assert set(NODE24_MAJORS) == set(PINNED)
    old = sorted({(f, a, m.group(1)) for f, a, _, rest in uses()
                  if (m := VERSION.fullmatch(rest)) and m.group(1) not in NODE24_MAJORS.get(a, set())})
    assert not old, f'an action pinned to a major that does not run on Node 24: {old}'


def test_one_major_of_an_action_is_one_sha_everywhere():
    """Two workflows on two different commits of the same major is an update
    that stopped halfway."""
    shas = {}
    for f, a, r, rest in uses():
        m = VERSION.fullmatch(rest)
        if m:
            shas.setdefault((a, m.group(1)), set()).add(r)
    split = {k: v for k, v in shas.items() if len(v) > 1}
    assert not split, split
