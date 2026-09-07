"""
Execute a Booth regression fixture, and record what Booth said about it.

    python src/booth_fixture_runner.py assemble fixed-everywhere
    python src/booth_fixture_runner.py prompt   fixed-everywhere
    python src/booth_fixture_runner.py record   fixed-everywhere --report r.md
    python src/booth_fixture_runner.py check

A fixture (tests/booth_fixtures/<id>/) is a miniature pull request containing a
KNOWN defect, drawn from a real audit of this repository. The question it poses
is "does Booth still catch this class of failure". Answering that needs Booth
to actually run, which costs subscription usage -- so this module is built so
that asking is rare and re-checking is free:

  assemble  builds a throwaway git repo: base/ committed, then head/ committed
            over it. That is the diff Booth audits.
  prompt    renders the exact instructions, pointing at BOOTH_PROTOCOL.md in
            the assembled checkout, the same as .github/workflows.
  record    takes Booth's report, parses the booth-verdict block, checks it
            against the fixture's declared expectation, and writes
            baseline.json into the fixture directory.
  check     re-checks every recorded baseline. Free. Also run by
            tests/test_booth_fixture_runner.py on every suite run.

WHAT THIS DELIBERATELY DOES NOT DO is invoke a model. Booth runs as a GitHub
Action on subscription auth, so it costs no money -- but it does cost usage,
and usage is the real constraint. Never spend an audit to learn something a
committed baseline already records.

THE ASSERTION IS NEVER BOOTH GRADING ITSELF. Booth writes both the prose and
the verdict block, so a self-report proves nothing on its own. Each fixture
seeds a known defect in a known file and declares one of two expectations:
file-locus (a claim implicating that path came back DISCREPANCY) or no-locus
(the overall verdict is not SAFE TO MERGE). The fixture holds the answer key.
"""
import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(REPO / 'tests' / 'booth_fixtures'))

import booth_verdict as bv  # noqa: E402
import loader  # noqa: E402

BASELINE = 'baseline.json'

#: Identity for the throwaway repo. Set per-command so the runner never depends
#: on, or writes to, the machine's global git config.
GIT_ID = ('-c', 'user.name=fixture', '-c', 'user.email=fixture@example.invalid')


def _git(cwd, *args):
    r = subprocess.run(
        ('git',) + GIT_ID + args, cwd=cwd,
        capture_output=True, text=True,
    )
    if r.returncode:
        raise RuntimeError('git {} failed in {}:\n{}'.format(
            ' '.join(args), cwd, r.stderr.strip() or r.stdout.strip()))
    return r.stdout


def _force_rmtree(path):
    """Delete a git checkout on Windows, where objects are read-only.

    Git writes loose objects without the write bit, and `shutil.rmtree` then
    fails with PermissionError partway through -- leaving a half-deleted repo
    that the next assemble() would build on top of. Clearing the bit and
    retrying is the portable fix; on POSIX the handler simply never fires.
    """
    import os
    import stat

    def _retry(func, target, _exc):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    shutil.rmtree(path, onerror=_retry)


def _write_tree(dest, tree):
    for rel, text in tree.items():
        path = dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')


def assemble(meta, dest):
    """Build the throwaway repo. Returns (base_sha, head_sha).

    Two real commits, not a patch file: Booth's procedure runs git commands --
    log, diff, show -- and a fixture that cannot answer them would test a
    different thing than the audits it is modelling.
    """
    dest = Path(dest)
    if dest.exists():
        _force_rmtree(dest)
    dest.mkdir(parents=True)

    _git(dest, 'init', '-q', '-b', 'main')

    _write_tree(dest, loader.base_tree(meta))
    _git(dest, 'add', '-A')
    _git(dest, 'commit', '-q', '-m', 'Base state before the pull request')
    base = _git(dest, 'rev-parse', 'HEAD').strip()

    _git(dest, 'checkout', '-q', '-b', 'fixture-pr')
    # Remove tracked files the head tree drops, so a deletion is a real
    # deletion in the diff rather than a leftover from base.
    for rel in loader.base_tree(meta):
        if rel not in loader.head_tree(meta):
            (dest / rel).unlink()
    _write_tree(dest, loader.head_tree(meta))
    _git(dest, 'add', '-A')

    subject = loader.body(meta).strip().splitlines()[0]
    _git(dest, 'commit', '-q', '-m', subject)
    head = _git(dest, 'rev-parse', 'HEAD').strip()

    (dest / 'PR_BODY.md').write_text(loader.body(meta), encoding='utf-8')
    shutil.copy2(REPO / 'BOOTH_PROTOCOL.md', dest / 'BOOTH_PROTOCOL.md')
    return base, head


