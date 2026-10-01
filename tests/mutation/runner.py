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
    python tests/mutation/runner.py --sample 30 --seed 20260929
                                                 # a reproducible slice
                                                 # (the nightly workflow)

Exit 0 only if every case is caught by the test it names.
"""
import argparse
import fnmatch
import os
import random
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from corpus import REPO_ROOT, CorpusError, anchor_occurrences, load_corpus

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
    # UTF-8 both ways, whatever the machine's locale. The child writes its
    # report in UTF-8 (PYTHONIOENCODING) and this side reads it as UTF-8.
    # Reading in the locale codec crashed the runner on markys (cp1252) at
    # byte 0x90 in one case's failure text, and a crash there reports nothing
    # about the case; errors='replace' keeps a stray byte from ever doing so.
    #
    # And the child runs in Python's UTF-8 mode (PYTHONUTF8), so a file opened
    # without an encoding is UTF-8 there, as on the Linux runners. Without it
    # a case whose mutation drops an encoding= (generator_encoding.json) was
    # caught on Windows by the conftest build crashing on cp1252 before the
    # test it names could run, and was reported WRONG-GUARD there only. The
    # encoding guards are source scans, which hold on every machine; a plain
    # suite run on Windows still builds the page in the locale's codec.
    env = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONIOENCODING': 'utf-8'}
    proc = subprocess.run(
        [sys.executable, '-B', '-m', 'pytest', test_path, '-q', '--no-header',
         '-p', 'no:cacheprovider'],
        cwd=REPO_ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
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


def select_cases(corpus, patterns):
    """Every case matching ANY of the patterns, in corpus order, each once."""
    return [c for c in corpus if any(fnmatch.fnmatch(c['id'], p) for p in patterns)]


def sample_cases(cases, n, seed):
    """n of the cases, chosen by the seed, in corpus order (Stage 27 item 2).

    The same seed over the same corpus always picks the same cases, so a
    nightly run's slice can be re-run by hand from the seed in its summary.
    Sorted by id before sampling, so the choice does not depend on the order
    the case files happen to load in."""
    ids = sorted(c['id'] for c in cases)
    chosen = set(random.Random(seed).sample(ids, min(n, len(ids))))
    return [c for c in cases if c['id'] in chosen]


def summary_markdown(results, scope):
    """The counts as a Markdown block for a CI run summary."""
    lines = [f'### Mutation slice: {scope}', '',
             '| Status | Cases |', '|---|---|']
    for status in (CAUGHT, SURVIVED, WRONG_GUARD, BAD_ANCHOR):
        lines.append(f'| {status} | {sum(1 for _, r in results if r["status"] == status)} |')
    bad = [(c, r) for c, r in results if r['status'] != CAUGHT]
    if bad:
        lines += ['', 'Not caught as the corpus claims:', '']
        lines += [f'- `{c["id"]}`: {r["status"]}' for c, r in bad]
    lines += ['', 'Cases run: ' + ', '.join(f'`{c["id"]}`' for c, _ in results), '']
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    # action='append': repeating --id used to keep only the LAST one and still
    # print "All N mutations caught", so three ids given on one command ran one
    # case and reported success (found 2026-09-21). Every --id now counts, and
    # the header says which ones ran.
    ap.add_argument('--id', action='append', default=None,
                    help="glob over case ids; repeat to select several (default: all)")
    ap.add_argument('--list', action='store_true',
                    help="list matching cases and exit without running them")
    ap.add_argument('--sample', type=int, default=None,
                    help="run only this many of the matching cases, chosen by --seed")
    ap.add_argument('--seed', type=int, default=None,
                    help="seed for --sample (the nightly workflow passes the UTC date)")
    ap.add_argument('--summary', default=None,
                    help="append a Markdown table of the counts to this file")
    args = ap.parse_args(argv)
    if (args.sample is None) != (args.seed is None):
        ap.error('--sample and --seed go together: a slice nobody can re-run is not evidence')

    patterns = args.id or ['*']
    cases = select_cases(load_corpus(), patterns)
    if not cases:
        print(f"no cases match {patterns!r}")
        return 1
    if args.sample is not None:
        cases = sample_cases(cases, args.sample, args.seed)

    if args.list:
        for c in cases:
            print(f"  {c['id']:<38} {c['target']}")
            print(f"  {'':<38} caught by {c['expect_caught_by']}")
        print(f"\n{len(cases)} case(s).")
        return 0

    scope = "the full corpus" if patterns == ['*'] else "--id " + " --id ".join(patterns)
    if args.sample is not None:
        scope = f"--sample {args.sample} --seed {args.seed} over {scope}"
    print(f"Running {len(cases)} mutation(s) selected by {scope}. Each breaks the "
          f"source on purpose and must be caught by the test it names.\n")

    results = []
    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case['id']}", flush=True)
        print(f"        {case['why']}")
        r = run_case(case)
        results.append((case, r))
        print(f"        {r['status']}: {r['detail']}\n", flush=True)

    bad = [(c, r) for c, r in results if r['status'] != CAUGHT]
    if args.summary:
        with open(args.summary, 'a', encoding='utf-8') as f:
            f.write(summary_markdown(results, scope))
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
