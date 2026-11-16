"""The NFL board's "Worth a look" box is not drawn when it is hidden (audit 9, finding D5).

`.board-insights` sets a display value, which outranks the browser's rule for the `hidden` attribute, so the box
needs its own `[hidden]` rule. The rendered proof, for this box and for anything else marked hidden, is
`tests/browser/check_hidden.py` in the Browser checks workflow.

Run with: pytest tests/test_hidden_stays_hidden.py -v
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
BODY = (ROOT / 'src' / 'dashboard' / 'body.html').read_text(encoding='utf-8')
WORKFLOW = (ROOT / '.github' / 'workflows' / 'browser-checks.yml').read_text(encoding='utf-8')


def test_the_box_starts_hidden_and_its_class_sets_a_display_value():
    """The two facts that make the rule necessary: if either stops being true, this file can go."""
    assert '<div class="board-insights" id="board-insights" hidden>' in BODY
    [box] = re.findall(r'(?m)^\s*\.board-insights\{([^}]*)\}', CSS)
    assert 'display:grid' in box


def test_the_hidden_box_has_a_rule_that_hides_it_after_the_rule_that_draws_it():
    hide = CSS.index('.board-insights[hidden]{display:none;}')
    assert hide > CSS.index('.board-insights{'), 'equal weight would not matter, but keep the pair together'


def test_the_browser_checks_run_the_hidden_check_on_all_three_sport_pages_and_prove_it_can_fail():
    assert 'python tests/browser/check_hidden.py --self-test --tmp "$RUNNER_TEMP/hidden"' in WORKFLOW
    assert ('python tests/browser/check_hidden.py index.html "$RUNNER_TEMP/states/nhl.html" '
            '"$RUNNER_TEMP/states/nba.html"') in WORKFLOW
