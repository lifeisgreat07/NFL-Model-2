"""ruff runs on every PR and push to main (Stage 27 item 3, from the
2026-09-28 audit), with the pyflakes rules, import order and upgrades
(Stage 32 item 18's tail, from the 2026-09-29 re-audit).

The pyflakes rules catch mistakes -- an undefined name, an unused import, a
variable assigned and never read, an f-string with nothing in it. `I` and
`UP` were added after one dry run and applied in the same PR; both are
auto-fixed, so neither asks anyone for a hand reformat. RUF100 (Stage 36,
the 2026-10-04 fourth audit) removes a `noqa` that silences nothing, also
auto-fixed. UP031 is the one
rule left off, for a reason ruff.toml states. The lint itself runs in CI
(run-tests.yml); these tests hold the pieces that make it run: the config,
the Python it targets, the pin and the step.

Run with: pytest tests/test_ruff.py -v
"""
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _config():
    return tomllib.loads((ROOT / 'ruff.toml').read_text(encoding='utf-8'))


def test_the_config_selects_the_agreed_rules_and_nothing_else():
    lint = _config().get('lint', {})
    assert lint.get('select') == ['F', 'I', 'UP', 'RUF100'], lint
    assert 'extend-select' not in lint, 'style rules crept in'
    assert lint.get('ignore', []) == ['UP031'], 'a rule is switched off beyond the one ruff.toml explains'


def test_the_upgrades_target_the_python_the_project_runs():
    """UP rewrites code into the newest syntax its target allows; a target
    newer than the runtime would write code the runtime cannot import."""
    want = 'py' + (ROOT / '.python-version').read_text(encoding='utf-8').strip().replace('.', '')
    assert _config().get('target-version') == want


def test_ruff_is_pinned_with_the_test_requirements():
    reqs = (ROOT / 'requirements-dev.txt').read_text(encoding='utf-8')
    assert re.search(r'(?m)^ruff==\d+\.\d+\.\d+$', reqs), 'ruff is not pinned in requirements-dev.txt'


def test_the_test_workflow_lints_the_whole_repository_before_the_tests():
    wf = (ROOT / '.github' / 'workflows' / 'run-tests.yml').read_text(encoding='utf-8')
    install = wf.index('pip install -r requirements.txt -r requirements-dev.txt')
    lint = re.search(r'(?m)^\s+run: ruff check \.\s*$', wf)
    assert lint, 'run-tests.yml does not run `ruff check .`'
    tests = wf.index('python -m pytest')
    assert install < lint.start() < tests
