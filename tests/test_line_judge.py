"""
Stage 44 item 1: Line Judge's checks for the NFL Weekly update
(src/sports/nfl/line_judge.py). Each check is shown holding and failing at
its edges, `locked_at` is driven with week 5's real git history, and the
workflow is held to running the checks after a green run.

Run with: pytest tests/test_line_judge.py -v
"""
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.sports.nfl import line_judge as lj

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = (REPO / '.github' / 'workflows' / 'nfl-weekly-update.yml').read_text(encoding='utf-8')
CANCELLED: set = set()


def game(week, home, away, when_et, score=None):
    """A schedule row; `when_et` is 'YYYY-MM-DD HH:MM' Eastern, as nflverse gives it."""
    day, time = when_et.split()
    hs, as_ = score if score else (np.nan, np.nan)
    return {'week': week, 'home_team': home, 'away_team': away, 'gameday': day, 'gametime': time,
            'home_score': hs, 'away_score': as_}


def sched(*rows):
    return pd.DataFrame(list(rows))


def utc(text):
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


# Thursday 2026-10-15 20:15 ET is 00:15 UTC on the 16th.
THU = game(6, 'DEN', 'SEA', '2026-10-15 20:15')
SUN = game(6, 'JAX', 'HOU', '2026-10-18 09:30')


# --- on-time ------------------------------------------------------------------

def test_a_dispatch_on_the_minute_is_on_time():
    assert lj.check_on_time('workflow_dispatch', utc('2026-10-15T11:00:41'), WORKFLOW) == []


def test_a_github_copy_seven_hours_late_is_flagged():
    found = lj.check_on_time('schedule', utc('2026-10-15T18:05:00'), WORKFLOW)
    assert [f.check for f in found] == ['on-time'] and '7.1 hours' in found[0].message


def test_a_run_by_hand_long_after_any_slot_serves_none_and_is_not_late():
    assert lj.check_on_time('workflow_dispatch', utc('2026-10-16T23:00:00'), WORKFLOW) == []


# --- every-week ---------------------------------------------------------------

NOW = utc('2026-10-16T03:00:00')  # after Thursday night's kickoff


def test_a_started_week_with_no_lock_is_flagged():
    found = lj.check_every_week(sched(THU, SUN), locked=[], skipped=[], now=NOW)
    assert [f.check for f in found] == ['every-week'] and 'week 6' in found[0].message


@pytest.mark.parametrize('locked, skipped', [([6], []), ([], [6])])
def test_a_locked_or_skipped_week_holds(locked, skipped):
    assert lj.check_every_week(sched(THU, SUN), locked=locked, skipped=skipped, now=NOW) == []


def test_a_week_not_yet_started_is_not_due():
    assert lj.check_every_week(sched(THU, SUN), [], [], now=utc('2026-10-15T11:00:00')) == []


def test_nothing_is_expected_past_the_super_bowl():
    assert lj.check_every_week(sched(game(23, 'DEN', 'SEA', '2027-02-20 18:30')), [], [],
                               now=utc('2027-03-01T00:00:00')) == []


# --- before-kickoff -----------------------------------------------------------

PICKS = [{'home': 'DEN', 'away': 'SEA'}, {'home': 'JAX', 'away': 'HOU'}]
LOCK = utc('2026-10-15T11:03:00')


def test_a_lock_before_every_kickoff_holds():
    assert lj.check_before_kickoff(6, LOCK, PICKS, sched(THU, SUN), CANCELLED) == []


def test_a_pick_saved_after_its_kickoff_is_flagged():
    found = lj.check_before_kickoff(6, utc('2026-10-16T01:00:00'), PICKS, sched(THU, SUN), CANCELLED)
    assert len(found) == 1 and 'SEA at DEN' in found[0].message and 'before its pick' in found[0].message


def test_an_upcoming_game_left_without_a_pick_is_flagged():
    found = lj.check_before_kickoff(6, LOCK, PICKS[:1], sched(THU, SUN), CANCELLED)
    assert len(found) == 1 and 'HOU at JAX' in found[0].message and 'no pick' in found[0].message


def test_a_game_already_started_at_the_lock_may_go_unpicked():
    """The run names those and gives them no pick (decide_lock)."""
    late = utc('2026-10-16T01:00:00')
    assert lj.check_before_kickoff(6, late, PICKS[1:], sched(THU, SUN), CANCELLED) == []


def test_a_cancelled_game_may_go_unpicked():
    assert lj.check_before_kickoff(6, LOCK, PICKS[:1], sched(THU, SUN), {('JAX', 'HOU')}) == []


# --- graded -------------------------------------------------------------------

FINAL = sched(game(6, 'DEN', 'SEA', '2026-10-15 20:15', (24, 17)),
              game(6, 'JAX', 'HOU', '2026-10-18 09:30', (20, 20)))


def test_a_final_week_graded_in_full_holds():
    assert lj.check_graded(6, PICKS, FINAL, PICKS, CANCELLED) == []


