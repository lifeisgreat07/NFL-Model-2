"""Property tests for the small functions every pick passes through
(Stage 48 item 16, proposed 2026-10-04).

The example tests elsewhere check the cases someone thought of. These state
what must hold for EVERY input in a range and let hypothesis search for a
counterexample: a market probability that is not monotone in the spread, a
kickoff off by an hour on the wrong side of a daylight-saving change, a
grade that is not the mirror image of the opposite pick.

Deterministic on purpose: `derandomize=True` makes every run draw the same
examples, so the count Booth reruns is the count quoted, and a failure here
reproduces on the next run instead of once in a while. No example database
is written (`database=None`), so a run leaves the checkout clean.

confidence_points is not here, though item 16 named it: it is computed
inline in weekly_update.predict_week, not by a function a property can call,
and lifting it out changes the weekly run, which waits for the 2026-10-08
lock.
"""
import math
from datetime import date, datetime, timedelta

import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st

from src.pipeline import weekly_update as wu
from src.pipeline.grade_predictions import graded_correct

PROPS = settings(derandomize=True, database=None, deadline=None, max_examples=300)

spreads = st.floats(min_value=-40, max_value=40, allow_nan=False, allow_infinity=False)
probs = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)


# ------------------------------------------------------------- market_prob

@PROPS
@given(spreads)
def test_market_prob_is_a_probability(s):
    p = float(wu.market_prob(s))
    assert 0.0 < p < 1.0


@PROPS
@given(spreads)
def test_market_prob_is_symmetric_about_a_pickem(s):
    """Home favoured by s and away favoured by s are mirror images."""
    assert math.isclose(float(wu.market_prob(s)) + float(wu.market_prob(-s)), 1.0, abs_tol=1e-12)


@PROPS
@given(spreads, st.floats(min_value=0.5, max_value=20, allow_nan=False))
def test_a_bigger_home_spread_never_lowers_the_home_probability(s, more):
    assert float(wu.market_prob(s + more)) > float(wu.market_prob(s))


def test_a_pickem_is_a_coin_flip():
    assert float(wu.market_prob(0.0)) == 0.5


# ------------------------------------------------------------- kickoff_utc

season_days = st.dates(min_value=date(2020, 8, 1), max_value=date(2030, 2, 28))
clock = st.times().map(lambda t: f'{t.hour:02d}:{t.minute:02d}')


def _eastern_offset_hours(day, hhmm):
    """EDT is UTC-4 and EST UTC-5; which one, from the zone database itself."""
    local = pd.Timestamp(f'{day} {hhmm}').tz_localize('America/New_York', ambiguous=True,
                                                      nonexistent='shift_forward')
    return -int(local.utcoffset().total_seconds() // 3600)


@PROPS
@given(season_days, clock)
def test_kickoff_is_utc_and_reads_back_as_the_eastern_clock(day, hhmm):
    """Whatever the date, the UTC kickoff converted back to Eastern is the
    listed kickoff: the four-or-five-hour offset follows the date, never a
    constant. NFL kickoffs never sit inside the 2am changeover hour, so
    those two clocks are not asked about."""
    if hhmm.startswith('02:'):
        return
    k = wu.kickoff_utc(pd.Series({'gameday': day.isoformat(), 'gametime': hhmm}))
    assert str(k.tz) == 'UTC'
    back = k.tz_convert('America/New_York')
    assert back.strftime('%Y-%m-%d %H:%M') == f'{day.isoformat()} {hhmm}'
    assert (k.tz_localize(None) - pd.Timestamp(f'{day} {hhmm}')) == pd.Timedelta(
        hours=_eastern_offset_hours(day, hhmm))


@PROPS
@given(season_days)
def test_a_missing_time_is_the_start_of_the_eastern_day(day):
    """The safe direction for the lock: no time means the earliest the game
    could be, midnight Eastern, never midnight UTC (hours earlier)."""
    k = wu.kickoff_utc(pd.Series({'gameday': day.isoformat(), 'gametime': None}))
    assert k.tz_convert('America/New_York').strftime('%Y-%m-%d %H:%M') == f'{day.isoformat()} 00:00'


@PROPS
@given(season_days, clock, st.integers(min_value=1, max_value=12))
def test_a_later_kickoff_is_later_in_utc(day, hhmm, days_on):
    if hhmm.startswith('02:'):
        return
    a = wu.kickoff_utc(pd.Series({'gameday': day.isoformat(), 'gametime': hhmm}))
    later = (datetime.combine(day, datetime.min.time()) + timedelta(days=days_on)).date()
    b = wu.kickoff_utc(pd.Series({'gameday': later.isoformat(), 'gametime': hhmm}))
    assert b > a


# ----------------------------------------------------------- graded_correct

@PROPS
@given(probs, st.sampled_from([0, 1]))
def test_a_grade_is_zero_or_one(p, won):
    assert graded_correct(p, won) in (0, 1)


@PROPS
@given(probs.filter(lambda p: p != 0.5), st.sampled_from([0, 1]))
def test_the_opposite_pick_gets_the_opposite_grade(p, won):
    """Away pick at 1-p is right exactly when home pick at p is wrong. 0.5 is
    left out: it is the one probability that picks home either way."""
    assert graded_correct(p, won) + graded_correct(1 - p, won) == 1


@PROPS
@given(probs, st.sampled_from([0, 1]))
def test_the_grade_is_whether_the_picked_side_won(p, won):
    picked_home = p >= 0.5
    assert graded_correct(p, won) == int(picked_home == bool(won))


@PROPS
@given(st.sampled_from([0, 1, None]))
def test_no_probability_is_no_grade(won):
    assert graded_correct(None, won) is None
