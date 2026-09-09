"""Print the derivable half of "where are we", so a session reads facts.

WHY THIS EXISTS

Every staleness failure in this repository has been the same mistake: a fact
that a machine could have derived, typed by hand instead. The suite count read
174 for three days, then 597 against a real 628. `docs/context.md` named the
next action long after it shipped. CLAUDE.md pointed at branches that had been
merged and deleted.

Writing the rule "keep these current" is what CLAUDE.md already did. So this
does not restate the rule -- it computes the answer. Everything printed below
comes from git or from running the suite. Nothing here is remembered.

What it deliberately does NOT do is fetch pull-request state: there is no `gh`
CLI on this machine, and inventing a PR's status would be exactly the class of
confident-but-unchecked claim the whole project exists to avoid. Where a fact
needs GitHub, this says so and stops.

    python src/session_start.py                # includes a full suite run
    python src/session_start.py --skip-tests   # git and documents only

Exits 0 always. This is an orientation tool, not a gate -- `session_wrapup.py`
is the gate.
"""
import argparse
import re
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path

REPO = Path(__file__).parent.parent
CONTEXT = REPO / 'docs' / 'context.md'
CLAUDE_MD = REPO / 'CLAUDE.md'
COUNT_RE = re.compile(r'Suite:\s*\*\*([0-9,]+)\s+passing\*\*')

#: How many days a context file may sit before it is called out. Three is a
#: judgement, not a measurement: long enough to survive a weekend, short
#: enough that a stale one is noticed while the session that wrote it is
#: still reconstructible.
CONTEXT_STALE_DAYS = 3


def _git(*args):
    r = subprocess.run(['git'] + list(args), cwd=REPO,
                       capture_output=True, text=True)
    return r.stdout.strip()


def section(title):
    print('\n' + title)
    print('-' * len(title))


def repo_state():
    section('Repository')
    branch = _git('rev-parse', '--abbrev-ref', 'HEAD')
    print('  branch          {}'.format(branch))

    dirty = _git('status', '--porcelain')
    print('  working tree    {}'.format(
        'clean' if not dirty else '{} uncommitted file(s) -- read these before '
        'you start, they are the last session\'s unfinished thought'.format(
            len(dirty.splitlines()))))
    if dirty:
        for line in dirty.splitlines()[:10]:
            print('                  ' + line)

    upstream = _git('rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}')
    if upstream:
        ahead = _git('rev-list', '--count', '{}..HEAD'.format(upstream))
        behind = _git('rev-list', '--count', 'HEAD..{}'.format(upstream))
        print('  vs {:<13} {} ahead, {} behind'.format(upstream, ahead, behind))
    else:
        print('  upstream        none -- commits here exist only on this machine')
    return branch


def branches():
    """Local branches, and whether each is already merged into main.

    A merged branch left lying around is the noise that makes the unmerged one
    hard to see, and `git branch` alone does not say which is which.
    """
    section('Branches')
    merged = set(_git('branch', '--merged', 'main').replace('*', '').split())
    for name in _git('branch', '--format=%(refname:short)').splitlines():
        if name == 'main':
            continue
        state = 'merged into main -- safe to delete' if name in merged else 'NOT merged'
        print('  {:<38} {}'.format(name, state))


def context_file():
    """Cross-check what docs/context.md says against what git knows.

    This is the check worth having. The file's job is to name the open work,
    and the specific way it rots is naming a branch that has since merged or
    been deleted -- which reads as current to anyone who does not verify it.
    """
    section('docs/context.md')
    if not CONTEXT.exists():
        print('  MISSING. It is the first thing you are supposed to read.')
        return
    text = CONTEXT.read_text(encoding='utf-8')

    m = re.search(r'Last updated:\s*(\d{4})-(\d{2})-(\d{2})', text)
    if m:
        stamped = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        age = (date.today() - stamped).days
        note = ''
        if age > CONTEXT_STALE_DAYS:
            note = '  <- {} days old; treat every claim in it as unverified'.format(age)
        print('  last updated    {} ({} day(s) ago){}'.format(stamped, age, note))
    else:
        print('  last updated    NO STAMP')

    named = set(re.findall(r'\bclaude/[\w./-]+', text))
    local = set(_git('branch', '--format=%(refname:short)').splitlines())
    remote = {b.split('origin/', 1)[1] for b in
              _git('branch', '-r', '--format=%(refname:short)').splitlines()
              if b.startswith('origin/')}
    merged = set(_git('branch', '--merged', 'main').replace('*', '').split())

    if named:
        print('  branches it names:')
        for name in sorted(named):
            if name in merged:
                state = 'MERGED -- the file is out of date'
            elif name in local or name in remote:
                state = 'still open'
            else:
                state = 'GONE -- no such branch locally or on origin'
            print('    {:<38} {}'.format(name, state))

    unmentioned = sorted((local | remote) - named - {'main', 'HEAD'})
    if unmentioned:
        print('  open branches it does NOT mention:')
        for name in unmentioned:
            print('    {}'.format(name))


def suite(skip):
    section('Suite')
    claimed = COUNT_RE.search(CLAUDE_MD.read_text(encoding='utf-8'))
    print('  CLAUDE.md says  {}'.format(
        claimed.group(1) if claimed else 'no count stated'))
    if skip:
        print('  a real run      skipped (--skip-tests)')
        return
    run = subprocess.run([sys.executable, '-m', 'pytest', '-q', '--no-header',
                          '-p', 'no:cacheprovider'],
                         cwd=REPO, capture_output=True, text=True)
    got = re.search(r'(\d+) passed', run.stdout)
    if not got:
        print('  a real run      COULD NOT RUN -- fix this before trusting anything')
        return
    print('  a real run      {}'.format(got.group(1)))
    if claimed and claimed.group(1).replace(',', '') != got.group(1):
        print('  MISMATCH. The documented figure is wrong; correct it now rather '
              'than carrying it through the session.')


def print_context():
    """Print docs/context.md in full, rather than telling you to go read it.

    It is capped at 70 non-blank lines by tests/test_workflow_docs.py for
    exactly this reason: it is meant to fit on a screen, so a reading list that
    points at a one-screen file is a pointless extra step. CLAUDE.md is not
    printed -- it is ~900 lines and mostly durable, so it is read on demand.

    This prints the file rather than summarising it. A summary here would be a
    second copy of the current state, drifting from the first, which is the
    problem this whole split was built to remove.
    """
    section('docs/context.md, in full')
    if not CONTEXT.exists():
        print('  MISSING.')
        return
    for line in CONTEXT.read_text(encoding='utf-8').splitlines():
        print('  ' + line if line.strip() else '')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--skip-tests', action='store_true')
    args = ap.parse_args(argv)

    print('Session start -- {}'.format(datetime.now().strftime('%Y-%m-%d %H:%M')))
    print('=' * 60)
    repo_state()
    branches()
    context_file()
    suite(args.skip_tests)

    print_context()

    section('Read next')
    print('  CLAUDE.md      methodology, stage plans, traps. ~900 lines, so it')
    print('                 is pointed at rather than printed -- but READ IT,')
    print('                 the traps section is where the expensive lessons are.')
    print('  docs/index.md  only if you need to find something')
    print('  memory/        only to answer "why did we decide that"')
    print('\n  Pull-request state is NOT shown above: there is no gh CLI here, and')
    print('  a guessed PR status is the kind of claim this project exists to')
    print('  avoid. Check open PRs on GitHub before starting new work.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