def test_a_final_week_with_no_graded_file_is_flagged():
    found = lj.check_graded(6, PICKS, FINAL, None, CANCELLED)
    assert [f.check for f in found] == ['graded'] and 'no graded file' in found[0].message


def test_a_final_game_missing_from_the_graded_file_is_flagged():
    found = lj.check_graded(6, PICKS, FINAL, PICKS[:1], CANCELLED)
    assert len(found) == 1 and 'HOU at JAX' in found[0].message


def test_a_week_with_a_game_still_to_finish_is_not_due():
    assert lj.check_graded(6, PICKS, sched(FINAL.iloc[0].to_dict(), SUN), None, CANCELLED) == []


def test_a_cancelled_game_is_not_owed_a_grade():
    unplayed = sched(FINAL.iloc[0].to_dict(), SUN)
    assert lj.check_graded(6, PICKS, unplayed, PICKS[:1], {('JAX', 'HOU')}) == []


# --- locked_at ----------------------------------------------------------------

# `git log --follow --name-status --format=%x00%cI` for predictions/nfl/2026_week5.json,
# as it reads on main (newest first).
WEEK5_LOG = ('\x002026-10-08T22:10:25-04:00\n\n'
             'R100\tpredictions/2026_week5.json\tpredictions/nfl/2026_week5.json\n'
             '\x002026-10-08T17:43:31Z\n\n'
             'R079\tpredictions/preview/2026_week5.json\tpredictions/2026_week5.json\n'
             '\x002026-10-06T17:00:29Z\n\n'
             'A\tpredictions/preview/2026_week5.json\n')


def fake_git(out):
    return lambda args, cwd: out


def test_the_lock_is_when_the_preview_was_moved_into_place_not_when_it_was_made():
    path = REPO / 'predictions' / 'nfl' / '2026_week5.json'
    assert lj.locked_at(path, REPO, fake_git(WEEK5_LOG)) == utc('2026-10-08T17:43:31')


def test_a_file_only_ever_a_preview_was_never_locked():
    only_preview = '\x002026-10-06T17:00:29Z\n\nA\tpredictions/preview/2026_week5.json\n'
    path = REPO / 'predictions' / 'nfl' / '2026_week5.json'
    assert lj.locked_at(path, REPO, fake_git(only_preview)) is None


def test_a_week_saved_straight_to_its_place_is_locked_when_added():
    added = '\x002026-09-02T16:38:14Z\n\nA\tpredictions/2026_week1.json\n'
    path = REPO / 'predictions' / 'nfl' / '2026_week1.json'
    assert lj.locked_at(path, REPO, fake_git(added)) == utc('2026-09-02T16:38:14')


# --- judge, end to end --------------------------------------------------------

def test_judge_reads_the_folders_and_runs_every_check(tmp_path):
    pred, skipped, results = tmp_path / 'pred', tmp_path / 'pred' / 'skipped', tmp_path / 'results'
    for d in (pred, skipped, results):
        d.mkdir(parents=True)
    (pred / '2026_week6.json').write_text(json.dumps(PICKS[:1]), encoding='utf-8')
    late_lock = lambda path: utc('2026-10-16T01:00:00')
    week7 = game(7, 'KC', 'LV', '2026-10-22 20:15')
    found = lj.judge(2026, sched(*FINAL.to_dict('records'), week7), utc('2026-10-24T00:00:00'),
                     late_lock, CANCELLED, 'schedule', utc('2026-10-22T19:30:00'), WORKFLOW,
                     pred_dir=pred, skipped_dir=skipped, results_dir=results)
    # Week 6's late lock saved SEA at DEN after its kickoff AND left the
    # upcoming HOU at JAX unpicked: two before-kickoff findings.
    assert [f.check for f in found] == ['on-time', 'every-week', 'before-kickoff', 'before-kickoff',
                                        'graded']


def test_the_report_names_each_finding_and_a_clean_run_says_so():
    assert 'every check holds' in lj.report([], 2026)
    text = lj.report([lj.Finding('graded', 'week 6: x.')], 2026)
    assert '1 thing(s)' in text and '**graded**: week 6: x.' in text


# --- the workflow -------------------------------------------------------------

def test_line_judge_runs_after_a_green_weekly_update_with_the_whole_history():
    lines = [ln.strip() for ln in WORKFLOW[WORKFLOW.index('\n  line-judge:\n'):].splitlines()]
    assert 'needs: [slot-guard, weekly-update]' in lines
    assert "if: ${{ needs.weekly-update.result == 'success' }}" in lines
    assert 'ref: main' in lines and 'fetch-depth: 0' in lines


def test_a_finding_fails_the_job_and_raises_its_own_alert():
    body = WORKFLOW[WORKFLOW.index('\n  line-judge:\n'):]
    assert 'python -m src.sports.nfl.line_judge --season "$season" --run-event "$GITHUB_EVENT_NAME"' in body
    assert '--run-started "$started" --report line-judge.md' in body
    assert '--title "NFL: Line Judge found the Weekly update left something wrong"' in body
    assert 'exit 1' in body.split('--body-file line-judge.md')[1]
