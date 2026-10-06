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
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
AXE = 'node_modules/axe-core/axe.min.js'
# Where browser-check builds the states pages (a tie, a skipped week, a stale
# preview). Outside the checkout, like CI's $RUNNER_TEMP/states, so nothing
# built here is ever staged. The page names are build_states.PAGES.
STATES = Path(tempfile.gettempdir()) / 'nfl-model-states'
STATE_PAGES = ('states_tie.html', 'states_preview.html')
# The NHL's page, built from a sample week (tests/browser/build_nhl.py) beside them.
NHL_PAGE = 'nhl.html'
# The NBA's page, built from the committed backtest (src/sports/nba/site.py).
NBA_PAGE = 'nba.html'
# The type check run-tests.yml runs (Stage 35).
TYPES = [PY, '-m', 'mypy', '--ignore-missing-imports', 'src/pipeline/weekly_update.py', 'src/pipeline/ratings_engine.py']
# The strict type check over the agents (Stage 48 item 19). --follow-imports=silent
# checks src/agents alone: the pipeline modules it imports are not strict yet.
AGENT_TYPES = [PY, '-m', 'mypy', '--strict', '--ignore-missing-imports', '--follow-imports=silent', 'src/agents']


def _slice_seed(argv):
    if '--seed' in argv:
        return argv[argv.index('--seed') + 1]
    return datetime.now(UTC).strftime('%Y%m%d')


def _axe():
    return ['--axe', AXE] if (ROOT / AXE).exists() else []


#: name -> (what it is, function from extra argv to the list of commands).
TASKS = {
    'test': ('the whole suite, as CLAUDE.md\'s Suite line quotes it',
             lambda a: [[PY, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider']]),
    'lint': ('ruff, then mypy over the weekly run\'s two core modules and strict mypy over the '
             'agents, as run-tests.yml runs them',
             lambda a: [['ruff', 'check', '.'], TYPES, AGENT_TYPES]),
    'check': ('lint, then the suite: the four things run-tests.yml runs',
              lambda a: [['ruff', 'check', '.'], TYPES, AGENT_TYPES,
                         [PY, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider']]),
    'build': ('build index.html from the data on disk (deploy-pages.yml does this)',
              lambda a: [[PY, '-m', 'src.pipeline.generate_dashboard']]),
    'browser-check': ('build, prove every browser rule can fail, check the page, then build '
                      'and check the states pages and the NHL\'s and NBA\'s pages (needs Playwright and node; axe-core is '
                      'used when node_modules has it)',
                      lambda a: [[PY, '-m', 'src.pipeline.generate_dashboard'],
                                 [PY, 'tests/browser/check_page.py', '--self-test', *_axe()],
                                 [PY, 'tests/browser/check_page.py', 'index.html', *_axe()],
                                 [PY, 'tests/browser/build_states.py', '--out', str(STATES)],
                                 *[[PY, 'tests/browser/check_page.py', str(STATES / page), *_axe()]
                                   for page in STATE_PAGES],
                                 [PY, 'tests/browser/build_nhl.py', '--out', str(STATES / NHL_PAGE)],
                                 [PY, 'tests/browser/check_page.py', str(STATES / NHL_PAGE), *_axe()],
                                 [PY, '-m', 'src.sports.nba.site', '--out', str(STATES / NBA_PAGE)],
                                 [PY, 'tests/browser/check_page.py', str(STATES / NBA_PAGE), *_axe()]]),
    'mutation-slice': ('30 mutation cases chosen by a date seed, as the nightly job runs '
                       '(--seed YYYYMMDD to replay a night)',
                       lambda a: [[PY, '-B', 'tests/mutation/runner.py', '--sample', '30',
                                   '--seed', _slice_seed(a)]]),
    'mutation-all': ('every mutation case; well over an hour, and nothing else may use '
                     'the checkout while it runs',
                     lambda a: [[PY, '-B', 'tests/mutation/runner.py']]),
    'wrapup': ('the end-of-session gate', lambda a: [[PY, '-m', 'src.agents.session_wrapup']]),
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
