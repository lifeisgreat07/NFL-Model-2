"""
Stage 93 item 16 (audit 7, R18): a day sport's failure alert names the
artifact that holds the picks the run made, and says to commit them only
before the first of their games starts, never after.

The run keeps its picks in an artifact when it fails (`if: failure()`), but
the issue only linked the run, so whoever read it at 7am had to know the
artifact existed, find it, and know that a pick committed after its game
started is not a prediction.

Run with: pytest tests/test_failure_body.py -v
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def steps(sport):
    text = (ROOT / '.github' / 'workflows' / f'{sport}-daily.yml').read_text(encoding='utf-8')
    return text.split('\n      - ')


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_the_failure_alert_names_the_artifact_the_run_keeps(sport):
    s = steps(sport)
    (keep,) = [x for x in s if x.startswith(f"name: Keep the {sport.upper()}'s picks when the run failed")]
    assert re.search(rf'name: {sport}-daily-\$\{{\{{ github\.run_id \}}\}}\n', keep)
    (alert,) = [x for x in s if x.startswith('name: Raise an alert\n')]
    assert 'if: failure()' in alert
    assert f'"{sport}-daily-$GITHUB_RUN_ID"' in alert
    assert f'predictions/{sport}, results/{sport} and data/{sport}' in alert
    for folder in (f'predictions/{sport}', f'results/{sport}', f'data/{sport}'):
        assert folder in keep, folder


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_it_says_when_they_may_be_committed(sport):
    (alert,) = [x for x in steps(sport) if x.startswith('name: Raise an alert\n')]
    assert 'Commit them only before the first of their games starts, never after' in alert
    assert 'the next run marks the games missed' in alert
    assert alert.index('> failure.md') < alert.index('--body-file failure.md')
