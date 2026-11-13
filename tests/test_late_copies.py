"""Stage 93 item 19: each copy GitHub's cron starts for a lock-writing run is
recorded, and the weekly digest says how close the latest came to the slack.

Run with: pytest tests/test_late_copies.py -v
"""
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.core import line_judge_digest as d
from src.core import start_delay as sd
from src.sports.nba import lock as nba_lock
from src.sports.nfl import weekly_update
from src.sports.nhl import lock as nhl_lock

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 9, 9, 0, tzinfo=UTC)


def run_start_delay(monkeypatch, tmp_path, workflow, now, event='schedule', on_runner=True):
    monkeypatch.chdir(tmp_path)
    wf = tmp_path / workflow
    wf.write_text((ROOT / '.github' / 'workflows' / workflow).read_text(encoding='utf-8'), encoding='utf-8')
    monkeypatch.setenv('GITHUB_EVENT_NAME', event)
    monkeypatch.delenv('CRON_SCHEDULE', raising=False)
    monkeypatch.delenv('GITHUB_STEP_SUMMARY', raising=False)
    if on_runner:
        monkeypatch.setenv('GITHUB_ACTIONS', 'true')
    else:
        monkeypatch.delenv('GITHUB_ACTIONS', raising=False)
    assert sd.main([str(wf)], now=now) == 0


def test_a_copy_github_started_is_recorded_with_its_delay(monkeypatch, tmp_path):
    exprs = sd.crons((ROOT / '.github/workflows/nfl-weekly-update.yml').read_text(encoding='utf-8'))
    slot, _ = sd.latest_slot(exprs, datetime(2026, 11, 5, 18, 0, tzinfo=UTC))
    run_start_delay(monkeypatch, tmp_path, 'nfl-weekly-update.yml', slot + timedelta(hours=4, minutes=7))
    (entry,) = json.loads((tmp_path / 'data/nfl/run_delays.json').read_text(encoding='utf-8'))
    assert entry['workflow'] == 'nfl-weekly-update.yml' and entry['delay_minutes'] == 247


@pytest.mark.parametrize('event, on_runner', [('workflow_dispatch', True), ('schedule', False)],
                         ids=['a-dispatch', 'off-a-runner'])
def test_a_dispatch_or_a_local_run_records_nothing(monkeypatch, tmp_path, event, on_runner):
    run_start_delay(monkeypatch, tmp_path, 'nhl-daily.yml', NOW, event=event, on_runner=on_runner)
    assert not (tmp_path / 'data').exists()


def test_the_record_keeps_sixty_days(tmp_path):
    path = tmp_path / 'r.json'
    old = datetime(2026, 8, 1, tzinfo=UTC)
    sd.record(path, 'nhl-daily.yml', old, old + timedelta(hours=3))
    kept = sd.record(path, 'nhl-daily.yml', NOW - timedelta(hours=5), NOW)
    assert [e['delay_minutes'] for e in kept] == [300]


def write(root, sport, *delays_hours, days_ago=1):
    path = root / 'data' / sport / 'run_delays.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    started = (NOW - timedelta(days=days_ago)).strftime('%Y-%m-%dT%H:%M:%SZ')
    path.write_text(json.dumps([{'workflow': 'x', 'slot': started, 'started': started,
                                 'delay_minutes': int(h * 60)} for h in delays_hours]), encoding='utf-8')


def test_an_nfl_copy_seven_and_a_half_hours_late_fails_the_digest(tmp_path, capsys):
    write(tmp_path, 'nfl', 3, 7.5)
    posted = []
    assert d.main([], now=NOW, api=lambda p: [], post=lambda t, b: posted.append(b), root=tmp_path) == 1
    assert '- NFL: 2 copies started by GitHub\'s cron in the last 30 days, the latest 7h 30m after its slot, ' \
           'against a lock slack of 8 hours: within an hour of it.' in posted[0]
    assert 'LATE COPIES: NFL came within an hour of the lock slack.' in capsys.readouterr().out


def test_copies_well_inside_the_slack_or_older_than_thirty_days_pass(tmp_path):
    write(tmp_path, 'nfl', 6.9)
    write(tmp_path, 'nhl', 7.5, days_ago=31)
    posted = []
    assert d.main([], now=NOW, api=lambda p: [], post=lambda t, b: posted.append(b), root=tmp_path) == 0
    assert '- NHL: no copy started by GitHub\'s cron in the last 30 days.' in posted[0]


def test_a_day_sport_copy_past_its_slack_is_reported_not_failed(tmp_path):
    write(tmp_path, 'nba', 4)
    posted = []
    assert d.main([], now=NOW, api=lambda p: [], post=lambda t, b: posted.append(b), root=tmp_path) == 0
    assert '- NBA: 1 copy started by GitHub\'s cron in the last 30 days, the latest 4h 00m after its slot, ' \
           'against a lock slack of 1 hour: within an hour of it.' in posted[0]


def test_the_slacks_are_the_locks_own():
    assert d.SLACK_HOURS['nfl'] == weekly_update.LOCK_SLACK / timedelta(hours=1)
    assert d.SLACK_HOURS['nhl'] == nhl_lock.SLACK / timedelta(hours=1)
    assert d.SLACK_HOURS['nba'] == nba_lock.SLACK / timedelta(hours=1)
    assert set(sd.RECORD_FOR) == {'nhl-daily.yml', 'nba-daily.yml', 'nfl-weekly-update.yml'}
    for wf in sd.RECORD_FOR:
        text = (ROOT / '.github' / 'workflows' / wf).read_text(encoding='utf-8')
        assert f'python -m src.core.start_delay .github/workflows/{wf}' in text
        sport = wf.split('-', 1)[0]
        assert sd.record_path(wf).as_posix() == f'data/{sport}/run_delays.json'
        assert f'data/{sport}' in text, f'{wf} does not commit data/{sport}, so its record would be lost'
