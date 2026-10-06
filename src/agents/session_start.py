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

It never GUESSES pull-request state: there is no `gh` CLI on this machine, and
inventing a PR's status would be exactly the class of confident-but-unchecked
claim the whole project exists to avoid. Since Stage 49 item 21 (2026-10-05)
it READS that state instead, with the unattended jobs every session opens by
checking -- the QB override routine's pull request, the Weekly update, the
weekend refresh, the nightly canary and mutation slice, and any open alert
issue -- from GitHub's public API, the same calls CLAUDE.md's PR loop makes by
hand. Every line it prints there says it came from the API and when. If the
API cannot be read (offline, rate-limited) it says so and the rest still runs;
`--offline` skips it, and then the old disclaimer is printed instead.

    python -m src.agents.session_start                # includes a full suite run
    python -m src.agents.session_start --skip-tests   # git, documents and GitHub
    python -m src.agents.session_start --skip-tests --offline   # git and documents only

Exits 0 always. This is an orientation tool, not a gate -- `session_wrapup.py`
is the gate.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

REPO = Path(__file__).parents[2]
SLUG = 'lifeisgreat07/NFL-Model-2'
API = 'https://api.github.com'

#: How far back the unattended-jobs section looks. A judgement, not a
#: measurement: long enough that a session starting the next afternoon still
#: sees last night's canary and slice AND GitHub's late copies of them, which
#: have arrived up to 8h39m after the requested run (2026-10-05).
RUN_WINDOW_HOURS = 36

#: A schedule run this soon after a requested run of the same workflow is
#: almost certainly GitHub's late copy of that slot, not a slot of its own.
#: Also a judgement: the latest copy seen was under 9 hours behind.
LATE_COPY_HOURS = 12
#: The other sports' unattended jobs. `src.pipeline.recent_runs.WATCHED`
#: is the NFL page's runs table, which is a page input the NHL does not join
#: until its own pages are built (Stage 57); until then a session sees the
#: NHL's runs here.
SPORT_WATCHED = {
    'nhl-daily.yml': 'NHL daily run',
    'nhl-canary.yml': 'NHL nightly canary',
}
CONTEXT = REPO / 'docs' / 'context.md'
CLAUDE_MD = REPO / 'CLAUDE.md'
COUNT_RE = re.compile(r'Suite:\s*\*\*([0-9,]+)\s+passing\*\*')

#: How many days a context file may sit before it is called out. Three is a
#: judgement, not a measurement: long enough to survive a weekend, short
#: enough that a stale one is noticed while the session that wrote it is
#: still reconstructible.
CONTEXT_STALE_DAYS = 3


def _git(*args: str) -> str:
    r = subprocess.run(['git'] + list(args), cwd=REPO,
                       capture_output=True, text=True)
    return r.stdout.strip()


def section(title: str) -> None:
    print('\n' + title)
    print('-' * len(title))


def repo_state() -> str:
    section('Repository')
    branch = _git('rev-parse', '--abbrev-ref', 'HEAD')
    print(f'  branch          {branch}')

    dirty = _git('status', '--porcelain')
    print('  working tree    {}'.format(
        'clean' if not dirty else f'{len(dirty.splitlines())} uncommitted file(s) -- read these before '
        'you start, they are the last session\'s unfinished thought'))
    if dirty:
        for line in dirty.splitlines()[:10]:
            print('                  ' + line)

    upstream = _git('rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}')
    if upstream:
        ahead = _git('rev-list', '--count', f'{upstream}..HEAD')
        behind = _git('rev-list', '--count', f'HEAD..{upstream}')
        print(f'  vs {upstream:<13} {ahead} ahead, {behind} behind')
    else:
        print('  upstream        none -- commits here exist only on this machine')
    return branch


def branches() -> None:
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
        print(f'  {name:<38} {state}')


def context_file() -> None:
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
            note = f'  <- {age} days old; treat every claim in it as unverified'
        print(f'  last updated    {stamped} ({age} day(s) ago){note}')
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
            print(f'    {name:<38} {state}')

    unmentioned = sorted((local | remote) - named - {'main', 'HEAD'})
    if unmentioned:
        print('  open branches it does NOT mention:')
        for name in unmentioned:
            print(f'    {name}')


def suite(skip: bool) -> None:
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
    print(f'  a real run      {got.group(1)}')
    if claimed and claimed.group(1).replace(',', '') != got.group(1):
        print('  MISMATCH. The documented figure is wrong; correct it now rather '
              'than carrying it through the session.')


