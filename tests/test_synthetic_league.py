"""The synthetic league's schedule must never put a game in a clock-change hour
(the Line Judge planted-run tests failed for an hour on 2026-10-17 because one
of them, built from the real clock, landed a game in the ambiguous hour on
2026-11-01, when the clocks go back).

nflverse writes a game's day and time as Eastern wall-clock strings; an hour
that happens twice (or not at all) cannot be turned back into one instant.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent))

import synthetic_league as league

H = pd.Timedelta(hours=1)
OFFSETS = [H, 2 * H, 3 * H, 4 * H]

# Runs whose other weeks fall in the hour the clocks go back (2026-11-01
# 01:00-02:00 Eastern = 05:00-06:00 UTC): the first four are ahead of it by a
# whole number of weeks plus a day, the last is behind it by four weeks.
RUNS = [
    '2026-10-17 05:30', '2026-10-17 06:00', '2026-10-24 05:30', '2026-11-01 05:30',
    '2026-11-29 05:30',
]


@pytest.mark.parametrize('run', RUNS, ids=RUNS)
def test_no_game_but_the_target_week_has_a_time_the_clock_change_makes_ambiguous(run):
    now = pd.Timestamp(run, tz='UTC')
    _, schedules = league.build(now, OFFSETS)
    for season, sched in schedules.items():
        rest = sched[~((sched['season'] == league.TARGET) & (sched['week'] == league.TARGET_WEEK))]
        for _, game in rest.iterrows():
            local = pd.Timestamp(f"{game['gameday']} {game['gametime']}")
            # Raises if the Eastern wall-clock time happens twice or not at all.
            local.tz_localize('America/New_York', ambiguous='raise', nonexistent='raise')


def test_the_target_week_still_kicks_off_the_offsets_after_now():
    now = pd.Timestamp('2026-10-20 15:00', tz='UTC')
    _, schedules = league.build(now, OFFSETS)
    sched = schedules[league.TARGET]
    week = sched[sched['week'] == league.TARGET_WEEK]
    got = sorted(pd.Timestamp(f"{d} {t}").tz_localize('America/New_York').tz_convert('UTC')
                 for d, t in zip(week['gameday'], week['gametime']))
    assert got == [now + o for o in OFFSETS]
