"""One entry point for the commands this repository runs (Stage 31 item 13).

    python tasks.py                 list the tasks
    python tasks.py test            the suite, as CLAUDE.md's Suite line quotes it
    python tasks.py check           lint, then the suite -- the two things run-tests.yml runs
    python tasks.py mutation-slice  tonight's nightly slice (or --seed YYYYMMDD)

Until this file the same commands lived in README, CLAUDE.md, fourteen
workflows and a handful of docstrings, each spelled slightly differently.
Each task here is the command CI or the wrap-up actually runs, and
tests/test_tasks.py holds every one to the workflow or script it copies, so
this file cannot drift into a fifteenth spelling.

Plain Python, no dependencies: `make` is not on a Windows machine by
default, and a runner that needs installing first is one more thing to
break. Every command is printed before it runs; the first failure stops the
task with that command's exit code.
"""
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
AXE = 'node_modules/axe-core/axe.min.js'


def _slice_seed(argv):
    if '--seed' in argv:
        return argv[argv.index('--seed') + 1]
    return datetime.now(timezone.utc).strftime('%Y%m%d')


def _axe():
    return ['--axe', AXE] if (ROOT / AXE).exists() else []


#: name -> (what it is, function from extra argv to the list of commands).
TASKS = {
    'test': ('the whole suite, as CLAUDE.md\'s Suite line quotes it',
             lambda a: [[PY, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider']]),
    'lint': ('ruff, as run-tests.yml runs it',
             lambda a: [['ruff', 'check', '.']]),
    'check': ('lint, then the suite: the two things run-tests.yml runs',
              lambda a: [['ruff', 'check', '.'],
                         [PY, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider']]),
    'build': ('build index.html from the data on disk (deploy-pages.yml does this)',
              lambda a: [[PY, 'src/generate_dashboard.py']]),
    'browser-check': ('build, prove every browser rule can fail, then check the page '
                      '(needs Playwright; axe-core is used when node_modules has it)',
                      lambda a: [[PY, 'src/generate_dashboard.py'],
                                 [PY, 'tests/browser/check_page.py', '--self-test', *_axe()],
                                 [PY, 'tests/browser/check_page.py', 'index.html', *_axe()]]),
    'mutation-slice': ('30 mutation cases chosen by a date seed, as the nightly job runs '
                       '(--seed YYYYMMDD to replay a night)',
                       lambda a: [[PY, '-B', 'tests/mutation/runner.py', '--sample', '30',
                                   '--seed', _slice_seed(a)]]),
    'mutation-all': ('every mutation case; well over an hour, and nothing else may use '
                     'the checkout while it runs',
                     lambda a: [[PY, '-B', 'tests/mutation/runner.py']]),
    'wrapup': ('the end-of-session gate', lambda a: [[PY, 'src/session_wrapup.py']]),
}


def usage():
    print('python tasks.py <task>\n')
    width = max(map(len, TASKS))
    for name, (what, _) in TASKS.items():
        print(f'  {name.ljust(width)}  {what}')


def main(argv=None, run=subprocess.run):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        usage()
        return 0
    name, extra = argv[0], argv[1:]
    if name not in TASKS:
        print(f'no task {name!r}\n')
        usage()
        return 2
    for cmd in TASKS[name][1](extra):
        print('>', ' '.join(cmd), flush=True)
        code = run(cmd, cwd=ROOT).returncode
        if code:
            return code
    return 0


if __name__ == '__main__':
    sys.exit(main())
