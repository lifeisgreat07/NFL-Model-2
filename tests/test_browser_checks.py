"""The browser-checks workflow runs the checker it claims to, the way it claims to.

Stage 12 (CLAUDE.md). tests/browser/check_page.py drives Chromium over the
built dashboard; .github/workflows/browser-checks.yml runs it in CI. The
checker needs Playwright and a browser, which this suite's machines do not
have, so its BEHAVIOUR is proven where it runs: the workflow runs
`--self-test` first, which fails unless every rule catches a page built to
break it.

What this file holds is everything that proof rests on and a static read can
check: that the workflow builds the page, proves the rules, then checks the
page, with axe-core passed to both; that the tools are pinned; and that the
checker still covers the six widths, both network conditions, and a fixture
for every rule. The checker is parsed, never imported -- importing it needs
Playwright.

Run with: pytest tests/test_browser_checks.py -v
"""
import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'browser-checks.yml'
CHECKER = ROOT / 'tests' / 'browser' / 'check_page.py'
RULES = ('overflow', 'focus', 'target', 'axe', 'font', 'error')


@pytest.fixture(scope='module')
def workflow():
    text = WORKFLOW.read_text(encoding='utf-8')
    return re.sub(r'(?m)^\s*#.*$', '', text)


@pytest.fixture(scope='module')
def checker():
    src = CHECKER.read_text(encoding='utf-8')
    return src, ast.parse(src)


def constant(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f'{name} is not a module constant in check_page.py any more')


def step_runs(workflow):
    return re.findall(r'(?m)^\s*run:\s*(.+)$', workflow)


def test_the_workflow_builds_then_proves_the_rules_then_checks_the_page(workflow):
    runs = step_runs(workflow)
    build = next(i for i, r in enumerate(runs) if 'generate_dashboard.py' in r)
    selftest = next(i for i, r in enumerate(runs) if 'check_page.py --self-test' in r)
    check = next(i for i, r in enumerate(runs) if 'check_page.py index.html' in r)
    assert build < selftest < check, (
        'the order must be: build the page, prove every rule can fail, then check '
        'the page -- a check that runs before the self-test can pass on a blind rule')


def test_axe_core_reaches_both_the_self_test_and_the_check(workflow):
    """Without --axe the axe rule is silently skipped, in both runs."""
    for r in step_runs(workflow):
        if 'check_page.py' in r:
            assert '--axe node_modules/axe-core/axe.min.js' in r, f'no axe-core in: {r}'


def test_the_tools_are_pinned(workflow):
    assert re.search(r'pip install playwright==\d+\.\d+\.\d+', workflow), 'Playwright is not pinned'
    assert re.search(r'axe-core@\d+\.\d+\.\d+', workflow), 'axe-core is not pinned'


def test_it_runs_on_changes_to_what_the_page_is_built_from(workflow):
    pr = re.search(r'pull_request:\s*\n\s*paths:\s*\n((?:\s*- .+\n)+)', workflow)
    assert pr, 'the workflow no longer runs on pull requests'
    for path in ('src/**', 'assets/**', 'tests/browser/**', '.github/workflows/browser-checks.yml'):
        assert f"'{path}'" in pr.group(1), f'a pull request changing {path} would not be checked'


def test_the_checker_covers_six_widths_and_both_network_conditions(checker):
    src, tree = checker
    assert constant(tree, 'WIDTHS') == (360, 390, 768, 1024, 1280, 1440)
    assert 'for network in (False, True):' in src, (
        'the checker no longer runs with the network both blocked and allowed')


def test_the_thresholds_are_what_the_rules_say(checker):
    _, tree = checker
    assert constant(tree, 'TARGET_MIN') == 24
    assert set(constant(tree, 'FAIL_IMPACTS')) == {'serious', 'critical'}
    budget = constant(tree, 'BYTE_BUDGET')
    assert isinstance(budget, int) and 600_000 < budget <= 1_000_000, (
        f'BYTE_BUDGET is {budget}; moving it is a decision with a reason, not a reflex')


def fixture_names(tree):
    """FIXTURES' keys. Its values are dict(...) calls, so it is not a literal."""
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == 'FIXTURES' for t in node.targets):
            return {ast.literal_eval(k) for k in node.value.keys}
    raise AssertionError('FIXTURES is not a module constant in check_page.py any more')


def test_every_rule_has_a_fixture_that_breaks_it(checker):
    """The self-test is only as wide as its fixtures."""
    _, tree = checker
    fixtures = fixture_names(tree)
    missing = [r for r in RULES if r not in fixtures]
    assert not missing, f'rules with no self-test fixture: {missing}'
    src, _ = checker
    assert "r.startswith('budget:')" in src, 'the budget rule has no self-test'


def test_the_font_is_judged_by_measured_width(checker):
    """CLAUDE.md: document.fonts.check() is true when nothing is pending."""
    src, _ = checker
    font = re.search(r'FONT_JS = """(.*?)"""', src, re.S)
    assert font, 'FONT_JS is gone -- re-anchor this guard'
    assert 'measureText' in font.group(1)
    assert 'fonts.check' not in font.group(1)
