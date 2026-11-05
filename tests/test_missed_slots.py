"""Stage 93 item 20: the page build looks for a missed daily slot itself.

Run with: pytest tests/test_missed_slots.py -v
"""
import json
from datetime import UTC, datetime
from pathlib import Path

from src.site import missed_slots

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 5, 3, 0, tzinfo=UTC)  # 22:00 on the 4th, US Eastern


def world(tmp_path, as_of='2026-11-04', picked=('2026020150',), extra=()):
    games = [{'game_id': '2026020150', 'away': 'TOR', 'home': 'MTL', 'start_utc': '2026-11-05T00:00:00Z',
              'status': 'final'},
             {'game_id': '2026020151', 'away': 'BOS', 'home': 'NYR', 'start_utc': '2026-11-05T23:00:00Z',
              'status': 'scheduled'},
             {'game_id': '2026020100', 'away': 'SEA', 'home': 'VAN', 'start_utc': '2026-10-30T02:00:00Z',
              'status': 'final'}, *extra]
    res = tmp_path / 'results' / 'nhl'
    res.mkdir(parents=True)
    (res / 'schedule_2026.json').write_text(json.dumps({'as_of': as_of, 'games': games}), encoding='utf-8')
    picks = tmp_path / 'predictions' / 'nhl' / '2026'
    picks.mkdir(parents=True)
    for gid in picked:
        (picks / f'{gid}.json').write_text('{}', encoding='utf-8')
    return tmp_path


def test_a_fresh_schedule_with_every_started_game_picked_is_clean(tmp_path):
    assert missed_slots.findings('nhl', NOW, world(tmp_path)) == []


def test_yesterdays_schedule_is_still_fresh_and_the_day_before_is_not(tmp_path):
    assert missed_slots.findings('nhl', NOW, world(tmp_path, as_of='2026-11-03')) == []
    (finding,) = missed_slots.findings('nhl', NOW, world(tmp_path / 'b', as_of='2026-11-02'))
    assert finding.startswith('the schedule was last refreshed 2026-11-02, and today is 2026-11-04')


def test_a_game_that_started_with_no_pick_is_named(tmp_path):
    (finding,) = missed_slots.findings('nhl', NOW, world(tmp_path, picked=()))
    assert finding == 'game 2026020150 (TOR at MTL, 2026-11-05T00:00:00Z) started with no pick saved'


def test_a_postponed_game_and_one_outside_the_window_are_not_findings(tmp_path):
    ppd = {'game_id': '2026020149', 'away': 'NJD', 'home': 'PHI', 'start_utc': '2026-11-04T23:00:00Z',
           'status': 'postponed'}
    assert missed_slots.findings('nhl', NOW, world(tmp_path, extra=(ppd,))) == []


def test_the_alert_is_raised_and_closed_per_sport(tmp_path, monkeypatch):
    raised, closed = [], []
    monkeypatch.setattr(missed_slots.alerts, 'open_or_comment', lambda t, b: raised.append((t, b)))
    monkeypatch.setattr(missed_slots.alerts, 'close_open_issue', lambda t, b: closed.append(t))
    assert missed_slots.main(['--alert', '--run-url', 'R'], now=NOW, root=world(tmp_path, picked=())) == 0
    assert [t for t, _ in raised] == ['NHL: a daily run slot went missing']
    assert 'game 2026020150 (TOR at MTL' in raised[0][1] and 'The page still published' in raised[0][1]
    assert closed == ['NBA: a daily run slot went missing']


def test_the_deploy_runs_it_without_ever_refusing_the_build():
    text = (ROOT / '.github' / 'workflows' / 'deploy-pages.yml').read_text(encoding='utf-8')
    step = next(s for s in text.split('\n      - ') if 'src.site.missed_slots' in s)
    assert 'continue-on-error: true' in step and "if: ${{ !cancelled() }}" in step
    assert 'python -m src.site.missed_slots --alert' in step
    assert text.index('src.site.missed_slots') < text.index('Upload the Pages artifact')
