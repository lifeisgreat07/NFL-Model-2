"""
Stage 83 item 4: an input the NBA or NHL daily run could not read is said on a
line starting DEGRADED:, and the workflow raises an issue on any such line.

Run with: pytest tests/test_degraded_inputs.py -v
"""
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.sports.nba import daily as nba
from src.sports.nhl import daily as nhl

ROOT = Path(__file__).resolve().parents[1]


def down(_url):
    raise OSError('connection refused')


def test_the_nba_says_degraded_for_injuries_and_odds(capsys):
    assert nba.read_injuries(down, {'ATL'}) is None
    assert nba.read_espn_odds('401', down) is None
    lines = capsys.readouterr().out.splitlines()
    assert [ln.split(':')[0] for ln in lines] == ['DEGRADED', 'DEGRADED']


def test_the_nhl_says_degraded_for_injuries_odds_and_rosters(capsys):
    assert nhl.read_injuries(2026, down) is None
    assert nhl.read_market(down, datetime(2026, 11, 2, tzinfo=UTC))[0] == []
    assert nhl.read_rosters({'TBL'}, down) == {'TBL': None}
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    assert lines and all(ln.startswith('DEGRADED: ') for ln in lines), lines
    assert len(lines) == 3


@pytest.mark.parametrize('sport', ['nba', 'nhl'])
def test_the_workflow_raises_an_issue_on_a_degraded_line(sport):
    text = (ROOT / '.github' / 'workflows' / f'{sport}-daily.yml').read_text(encoding='utf-8')
    step = text[text.index('- name: Raise an alert on an input the run could not read'):]
    step = step[:step.index('\n      - name:')]
    assert f"grep -q '^DEGRADED:' {sport}-daily.log" in step
    assert f'--title "{sport.upper()}: the daily run could not read an input"' in step
    assert 'if: success()' in step
