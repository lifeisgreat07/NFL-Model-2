"""The NHL's nightly canary: every step runs, one failure does not hide the
others, and any failure fails the night.

Run with: pytest tests/test_nhl_canary.py -v
"""
import json
from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from src.sports.nhl import canary, history

NOW = datetime(2026, 10, 10, 6, 0, tzinfo=UTC)


def ok(state):
    return 'fine'


def boom(state):
    raise ValueError('the feed changed shape')


def test_a_failing_step_is_recorded_and_the_rest_still_run():
    errors, notes = canary.run(NOW, steps=[('a', boom), ('b', ok)])
    assert errors == ['a raised ValueError: the feed changed shape']
    assert notes[1] == 'b: fine' and notes[0].startswith('a: FAILED')


def test_any_error_fails_the_night_and_the_report_says_which(tmp_path, monkeypatch):
    monkeypatch.setattr(canary, 'STEPS', [('market', boom), ('roster', ok)])
    report = tmp_path / 'r.md'
    assert canary.main(['--report', str(report)], now=NOW) == 1
    text = report.read_text()
    assert '## Errors' in text and 'market raised ValueError' in text


def test_a_clean_night_passes(tmp_path, monkeypatch):
    monkeypatch.setattr(canary, 'STEPS', [('roster', ok)])
    assert canary.main([], now=NOW) == 0


def test_every_read_the_daily_run_makes_has_a_step():
    assert [name for name, _ in canary.STEPS] == ['schedule', 'lock', 'box score', 'market', 'goalies', 'roster']


# --- the box score step, 2026-10-16 (issue 495) ------------------------------------------
# Game 2026020118 was final with no starting goalie flagged at the 06:40 canary, and settled
# by the 11:52 one. The daily import already waits for such a game; the canary now does too,
# up to a limit, and past it the night fails so a game that never settles is not silent.

def box(gid, starters=(1, 1)):
    def goalies(n, first):
        return [{'playerId': first + i, 'starter': i < n, 'shotsAgainst': 30 if i < n else 0,
                 'goalsAgainst': 2 if i < n else 0} for i in range(max(n, 1) + 1)]
    return {'id': gid, 'season': 20262027, 'gameDate': '2026-10-15', 'gameOutcome': {'lastPeriodType': 'REG'},
            'homeTeam': {'abbrev': 'TOR', 'score': 4, 'sog': 23}, 'awayTeam': {'abbrev': 'FLA', 'score': 1, 'sog': 33},
            'playerByGameStats': {'homeTeam': {'goalies': goalies(starters[0], 100)},
                                  'awayTeam': {'goalies': goalies(starters[1], 200)}}}


def box_state(games, unsettled=(), now=NOW, raw=None):
    """`games` is [(game_id, hours since its start)]; `unsettled` are the ids whose box lacks a starter."""
    sched = pd.DataFrame([{'game_id': gid, 'game_type': 'regular', 'status': 'final',
                           'start_utc': (now - timedelta(hours=h)).strftime('%Y-%m-%dT%H:%M:%SZ')}
                          for gid, h in games])
    asked = []

    def get(url):
        asked.append(url)
        gid = int(url.rstrip('/').split('/')[-2] if url.endswith('/boxscore') else url.split('/')[-1])
        if raw is not None:
            return raw
        return json.dumps(box(gid, (0, 1) if gid in unsettled else (1, 1))).encode()
    return {'schedule': sched, 'now': now, 'get': get, 'asked': asked}


def test_a_settled_newest_final_passes_and_is_the_one_reported():
    state = box_state([(2026020117, 9), (2026020118, 5)])
    note = canary.step_box_score(state)
    assert 'game 2026020118' in note and 'not settled' not in note and len(state['asked']) == 2


def test_the_newest_by_start_is_read_whatever_order_the_schedule_lists_them_in():
    state = box_state([(2026020118, 5), (2026020117, 9)])
    assert 'game 2026020118' in canary.step_box_score(state)


def test_a_recent_final_the_league_has_not_settled_does_not_fail_the_night():
    """The 2026-10-16 canary, replayed: the newest final has no starter flagged yet."""
    state = box_state([(2026020117, 9), (2026020118, 5)], unsettled={2026020118})
    note = canary.step_box_score(state)
    assert 'game 2026020117' in note and '2026020118 final but not settled yet' in note


def test_when_every_recent_final_is_unsettled_the_night_still_passes_and_says_so():
    state = box_state([(2026020117, 9), (2026020118, 5)], unsettled={2026020117, 2026020118})
    note = canary.step_box_score(state)
    assert note.startswith('no settled box score yet') and 'not an error' in note


@pytest.mark.parametrize('hours, fails', [(11.9, False), (12, True), (30, True)], ids=['just-under', 'at-the-limit', 'long-stuck'])
def test_a_final_still_unsettled_past_the_limit_fails_the_night_naming_the_game(hours, fails):
    state = box_state([(2026020117, hours + 4), (2026020118, hours)], unsettled={2026020118})
    if not fails:
        assert 'not settled yet' in canary.step_box_score(state)
        return
    with pytest.raises(history.HistoryError, match=r'2026020118.*starting goalies flagged, not 1.*is not settling'):
        canary.step_box_score(state)


def test_a_stuck_final_behind_a_settled_newer_one_is_still_found():
    """The newest final settling must not hide an older one that never did."""
    state = box_state([(2026020117, 30), (2026020118, 5)], unsettled={2026020117})
    with pytest.raises(history.HistoryError, match=r'2026020117.*is not settling'):
        canary.step_box_score(state)


def test_a_feed_that_changed_shape_still_fails_the_night():
    """Only an unsettled starter flag is waited for; anything else the feed does is the finding."""
    state = box_state([(2026020118, 5)], raw=b'<html>not json</html>')
    with pytest.raises(json.JSONDecodeError):
        canary.step_box_score(state)


def test_only_the_newest_few_finals_are_looked_through():
    state = box_state([(2026020100 + i, 5 + i) for i in range(8)], unsettled={2026020100 + i for i in range(8)})
    canary.step_box_score(state)
    assert len(state['asked']) == canary.LOOKBACK
