"""tasks.py is the one place the repository's commands live (Stage 31 item 13).

A task runner is only worth having if it runs what CI and the wrap-up run.
Each test here holds one task to the file it copies, so a workflow that
changes its command without tasks.py changing too goes red, rather than
leaving a fifteenth spelling of the same command.

Nothing here runs a real command: main() takes the function that would.

Run with: pytest tests/test_tasks.py -v
"""
import re
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import tasks  # noqa: E402

WF = ROOT / '.github' / 'workflows'


def commands(name, extra=()):
    """The commands a task runs, with the interpreter written as `python`."""
    return [' '.join('python' if part == tasks.PY else part for part in cmd)
            for cmd in tasks.TASKS[name][1](list(extra))]


def runs(workflow):
    return re.findall(r'(?m)^\s*run:\s*(.+)$', (WF / workflow).read_text(encoding='utf-8'))


def test_lint_is_what_run_tests_runs():
    assert commands('lint') == ['ruff check .']
    assert 'ruff check .' in runs('run-tests.yml')


def test_check_is_lint_then_the_suite():
    assert commands('check') == ['ruff check .', commands('test')[0]]


def test_the_suite_command_is_claude_mds_and_collects_what_the_gate_does():
    """CLAUDE.md's `Suite:` line quotes `python -B -m pytest -q -p
    no:cacheprovider`, and session_wrapup.py checks that figure with
    `-B -m pytest -q`. The cache plugin changes nothing about what is
    collected, so both give the same count; the task is CLAUDE.md's spelling,
    and a gate that stopped running the same pytest would fail here."""
    claude = (ROOT / 'CLAUDE.md').read_text(encoding='utf-8')
    assert '`python -B -m pytest -q -p no:cacheprovider`' in claude
    wrapup = (ROOT / 'src' / 'session_wrapup.py').read_text(encoding='utf-8')
    assert "[sys.executable, '-B', '-m', 'pytest', '-q'" in wrapup
    assert commands('test') == ['python -B -m pytest -q -p no:cacheprovider']


def test_build_is_what_the_pages_workflow_runs():
    assert commands('build') == ['python src/generate_dashboard.py']
    assert 'python src/generate_dashboard.py' in runs('deploy-pages.yml')


def test_browser_check_runs_what_the_workflow_runs_in_the_same_order():
    got = commands('browser-check')
    wf = [r for r in runs('browser-checks.yml') if 'generate_dashboard' in r or 'check_page.py' in r]
    assert [c.split(' --axe')[0] for c in got] == [
        'python src/generate_dashboard.py',
        'python tests/browser/check_page.py --self-test',
        'python tests/browser/check_page.py index.html']
    assert [w.split(' --axe')[0] for w in wf] == [
        'python src/generate_dashboard.py',
        'python tests/browser/check_page.py --self-test',
        'python tests/browser/check_page.py index.html']


def test_the_mutation_slice_is_the_nightly_slice():
    wf = (WF / 'nightly-mutation.yml').read_text(encoding='utf-8')
    n = re.search(r'runner\.py --sample (\d+)', wf).group(1)
    assert commands('mutation-slice', ['--seed', '20260929']) == [
        f'python -B tests/mutation/runner.py --sample {n} --seed 20260929']
    assert re.fullmatch(r'python -B tests/mutation/runner.py --sample \d+ --seed \d{8}',
                        commands('mutation-slice')[0]), 'no seed defaults to the UTC date'


def test_the_first_failure_stops_the_task_with_its_code():
    seen = []

    def fake(cmd, cwd):
        seen.append(cmd)
        return SimpleNamespace(returncode=3 if cmd[0] == 'ruff' else 0)

    assert tasks.main(['check'], run=fake) == 3
    assert len(seen) == 1, 'the suite ran after lint failed'


def test_an_unknown_task_is_refused_and_no_task_lists_them(capsys):
    assert tasks.main(['tset'], run=lambda *a, **k: None) == 2
    assert tasks.main([], run=lambda *a, **k: None) == 0
    out = capsys.readouterr().out
    for name in tasks.TASKS:
        assert name in out


def test_the_readme_points_at_it():
    text = (ROOT / 'README.md').read_text(encoding='utf-8')
    assert 'python tasks.py' in text, "README's Running the tests does not mention tasks.py"
