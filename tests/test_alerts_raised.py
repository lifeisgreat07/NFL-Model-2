"""Every alert a workflow closes on a good run, it also raises on a bad one.

The recovery steps (`python -m src.core.alerts --resolve --title "..."`) name
each alert's title, so a test that only looked for the title passed with the
raise itself gone: three mutation cases that drop a raise SURVIVED on main
(nba-daily-silent-failure, nba-canary-unnamed-failure-silent,
nhl-canary-alert-dropped; found 2026-11-23). This holds the pairing for every
workflow: a title closed with `--resolve` is raised somewhere in the same file
by a line without it.

Run with: pytest tests/test_alerts_raised.py -v
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / '.github' / 'workflows').glob('*.yml'))
RESOLVED = re.compile(r'python -m src\.core\.alerts --resolve --title "([^"]+)"')


def text(path):
    return path.read_text(encoding='utf-8').replace('\r\n', '\n')


def unraised(t):
    """The titles `t` closes with --resolve and never raises with a `--body-file`."""
    return [title for title in RESOLVED.findall(t)
            if not re.search(rf'python -m src\.core\.alerts --title "{re.escape(title)}" --body-file \S', t)]


@pytest.mark.parametrize('path', WORKFLOWS, ids=lambda p: p.name)
def test_every_alert_a_workflow_resolves_it_also_raises(path):
    missing = unraised(text(path))
    assert not missing, f'{path.name} closes {missing} on a good run and never raises them on a bad one'


def test_the_rule_reads_the_workflows_and_can_fail():
    resolved = [title for p in WORKFLOWS for title in RESOLVED.findall(text(p))]
    assert len(resolved) >= 5, f'only {resolved}: the pattern no longer matches the recovery steps'
    t = ('python -m src.core.alerts --resolve --title "X: failing" --body-file ok.md\n'
         'echo "X: failing"\n')
    assert unraised(t) == ['X: failing']
    assert unraised(t + 'python -m src.core.alerts --title "X: failing" --body-file bad.md\n') == []