def _get_json(url: str) -> Any:
    """One anonymous read of GitHub's public API (GITHUB_TOKEN if set). The
    repository is public, so no token is needed; without one the limit is
    60 calls an hour, and this section makes six."""
    req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json',
                                               'User-Agent': 'nfl-model-2-session-start'})
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def _utc(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(UTC) if value else None


def run_lines(runs: list[dict[str, Any]], shown: str, now: datetime) -> list[str]:
    """A workflow's runs inside the window, oldest first, one line each.

    A schedule run that follows a requested run of the same workflow within
    LATE_COPY_HOURS is labelled as GitHub's late copy: since Stage 42 every
    slot is requested on time from cron-job.org and GitHub's own cron fires
    the same slot hours later, and a session checking a slot needs to know
    which of the two runs it is looking at.
    """
    cutoff = now - timedelta(hours=RUN_WINDOW_HOURS)
    recent = sorted((r for r in runs if (_utc(r.get('run_started_at') or r.get('created_at'))
                                         or cutoff) > cutoff),
                    key=lambda r: str(r.get('run_started_at') or r.get('created_at')))
    if not recent:
        return [f'  {shown:<26} no run in the last {RUN_WINDOW_HOURS} hours']
    lines, requested = [], None
    for r in recent:
        start = _utc(r.get('run_started_at') or r.get('created_at'))
        if start is None:  # the window filter above already left these out
            continue
        note = ''
        if r.get('event') == 'workflow_dispatch':
            how, requested = 'requested', start
        elif r.get('event') == 'schedule':
            how = 'schedule'
            if requested and start - requested < timedelta(hours=LATE_COPY_HOURS):
                lag = start - requested
                note = (f'  <- GitHub\'s late copy, {lag.seconds // 3600}h'
                        f'{lag.seconds % 3600 // 60:02d}m after the requested run')
        else:
            how = r.get('event') or '?'
        result = r.get('conclusion') or r.get('status') or '?'
        lines.append(f'  {shown:<26} {start:%a %d %H:%M} UTC  {how:<9}  {result}{note}')
    return lines


def github_state(get: Callable[[str], Any] = _get_json, now: datetime | None = None) -> None:
    """The unattended jobs and the open pull requests and issues, read from
    GitHub. Never raises: a failed read is printed as one, and the session
    goes on with what git can tell it."""
    sys.path.insert(0, str(REPO))
    from src.pipeline.recent_runs import WATCHED  # the one list of unattended jobs

    now = now or datetime.now(UTC)
    section(f'GitHub, read from the public API at {now:%Y-%m-%d %H:%M} UTC')
    try:
        print(f'  Unattended jobs, last {RUN_WINDOW_HOURS} hours ("requested" is '
              'cron-job.org on time, or a run by hand):')
        for workflow, shown in {**WATCHED, **SPORT_WATCHED}.items():
            runs = get(f'{API}/repos/{SLUG}/actions/workflows/{workflow}/runs?per_page=15')
            for line in run_lines(runs.get('workflow_runs', []), shown, now):
                print('  ' + line)

        pulls = get(f'{API}/repos/{SLUG}/pulls?state=all&sort=created&direction=desc&per_page=30')
        qb = [p for p in pulls if (p.get('head') or {}).get('ref', '').startswith('qb-overrides')]
        print('\n  QB override routine (Mon and Wed 22:00 UTC), its latest pull request:')
        if qb:
            p = qb[0]
            state = 'merged' if p.get('merged_at') else p.get('state')
            print(f'    #{p["number"]} {p["title"]} -- opened {p["created_at"]}, {state}')
        else:
            print('    none among the last 30 pull requests')

        open_prs = [p for p in pulls if p.get('state') == 'open']
        print('\n  Open pull requests:' + ('' if open_prs else ' none'))
        for p in open_prs:
            print(f'    #{p["number"]} {p["title"]} ({p["head"]["ref"]})')

        issues = [i for i in get(f'{API}/repos/{SLUG}/issues?state=open&per_page=30')
                  if 'pull_request' not in i]
        print('\n  Open issues (every unattended failure and a drift flag open one):'
              + ('' if issues else ' none'))
        for i in issues:
            print(f'    #{i["number"]} {i["title"]} -- opened {i["created_at"]}')
        print('\n  The Weekly update\'s "DRIFT CHECK:" line is in its run summary, which')
        print('  this API does not serve. A flag opens "Model drift detected" above.')
    except Exception as exc:  # an orientation tool reports, never dies
        print(f'  COULD NOT READ GitHub ({type(exc).__name__}: {exc}).')
        print('  Nothing above this line is affected; check the Actions tab by hand.')


def print_context() -> None:
    """Print docs/context.md in full, rather than telling you to go read it.

    It is capped at 70 non-blank lines by tests/test_workflow_docs.py for
    exactly this reason: it is meant to fit on a screen, so a reading list that
    points at a one-screen file is a pointless extra step. CLAUDE.md is not
    printed -- it is ~430 lines and mostly durable, so it is read on demand,
    and so are docs/traps.md and docs/stage-history.md.

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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--skip-tests', action='store_true')
    ap.add_argument('--offline', action='store_true',
                    help='do not read GitHub (the test suite always passes this)')
    args = ap.parse_args(argv)

    # docs/context.md is written by whoever last had an opinion, and this
    # prints it verbatim. On Windows a redirected stdout defaults to cp1252,
    # which cannot encode an arrow, a curly quote or an em-dash in some
    # code pages -- so a single typographic character in a DOCUMENT was able
    # to crash the first command of every session with a UnicodeEncodeError
    # partway through the file. That happened, on 2026-09-12, to a '->' the
    # author had typed as a real arrow.
    #
    # The tests already pinned PYTHONIOENCODING=utf-8 at both ends, which is
    # exactly why they never caught it: the fixture was more careful than the
    # environment it was standing in for. An orientation tool must not be
    # able to die on the contents of the file it exists to show you.
    for stream in (sys.stdout, sys.stderr):
        try:
            getattr(stream, 'reconfigure')(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError, OSError):
            pass

    print('Session start -- {}'.format(datetime.now().strftime('%Y-%m-%d %H:%M')))
    print('=' * 60)
    repo_state()
    branches()
    context_file()
    suite(args.skip_tests)
    if not args.offline:
        github_state()

    print_context()

    section('Read next')
    print('  CLAUDE.md      methodology, environment, the PR loop. ~430 lines,')
    print('                 pointed at rather than printed -- but READ IT.')
    print('  docs/traps.md  where the expensive lessons are; read it before a PR,')
    print('                 a measurement or a mutation run.')
    print('  docs/index.md  only if you need to find something')
    print('  memory/        only to answer "why did we decide that"')
    if args.offline:
        print('\n  Pull-request state is NOT shown above: --offline, and there is no gh')
        print('  CLI here to ask instead. A guessed PR status is the kind of claim this')
        print('  project exists to avoid. Check open PRs on GitHub before starting new work.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
