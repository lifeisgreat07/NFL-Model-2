"""
Stage 92 item 11 (audit 7, R11): MISSED PICKS covers every game of
yesterday's and today's slates that started with no saved pick.

The run decides today's and tomorrow's slates, so the started games it named
were today's only. A game of yesterday's slate that started after the last
run able to save it (a failed run, a late copy) was never named, and no alert
said a pick was lost.

Run with: pytest tests/test_missed_days.py -v
"""
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from src.sports.nba import daily as nba_daily
from src.sports.nhl import daily as nhl_daily

DAILY = {'nhl': nhl_daily, 'nba': nba_daily}
NOW = datetime(2026, 11, 5, 14, 0, tzinfo=UTC)   # 09:00 Eastern on 2026-11-05


def sched(rows):
    frame = pd.DataFrame(rows, columns=['game_id', 'slate', 'start_utc', 'status'])
    return frame.assign(start_utc=pd.to_datetime(frame['start_utc'], utc=True))


GAMES = sched([
    ('201', '2026-11-03', '2026-11-04T00:00:00Z', 'final'),        # two days ago: not this run's to name
    ('301', '2026-11-04', '2026-11-05T02:30:00Z', 'final'),        # yesterday's late game
    ('302', '2026-11-04', '2026-11-04T23:00:00Z', 'final'),        # yesterday's, picked
    ('303', '2026-11-04', '2026-11-05T00:00:00Z', 'postponed'),    # yesterday's, never played
    ('401', '2026-11-05', '2026-11-05T13:00:00Z', 'in_progress'),  # today's, under way
    ('402', '2026-11-05', '2026-11-06T00:00:00Z', 'scheduled'),    # today's, not started
])


@pytest.mark.parametrize('sport', DAILY)
def test_yesterdays_and_todays_started_games_are_named(sport):
    assert set(DAILY[sport].recently_started(GAMES, NOW)) == {'301', '302', '401'}


@pytest.mark.parametrize('sport', DAILY)
def test_a_late_game_of_yesterday_with_no_pick_is_missed(sport, tmp_path):
    (tmp_path / '302.json').write_text('{}', encoding='utf-8')
    (tmp_path / '401.json').write_text('{}', encoding='utf-8')
    d = DAILY[sport]
    assert d.missed_line(sorted(set(d.recently_started(GAMES, NOW))), tmp_path) == \
        'MISSED PICKS: 1 started with no saved pick: 301'


@pytest.mark.parametrize('sport', DAILY)
def test_the_run_names_both_days(sport):
    src = Path(DAILY[sport].__file__).read_text(encoding='utf-8')
    assert 'lost = missed_line(sorted(set(decision.started) | set(recently_started(sched, now))), folder)' in src
