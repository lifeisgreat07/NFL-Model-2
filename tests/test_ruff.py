"""ruff runs on every PR and push to main, with the pyflakes rules only
(Stage 27 item 3, from the 2026-09-28 audit).

The rules catch mistakes -- an undefined name, an unused import, a variable
assigned and never read, an f-string with nothing in it -- and no style, so
turning them on asked for no reformat. The first run found 22, fixed in the
same PR. The lint itself runs in CI (run-tests.yml); these tests hold the
three pieces that make it run: the config, the pin and the step.

Run with: pytest tests/test_ruff.py -v
"""
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_config_selects_the_pyflakes_rules_and_nothing_else():
    cfg = tomllib.loads((ROOT / 'ruff.toml').read_text(encoding='utf-8'))
    assert cfg.get('lint', {}).get('select') == ['F'], cfg
    assert 'extend-select' not in cfg.get('lint', {}), 'style rules crept in'
    assert 'ignore' not in cfg.get('lint', {}), 'a pyflakes rule is switched off'


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
