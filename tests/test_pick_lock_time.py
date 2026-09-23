"""When the weekly run locks a week's picks.

Decided by Mark on 2026-09-22: Thursday, before Thursday night's kickoff,
instead of Tuesday morning. Tuesday locked before most injury news, so a
sourced QB override could only help if it existed two days before anyone
had practised -- and v2.5 exists to give the pick better QB information.

The rule lives in weekly_update.decide_lock: a run locks when the first
game still to come kicks off before the NEXT scheduled run plus
LOCK_SLACK. These tests hold it on the weeks that make a calendar rule go
wrong: an ordinary Thursday-night week, Thanksgiving, a Wednesday game, a
Saturday-first week 18, a Sunday-only week, both sides of the clock change,
and a manual run after a kickoff was missed.

The dates and kickoff slots follow the 2026 calendar (Thursday night
20:15, Thanksgiving 12:30, the 1 Nov clock change); the matchups are
illustrative, not the real fixtures. Kickoffs are ET, as the schedule's
`gametime` is.
"""
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import weekly_update as wu  # noqa: E402

WORKFLOW = ROOT / '.github' / 'workflows' / 'weekly-update.yml'


def utc(s):
    return pd.Timestamp(s, tz='UTC')


def week(*games):
    """games: (away, home, gameday, gametime_et)."""
    return pd.DataFrame([{'away_team': a, 'home_team': h, 'gameday': d, 'gametime': t}
                         for a, h, d, t in games])


# 2026 week 3's shape: Thursday night in EDT, then Sunday and Monday.
WEEK3 = week(('MIA', 'BUF', '2026-09-24', '20:15'),
             ('ATL', 'CAR', '2026-09-27', '13:00'),
             ('KC', 'NYG', '2026-09-28', '20:15'))


# --- the ordinary week -------------------------------------------------------

def test_tuesday_holds_an_ordinary_week_for_thursday():
    d = wu.decide_lock(WEEK3, utc('2026-09-22 11:07'))
    assert d.lock is False, (
        "the Tuesday run locked a week whose first game is Thursday night. "
        "That is the old behaviour Mark decided against on 2026-09-22: it "
        "locks before Wednesday's injury reports, so no QB override written "
        "after Tuesday morning can reach the pick.")
    assert d.next_run == utc('2026-09-24 16:00')
    assert d.started == []


def test_thursday_locks_it_before_kickoff():
    d = wu.decide_lock(WEEK3, utc('2026-09-24 16:12'))
    assert d.lock is True, "the Thursday run did not lock the week"
    assert d.first_kickoff == utc('2026-09-25 00:15')
    assert d.started == []


def test_a_late_thursday_run_still_locks():
    """Scheduled Actions start late. Three hours late is still in time."""
    assert wu.decide_lock(WEEK3, utc('2026-09-24 19:05')).lock is True


def test_a_manual_run_before_the_thursday_run_leaves_it_to_that_run():
    d = wu.decide_lock(WEEK3, utc('2026-09-24 14:00'))
    assert d.lock is False
    assert d.next_run == utc('2026-09-24 16:00')


# --- weeks a calendar rule gets wrong ---------------------------------------

def test_thanksgiving_locks_on_tuesday_by_itself():
    """12:30 ET on 26 Nov 2026 is 17:30 UTC (EST): 90 minutes after the
    Thursday run is due. A run that late is ordinary for Actions, so the
    Tuesday run takes it -- this is what LOCK_SLACK is for."""
    thanksgiving = week(('CHI', 'DET', '2026-11-26', '12:30'),
                        ('NYG', 'DAL', '2026-11-26', '16:30'),
                        ('LV', 'KC', '2026-11-26', '20:20'),
                        ('ATL', 'NO', '2026-11-29', '13:00'))
    d = wu.decide_lock(thanksgiving, utc('2026-11-24 11:05'))
    assert d.lock is True, (
        "Thanksgiving week waited for Thursday, leaving an early kickoff 90 "
        "minutes after a scheduled run that can easily start later than that")
    assert d.first_kickoff == utc('2026-11-26 17:30')


def test_a_wednesday_game_locks_on_tuesday():
    xmas = week(('PIT', 'KC', '2030-12-25', '13:00'),
                ('BAL', 'HOU', '2030-12-25', '16:30'),
                ('SEA', 'LA', '2030-12-29', '16:25'))
    assert wu.decide_lock(xmas, utc('2030-12-24 11:02')).lock is True


def test_a_saturday_first_week_locks_on_thursday():
    """Week 18 has no Thursday game. A rule keyed on 'the day before the
    first game' would hold on Thursday and never lock at all."""
    wk18 = week(('CLE', 'CIN', '2027-01-09', '16:30'),
                ('NYJ', 'BUF', '2027-01-10', '13:00'))
    assert wu.decide_lock(wk18, utc('2027-01-05 11:03')).lock is False
    assert wu.decide_lock(wk18, utc('2027-01-07 16:04')).lock is True


