"""
src/canary.py and .github/workflows/nightly-canary.yml.

The steps are injected, so the error paths run with no network. What is
checked: one broken step does not hide the others, a crash is a finding,
the exit code follows the errors, and the workflow alerts on failure and
writes nothing to the repository.

Run with: pytest tests/test_canary.py -v
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / 'src'))

import canary  # noqa: E402
from data_quality import Report  # noqa: E402

WORKFLOW = REPO / '.github' / 'workflows' / 'nightly-canary.yml'


def _boom(state):
    raise ConnectionError('nflverse said 404')


def _warn(state):
    r = Report()
    r.warnings.append('a warning')
    return r


def _error(state):
    r = Report()
    r.errors.append('a real error')
    return r


def test_a_crashing_step_is_an_error_and_the_rest_still_run():
    ran = []
    steps = [('load', _boom), ('after', lambda s: ran.append('after') or 'fine')]
    report, notes = canary.run(2026, steps)
    assert any('load raised ConnectionError: nflverse said 404' in e for e in report.errors)
    assert ran == ['after'], 'one broken step hid the steps after it'
    assert notes[0].startswith('load: FAILED')


def test_findings_from_every_step_are_collected():
    report, _ = canary.run(2026, [('a', _warn), ('b', _error)])
    assert report.warnings == ['a warning'] and report.errors == ['a real error']


def test_warnings_alone_do_not_fail_the_canary(monkeypatch):
    monkeypatch.setattr(canary, 'default_steps', lambda: [('a', _warn)])
    assert canary.main(['--season', '2026']) == 0


def test_an_error_fails_the_canary_and_the_report_says_so(monkeypatch, tmp_path):
    monkeypatch.setattr(canary, 'default_steps', lambda: [('a', _error)])
    out = tmp_path / 'report.md'
    assert canary.main(['--season', '2026', '--report', str(out)]) == 1
    text = out.read_text(encoding='utf-8')
    assert 'FAILING' in text and 'ERROR: a real error' in text


def test_january_belongs_to_last_season():
    assert canary.current_season(datetime(2027, 1, 20, tzinfo=timezone.utc)) == 2026
    assert canary.current_season(datetime(2026, 9, 24, tzinfo=timezone.utc)) == 2026


def test_the_default_steps_are_the_weekly_data_path():
    names = [name for name, _ in canary.default_steps()]
    assert names == ['load play-by-play', 'load schedule', 'data quality',
                     'schema', 'next week']


# --- the workflow ------------------------------------------------------------

def _text():
    return WORKFLOW.read_text(encoding='utf-8')


def test_it_runs_every_night():
    assert re.search(r"cron:\s*'0 6 \* \* \*'", _text())


def test_a_failure_raises_the_alert():
    text = _text()
    alert = text[text.index('- name: Raise an alert'):]
    assert re.search(r'if:\s*failure\(\)', alert)
    assert '--title "Nightly canary failing"' in alert
    assert '--report canary-report.md' in text and '--body-file canary-report.md' in alert


def test_it_can_open_issues_and_cannot_write_the_repository():
    """The canary must never be able to touch a lock, a pick or a grade."""
    text = _text()
    block = re.search(r'^permissions:\s*\n((?:[ \t]+.+\n)+)', text, re.M)
    granted = dict(re.findall(r'(\S+):\s*(\S+)', block.group(1)))
    assert granted == {'contents': 'read', 'issues': 'write'}
    assert 'git-auto-commit' not in text and 'git push' not in text
