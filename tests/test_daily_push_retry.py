"""The NHL and NBA daily runs retry a refused push and keep their picks if it still fails.

Six workflows push to main. A daily run's push refused as non-fast-forward
used to end the run with the slate's picks unsaved, and since a pick is
written once, before its game, a later run cannot make it again (Stage 68
item 2, the 2026-10-09 audit, E2).

Run with: pytest tests/test_daily_push_retry.py -v
"""
import re
from pathlib import Path

import pytest

WF = Path(__file__).resolve().parents[1] / '.github' / 'workflows'
SPORTS = ('nhl', 'nba')


def text(sport):
    return (WF / f'{sport}-daily.yml').read_text(encoding='utf-8').replace('\r\n', '\n')


def step(t, name):
    start = t.index(f'      - name: {name}')
    nxt = t.find('\n      - name:', start + 1)
    return t[start:nxt if nxt != -1 else None]


@pytest.mark.parametrize('sport', SPORTS)
def test_the_push_is_retried_after_a_rebase(sport):
    s = step(text(sport), f"Commit the {sport.upper()}'s picks, grades and history")
    loop = re.search(r'for try in 1 2 3; do\n(.*?)\n\s+done\n', s, re.S)
    assert loop, 'no three-try push loop'
    body = loop.group(1)
    assert 'if git push origin HEAD:main; then exit 0; fi' in body
    assert 'pull --rebase origin main' in body
    assert body.index('git push') < body.index('pull --rebase'), 'push first, rebase only after a refusal'
    assert re.search(r'done\n\s+echo "push refused three times"\n\s+exit 1\n', s), 'a final refusal must fail'
    assert s.count('git push') == 1, 'one push, inside the loop'


@pytest.mark.parametrize('sport', SPORTS)
def test_a_failed_run_keeps_its_picks_as_an_artifact(sport):
    t = text(sport)
    name = f"Keep the {sport.upper()}'s picks when the run failed"
    s = step(t, name)
    assert re.search(r'^\s+if: failure\(\)$', s, re.M)
    assert 'uses: actions/upload-artifact@' in s
    assert f'            predictions/{sport}\n' in s
    assert t.index(f"Commit the {sport.upper()}'s") < t.index(name) < t.index('      - name: Raise an alert\n')