def test_a_sunday_only_week_locks_on_thursday():
    """A Super Bowl, or any week whose first game is Sunday. The next run
    after Thursday is Tuesday, after every game -- so Thursday must lock.
    A fixed 'lock within N hours of kickoff' horizon cannot do this and
    also hold an ordinary week on Tuesday: Thursday 16:00 to a Sunday 09:30
    ET London kickoff is 69.5 hours, longer than Tuesday to Thursday night."""
    sb = week(('SF', 'KC', '2027-02-14', '18:30'))
    assert wu.decide_lock(sb, utc('2027-02-09 11:01')).lock is False
    assert wu.decide_lock(sb, utc('2027-02-11 16:01')).lock is True
    london = week(('NYJ', 'MIN', '2026-10-11', '09:30'),
                  ('DAL', 'PHI', '2026-10-11', '13:00'))
    assert wu.decide_lock(london, utc('2026-10-08 16:03')).lock is True


# --- clock change and kickoff arithmetic ------------------------------------

@pytest.mark.parametrize('gameday, expected', [
    ('2026-09-24', '2026-09-25 00:15'),   # EDT, UTC-4
    ('2026-11-05', '2026-11-06 01:15'),   # EST, UTC-5, after 1 Nov
])
def test_kickoff_is_localised_not_offset(gameday, expected):
    game = {'gameday': gameday, 'gametime': '20:15'}
    assert wu.kickoff_utc(game) == utc(expected), (
        "gametime is Eastern and the offset changes on 1 Nov 2026; a fixed "
        "offset gets one half of the season an hour wrong")


def test_an_est_thursday_night_still_waits_for_thursday():
    est = week(('GB', 'MIN', '2026-11-05', '20:15'),
               ('DEN', 'LV', '2026-11-08', '16:05'))
    assert wu.decide_lock(est, utc('2026-11-03 11:04')).lock is False
    assert wu.decide_lock(est, utc('2026-11-05 16:04')).lock is True


def test_a_missing_time_counts_as_the_start_of_the_day():
    """The earliest the game could be -- the safe side for both decisions."""
    assert wu.kickoff_utc({'gameday': '2026-09-24', 'gametime': None}) == utc('2026-09-24 04:00')
    assert wu.kickoff_utc({'gameday': None, 'gametime': '20:15'}) is None


# --- a kickoff that was missed ---------------------------------------------

def test_a_run_after_a_kickoff_locks_the_rest_and_names_what_it_missed():
    """The Thursday run failed and someone dispatched it on Friday. Before
    this rule the Tuesday lock left ~61 hours of margin and this could not
    happen; with a Thursday lock it can. Thursday night's game gets no pick
    -- a pick saved after kickoff is not a prediction -- and the rest lock."""
    d = wu.decide_lock(WEEK3, utc('2026-09-25 14:00'))
    assert d.lock is True
    assert d.started == [('MIA', 'BUF')], (
        "a game that has already kicked off was not reported as started, so "
        "main() would save a pick for it after kickoff")
    assert d.first_kickoff == utc('2026-09-27 17:00')


def test_a_week_entirely_in_the_past_does_not_lock():
    d = wu.decide_lock(WEEK3, utc('2026-09-29 11:00'))
    assert d.lock is False
    assert len(d.started) == 3


def test_a_week_with_no_known_kickoff_locks_as_it_always_did():
    unknown = week(('MIA', 'BUF', None, None))
    d = wu.decide_lock(unknown, utc('2026-09-22 11:00'))
    assert d.lock is True and d.started == []


# --- the constant and the workflow must describe the same schedule ----------

def _cron_runs():
    """(weekday Mon=0, hour, minute) for every `cron:` line in the workflow."""
    text = WORKFLOW.read_text(encoding='utf-8')
    crons = re.findall(r"^\s*-\s*cron:\s*'([^']+)'", text, re.M)
    runs = set()
    for c in crons:
        minute, hour, dom, month, dow = c.split()
        assert dom == '*' and month == '*' and dow.isdigit() and hour.isdigit() \
            and minute.isdigit(), (
            f"cron {c!r} is not one fixed weekly time; SCHEDULED_RUNS_UTC cannot "
            "describe it, so decide_lock cannot know when the next run is")
        runs.add(((int(dow) - 1) % 7, int(hour), int(minute)))
    return crons, runs


def test_the_workflow_schedule_is_the_one_decide_lock_assumes():
    crons, runs = _cron_runs()
    # Vacuity: a parser that finds nothing would make the comparison below
    # compare two empty things, or fail with a confusing diff.
    assert len(crons) >= 2, f"found {len(crons)} cron line(s) in {WORKFLOW.name}"
    assert runs == set(wu.SCHEDULED_RUNS_UTC), (
        f"{WORKFLOW.name} runs at {sorted(runs)} but SCHEDULED_RUNS_UTC says "
        f"{sorted(wu.SCHEDULED_RUNS_UTC)}. decide_lock holds a week for the "
        "next run it believes in; if that run does not exist, the week is "
        "never locked before kickoff.")


def test_the_lock_step_skips_games_that_have_started():
    """Structural: main() needs the network. decide_lock can report a started
    game correctly and main() can still predict it; this stops that."""
    import inspect
    src = inspect.getsource(wu.main)
    assert re.search(r"if \(away, home\) in started:\s*\n\s*continue", src), (
        "main() no longer skips games decide_lock reported as started")