PROMPT = """You are Booth. The repository to audit is at {work_dir}. Work
there -- `cd {work_dir}` first, and run every command inside it.

Read BOOTH_PROTOCOL.md in that directory and follow its procedure exactly for
the pull request described below.

This is a REGRESSION FIXTURE, not a live pull request. There is no GitHub API
here. The repository is checked out at the PR's head commit on branch
`fixture-pr`; its base is `main`. Use ordinary git commands.

  the diff:        git diff main..fixture-pr
  the description: PR_BODY.md in the repository root

Non-negotiable, from the protocol: RE-EXECUTE the commands that would prove or
disprove each claim, and show the real output you got. A report that reasons
about whether claims sound plausible, without running anything, is a failed
audit. If a claim genuinely cannot be checked with the tools available here,
mark it UNVERIFIABLE and say why rather than guessing.

Close with the machine-readable booth-verdict block the protocol specifies.
Use {head} as the head, and 0 as the PR number.
"""


def prompt(meta, head_sha, work_dir='.'):
    """The exact instructions, as one source of truth.

    The workflow calls this rather than restating the prompt in YAML. The
    live audit workflow already makes that choice deliberately -- it points at
    BOOTH_PROTOCOL.md instead of duplicating it, with a comment saying "one
    source of truth" -- and a prompt copied into a workflow file would drift
    from this one exactly the way that comment warns about.
    """
    return PROMPT.format(head=head_sha[:7], work_dir=work_dir)


def baseline_path(meta):
    return meta['_path'] / BASELINE


def record(meta, report_text, head_sha=None):
    """Parse a Booth report, check the expectation, write the baseline.

    Returns (ok, explanation). Writes the baseline either way: a fixture Booth
    FAILED is the most important thing to have on record, and hiding it until
    someone re-runs the audit would be the expensive mistake.
    """
    verdict = bv.extract(report_text)
    ok, why = loader.satisfied_by(meta, verdict)
    payload = {
        'fixture': meta['id'],
        'recorded_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'fixture_head': head_sha,
        'assertion': meta['assertion'],
        'satisfied': ok,
        'explanation': why,
        'cross_check': bv.cross_check(report_text, verdict) if verdict else [
            'no booth-verdict block found'],
        'verdict': verdict,
    }
    baseline_path(meta).write_text(
        json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    return ok, why


def load_baseline(meta):
    p = baseline_path(meta)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding='utf-8'))


def check_one(meta):
    """Re-check a recorded baseline against the fixture's expectation. Free.

    Deliberately re-derives the answer from the stored verdict rather than
    trusting the stored `satisfied` flag. If the fixture's expectation is
    edited -- a different path named, say -- the recorded pass must stop
    counting, or the corpus would keep reporting a result for a question it is
    no longer asking.
    """
    baseline = load_baseline(meta)
    if baseline is None:
        return None, 'no baseline recorded yet'
    ok, why = loader.satisfied_by(meta, baseline.get('verdict'))
    return ok, why


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    sub = ap.add_subparsers(dest='cmd', required=True)

    for name in ('assemble', 'prompt', 'record'):
        p = sub.add_parser(name)
        p.add_argument('fixture')
        p.add_argument('--out', default=None,
                       help='directory for the throwaway repo')
        if name == 'record':
            p.add_argument('--report', required=True,
                           help="file holding Booth's report")
    sub.add_parser('check')

    args = ap.parse_args(argv)

    if args.cmd == 'check':
        rows = [(m, ) + check_one(m) for m in loader.load_all()]
        failed = 0
        for meta, ok, why in rows:
            state = 'NO BASELINE' if ok is None else ('PASS' if ok else 'FAIL')
            print('  [{}] {}'.format(state, meta['id']))
            print('      ' + why)
            failed += ok is False
        print()
        if failed:
            print('{} fixture(s) recorded a verdict that does not satisfy '
                  'their expectation.'.format(failed))
            return 1
        print('Every recorded baseline still satisfies its fixture.')
        return 0

    meta = loader.load(loader.FIXTURE_ROOT / args.fixture)
    out = Path(args.out) if getattr(args, 'out', None) else \
        REPO / '.fixture-run' / meta['id']

    base, head = assemble(meta, out)

    if args.cmd == 'prompt':
        # The work_dir the prompt names must be the directory that was just
        # assembled. An earlier version reassembled somewhere else and told
        # Booth to work in a third place; the CI job would have audited an
        # empty directory and reported honestly on nothing.
        print(prompt(meta, head, work_dir=str(out)))
        return 0

    if args.cmd == 'assemble':
        print('assembled {} at {}'.format(meta['id'], out))
        print('  base main        {}'.format(base[:7]))
        print('  head fixture-pr  {}'.format(head[:7]))
        print('  description      PR_BODY.md')
        print('\nseeded defect: {}'.format(
            meta.get('seeded_defect', {}).get('explanation', '(none declared)')))
        return 0

    ok, why = record(meta, Path(args.report).read_text(encoding='utf-8'), head)
    print('{}: {}'.format('SATISFIED' if ok else 'NOT SATISFIED', why))
    print('baseline written to {}'.format(baseline_path(meta)))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
