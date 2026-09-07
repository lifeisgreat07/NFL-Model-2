"""
Run the mutation corpus: break something on purpose, prove a test notices.

WHY THIS IS COMMITTED

CLAUDE.md instructs "mutation-test every new guard" -- a rule earned by a
failure that has now happened five times, where a guard's comment claimed more
than its code delivered. Every PR in this repository that added a guard also
claimed a mutation table: N mutations, each caught.

Every one of those tables was produced by a script in a temp directory that
was then thrown away. Booth said so on PR #26: "No mutation-testing script was
committed for this PR... 2/13 is a sample, not a full re-run." It was right,
and it had to hand-reconstruct two mutations to spot-check the claim.

So the tables were prose describing an experiment with no surviving artifact --
the same species as the version history that lived in a comment and the
screenshots that were never attached. This makes the claim a command.

WHAT IT CHECKS, BEYOND "SOMETHING FAILED"

A mutation that makes the suite go red is weaker evidence than it looks. It
matters WHICH test caught it: if a mutation aimed at the date guard is caught
by an ordering guard that runs first, the date guard is still untested and the
table still says it passed. That happened, in this repo, and is recorded in
CLAUDE.md as its own trap.

So every case names `expect_caught_by`, and a case whose intended test did not
fail is reported as WRONG-GUARD -- a failure, not a pass, even though the
suite went red.

BYTECODE

Cleared before every run, with -B. Several mutations preserve file size
(2.4 -> 2.5, 2026 -> 2126), and .pyc invalidation keys on size plus a
one-second-granularity mtime. Written milliseconds apart, Python reuses the
previous case's bytecode and mutations report CAUGHT while displaying the
PREVIOUS case's failure. That is a harness that lies, and it did.

Usage:
    python tests/mutation/runner.py              # every case
    python tests/mutation/runner.py --id sos-*   # a subset, glob on id
    python tests/mutation/runner.py --list       # names only, runs nothing

Exit 0 only if every case is caught by the test it names.
"""
import argparse
import fnmatch
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from corpus import REPO_ROOT, load_corpus, anchor_occurrences, CorpusError

CAUGHT, SURVIVED, WRONG_GUARD, BAD_ANCHOR = 'CAUGHT', 'SURVIVED', 'WRONG-GUARD', 'BAD-ANCHOR'


def _clear_bytecode():
    for cache in REPO_ROOT.rglob('__pycache__'):
        for pyc in cache.glob('*.pyc'):
            try:
                pyc.unlink()
            except OSError:
                pass


def _run_tests(test_path):
    """Returns (returncode, set of failed test names, raw stdout)."""
    _clear_bytecode()
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
    proc = subprocess.run(
        [sys.executable, '-B', '-m', 'pytest', test_path, '-q', '--no-header',
         '-p', 'no:cacheprovider'],
        cwd=REPO_ROOT, capture_output=True, text=True, env=env)
    failed = set()
    for line in proc.stdout.splitlines():
        # pytest -q short summary: "FAILED tests/x.py::test_name - detail"
        if line.startswith('FAILED '):
            name = line[len('FAILED '):].split(' ')[0]
            failed.add(name.split('::')[-1].split('[')[0])
    return proc.returncode, failed, proc.stdout


def run_case(case):
    """Apply one mutation, run its tests, restore. Never leaves the tree dirty."""
    target = REPO_ROOT / case['target']
    original = target.read_bytes()

    try:
        count, find, nl = anchor_occurrences(case)
    except CorpusError as e:
        return {'status': BAD_ANCHOR, 'detail': str(e), 'caught_by': set()}

    if count != 1:
        return {
            'status': BAD_ANCHOR,
            'detail': (f"anchor matches {count} time(s) in {case['target']}, "
                       f"expected exactly 1 -- this case is testing nothing"),
            'caught_by': set(),
        }

    replace = case['replace'].encode('utf-8').replace(b'\n', nl)
    try:
        target.write_bytes(original.replace(find, replace))
        code, failed, out = _run_tests(case['tests'])
    finally:
        target.write_bytes(original)
        restored = target.read_bytes() == original

    if not restored:
        return {'status': BAD_ANCHOR, 'caught_by': set(),
                'detail': f"FAILED TO RESTORE {case['target']} -- fix by hand"}

    intended = case['expect_caught_by']
    if code == 0:
        return {'status': SURVIVED, 'caught_by': set(),
                'detail': (f"the suite stayed green with this mutation applied; "
                           f"{intended} does not actually catch it")}
    if intended not in failed:
        return {'status': WRONG_GUARD, 'caught_by': failed,
                'detail': (f"the suite went red, but {intended} passed. "
                           f"Failures: {sorted(failed) or 'none reported'}. "
                           f"Another guard fired first, so the intended one is "
                           f"still untested.")}
    return {'status': CAUGHT, 'caught_by': failed,
            'detail': f"caught by {intended}"}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('--id', default='*',
                    help="glob over case ids (default: all)")
    ap.add_argument('--list', action='store_true',
                    help="list matching cases and exit without running them")
    args = ap.parse_args()

    cases = [c for c in load_corpus() if fnmatch.fnmatch(c['id'], args.id)]
    if not cases:
        print(f"no cases match {args.id!r}")
        return 1

    if args.list:
        for c in cases:
            print(f"  {c['id']:<38} {c['target']}")
            print(f"  {'':<38} caught by {c['expect_caught_by']}")
        print(f"\n{len(cases)} case(s).")
        return 0

    print(f"Running {len(cases)} mutation(s). Each breaks the source on "
          f"purpose and must be caught by the test it names.\n")

    results = []
    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case['id']}", flush=True)
        print(f"        {case['why']}")
        r = run_case(case)
        results.append((case, r))
        print(f"        {r['status']}: {r['detail']}\n", flush=True)

    bad = [(c, r) for c, r in results if r['status'] != CAUGHT]
    print('-' * 68)
    for status in (CAUGHT, SURVIVED, WRONG_GUARD, BAD_ANCHOR):
        n = sum(1 for _, r in results if r['status'] == status)
        if n:
            print(f"  {status:<12} {n}")

    if bad:
        print(f"\n{len(bad)} case(s) did not behave as the corpus claims:")
        for c, r in bad:
            print(f"  - {c['id']}: {r['status']}")
        print("\nA guard that a mutation cannot break is not a guard. Fix the "
              "guard, or fix the case -- but do not quote a mutation table "
              "while this is red.")
        return 1

    print(f"\nAll {len(results)} mutations caught by the tests they name.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
