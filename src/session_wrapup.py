"""
End-of-session check. Run this before closing a session, every time.

    python src/session_wrapup.py

Why it exists: a session ends when usage runs out or attention moves, not when
the work reaches a tidy boundary. Whatever is true at that moment is what the
NEXT session inherits -- and it inherits it through CLAUDE.md, cold, with no
memory of the conversation that produced it. Every wrong fact in that file gets
believed.

This has already cost real time. CLAUDE.md said "Suite: 174 passing" for three
days after it stopped being true; the real number was 382. A stale figure in
the handoff is the first thing a fresh session anchors on.

The split, matching how everything else in this repo works: the cheap checks
that CAN run continuously live in tests/test_claude_md_freshness.py and run on
every commit. The checks that cannot -- running the suite and comparing its
real count to the documented one, inspecting git state -- run here, once, on
demand. A test that runs the suite from inside the suite does not terminate.

Exits non-zero if anything mechanical is wrong, so it can gate a wrap-up.
"""
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
DOC = REPO / 'CLAUDE.md'

#: The line in CLAUDE.md that states the suite size.
COUNT_RE = re.compile(r'Suite:\s*\*\*([0-9,]+)\s+passing\*\*')


class Check:
    def __init__(self, name, ok, detail):
        self.name, self.ok, self.detail = name, ok, detail


def _git(*args):
    r = subprocess.run(('git',) + args, cwd=REPO, capture_output=True, text=True)
    return r.stdout.strip()


def check_suite_count():
    """The number in CLAUDE.md must match a real run, not a remembered one."""
    text = DOC.read_text(encoding='utf-8')
    m = COUNT_RE.search(text)
    if not m:
        return Check('suite count', False,
                     "CLAUDE.md has no 'Suite: **N passing**' line to check")
    claimed = int(m.group(1).replace(',', ''))

    run = subprocess.run(
        [sys.executable, '-B', '-m', 'pytest', '-q'],
        cwd=REPO, capture_output=True, text=True,
    )
    got = re.search(r'(\d+) passed', run.stdout)
    if not got:
        return Check('suite count', False,
                     'could not run the suite; a count that cannot be '
                     'verified must not be published\n' + run.stdout[-400:])
    actual = int(got.group(1))
    if actual != claimed:
        return Check('suite count', False,
                     'CLAUDE.md says {} passing, a real run gives {}. '
                     'Fix the file before the next session inherits '
                     'it.'.format(claimed, actual))
    return Check('suite count', True,
                 'CLAUDE.md and a real run both say {}'.format(actual))


def check_tree_clean():
    dirty = _git('status', '--porcelain')
    if dirty:
        return Check('working tree', False,
                     'uncommitted changes would be invisible to the next '
                     'session:\n  ' + dirty.replace('\n', '\n  '))
    return Check('working tree', True, 'clean')


def check_nothing_unpushed():
    branch = _git('rev-parse', '--abbrev-ref', 'HEAD')
    upstream = _git('rev-parse', '--abbrev-ref', '@{u}')
    if not upstream:
        return Check('unpushed work', False,
                     "branch {!r} has no upstream; commits on it exist only "
                     "on this machine".format(branch))
    ahead = _git('rev-list', '--count', '@{u}..HEAD')
    if ahead and ahead != '0':
        return Check('unpushed work', False,
                     '{} commit(s) on {} are not pushed'.format(ahead, branch))
    return Check('unpushed work', True, '{} is level with {}'.format(branch, upstream))


def check_branch_state():
    """Not a failure, but the next session should know where it is."""
    branch = _git('rev-parse', '--abbrev-ref', 'HEAD')
    if branch == 'main':
        return Check('branch', True, 'on main')
    return Check('branch', True,
                 'on {} -- make sure CLAUDE.md says what this branch is '
                 'for and whether its PR is open'.format(branch))


#: Things no script can check. Printed as a prompt, not asserted.
BY_HAND = [
    "Does CLAUDE.md's 'Current state' describe today, including which stage is "
    "in progress and what the next concrete action is?",
    "Is every PR opened this session either merged, or described in CLAUDE.md "
    "with its number and what it is waiting on?",
    "Did anything surprise you today? A trap entry is cheap now and expensive "
    "to reconstruct later. Prefer the durable shape over the story.",
    "Did any decision get made that a future session would otherwise re-litigate? "
    "Record the decision AND the reasoning, or it gets re-opened.",
    "Are the stage sections still in the order work will actually happen?",
    "Is the Progress tab consistent with CLAUDE.md?",
]


def main():
    checks = [
        check_branch_state(),
        check_tree_clean(),
        check_nothing_unpushed(),
        check_suite_count(),
    ]

    print('Session wrap-up\n' + '-' * 60)
    failed = 0
    for c in checks:
        print('  [{}] {}'.format('PASS' if c.ok else 'FAIL', c.name))
        for line in c.detail.splitlines():
            print('      ' + line)
        failed += not c.ok

    print('\nBy hand -- nothing below can be checked mechanically:')
    for i, q in enumerate(BY_HAND, 1):
        print('  {}. {}'.format(i, q))

    print()
    if failed:
        print('{} mechanical check(s) failed. The next session reads CLAUDE.md '
              'cold and believes it.'.format(failed))
        return 1
    print('Mechanical checks pass. The by-hand list is the real work.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
