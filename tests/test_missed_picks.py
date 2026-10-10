"""A daily game that starts with no saved pick is never silent (Stage 68 item 3).

The NHL and NBA save each pick once, at the last run before the game, with
an hour of slack. A run that starts late, or fails, can leave a game
unpicked, and nothing used to say so: main printed only "started N". Now it
prints a MISSED PICKS line, the workflow raises an alert on it, and the
start delay of a daily run is measured against the cron line that fired and
warned at the lock's own hour of slack.

Run with: pytest tests/test_missed_picks.py -v
"""
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.core import start_delay as sd
from src.sports.nba import daily as nba_daily
from src.sports.nba import lock as nba_lock
from src.sports.nhl import daily as nhl_daily
from src.sports.nhl import lock as nhl_lock

WF = Path(__file__).resolve().parents[1] / '.github' / 'workflows'
DAILY = {'nhl': nhl_daily, 'nba': nba_daily}
LOCK = {'nhl': nhl_lock, 'nba': nba_lock}


def text(sport):
    return (WF / f'{sport}-daily.yml').read_text(encoding='utf-8').replace('\r\n', '\n')


def step(t, name):
    start = t.index(f'      - name: {name}\n')
    nxt = t.find('\n      - name:', start + 1)
    return t[start:nxt if nxt != -1 else None]


@pytest.mark.parametrize('sport', DAILY)
def test_a_started_game_with_no_pick_file_is_missed(sport, tmp_path):
    (tmp_path / '101.json').write_text('{}', encoding='utf-8')
    assert DAILY[sport].missed(('103', '101', '102'), tmp_path) == ['102', '103']
    assert DAILY[sport].missed((), tmp_path) == []
    assert DAILY[sport].missed(('101',), tmp_path / 'not-yet-made') == ['101']


@pytest.mark.parametrize('sport', DAILY)
def test_main_prints_the_line_the_alert_reads(sport, tmp_path):
    (tmp_path / '101.json').write_text('{}', encoding='utf-8')
    line = DAILY[sport].missed_line(('102', '101'), tmp_path)
    assert line == 'MISSED PICKS: 1 started with no saved pick: 102'
    assert re.match(r'^MISSED PICKS:', line), 'the workflow greps for this prefix'
    assert DAILY[sport].missed_line(('101',), tmp_path) is None
    src = Path(DAILY[sport].__file__).read_text(encoding='utf-8')
    assert 'lost = missed_line(decision.started, folder)\n    if lost:\n        print(lost)\n' in src


@pytest.mark.parametrize('sport', DAILY)
def test_the_workflow_raises_the_alert_on_that_line(sport):
    t = text(sport)
    s = step(t, 'Raise an alert on a missed pick')
    assert re.search(r'^\s+if: success\(\)$', s, re.M)
    assert f"grep -q '^MISSED PICKS:' {sport}-daily.log" in s
    assert f'--title "{sport.upper()}: a game started with no saved pick"' in s
    assert t.index("      - name: Commit the") < t.index('Raise an alert on a missed pick') < t.index(
        '      - name: Raise an alert\n')


@pytest.mark.parametrize('sport', DAILY)
def test_a_daily_run_is_warned_at_its_lock_slack(sport):
    assert timedelta(hours=sd.WARN_HOURS_FOR[f'{sport}-daily.yml']) == LOCK[sport].SLACK


@pytest.mark.parametrize('sport', DAILY)
def test_the_daily_workflow_passes_the_cron_line_that_fired(sport):
    s = step(text(sport), 'Record the start delay')
    assert 'CRON_SCHEDULE: ${{ github.event.schedule }}' in s


def test_a_late_copy_is_measured_against_its_own_slot():
    wf = text('nhl')
    at = datetime(2026, 10, 10, 21, 20, tzinfo=UTC)
    line, warn = sd.report(wf, at, 'schedule', '0 14 * * *', 1)
    assert line.startswith("Start delay: 7h 20m after the Sat 14:00 UTC slot (cron '0 14 * * *')") and warn
    line, warn = sd.report(wf, at, 'schedule', None, 1)
    assert line.startswith('Start delay: 0h 20m after the Sat 21:00 UTC slot') and not warn


def test_a_dispatch_ignores_a_schedule_it_was_not_given():
    wf = text('nhl')
    line, _ = sd.report(wf, datetime(2026, 10, 10, 21, 2, tzinfo=UTC), 'workflow_dispatch', '0 14 * * *', 1)
    assert 'after the Sat 21:00 UTC slot' in line


def test_main_reads_the_schedule_and_the_threshold(tmp_path, monkeypatch, capsys):
    wf = tmp_path / 'nhl-daily.yml'
    wf.write_text(text('nhl'), encoding='utf-8')
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'schedule')
    monkeypatch.setenv('CRON_SCHEDULE', '0 21 * * *')
    monkeypatch.delenv('GITHUB_STEP_SUMMARY', raising=False)
    assert sd.main([str(wf)], now=datetime(2026, 10, 10, 22, 5, tzinfo=UTC)) == 0
    out = capsys.readouterr().out
    assert '::warning title=Late start::Start delay: 1h 05m' in out and 'Warned at 1 hours.' in out
