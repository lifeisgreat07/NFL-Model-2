"""
Stage 44 item 1: Line Judge's checks for the NFL Weekly update
(src/sports/nfl/line_judge.py). Each check is shown holding and failing at
its edges, `locked_at` is driven with week 5's real git history, and the
workflow is held to running the checks after a green run.

Run with: pytest tests/test_line_judge.py -v
"""
import json
from datetime import UTC, datetime, timedelta
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


# The daily runs' fix (#521) for the same exposure: cron-job.org dispatches the slot on
# time, and GitHub's own cron starts a copy hours later that commits nothing. Judged as
# a run, the copy reads 7 hours late.
SLOT = utc('2026-10-15T11:00:00')
COPY = utc('2026-10-15T18:05:00')


def served_at(*starts):
    return lambda workflow, slot: [utc(t) for t in starts]


def test_githubs_late_copy_of_a_slot_a_dispatch_served_is_not_judged():
    assert lj.check_on_time('schedule', COPY, WORKFLOW, served_at('2026-10-15T11:00:41')) == []


def test_a_late_run_for_a_slot_no_dispatch_served_is_still_flagged():
    for fetch in (served_at(), served_at('2026-10-15T04:01:00'), served_at('2026-10-15T11:20:00')):
        found = lj.check_on_time('schedule', COPY, WORKFLOW, fetch)
        assert [f.check for f in found] == ['on-time'] and '7.1 hours' in found[0].message


def test_a_late_run_is_flagged_when_the_actions_api_cannot_be_read():
    def broken(workflow, slot):
        raise RuntimeError('HTTP 502')
    assert [f.check for f in lj.check_on_time('schedule', COPY, WORKFLOW, broken)] == ['on-time']


def test_a_dispatched_run_is_judged_even_when_a_dispatch_served_its_slot():
    """The dispatched run is the one that does the work: its own lateness counts."""
    late_dispatch = utc('2026-10-15T18:05:00')
    found = lj.check_on_time('workflow_dispatch', late_dispatch, WORKFLOW,
                             served_at('2026-10-15T11:00:41', '2026-10-15T18:05:00'))
    assert [f.check for f in found] == ['on-time']


def test_the_slot_is_looked_up_only_for_a_late_run_and_under_the_judged_workflow():
    asked = []

    def fetch(workflow, slot):
        asked.append((workflow, slot))
        return []
    assert lj.check_on_time('schedule', SLOT + timedelta(minutes=10), WORKFLOW, fetch) == []
    assert asked == []
    lj.check_on_time('schedule', COPY, WORKFLOW, fetch)
    assert asked == [('nfl-weekly-update.yml', SLOT)]


def test_the_weekend_refresh_asks_about_its_own_workflow(tmp_path):
    asked = []

    def fetch(workflow, slot):
        asked.append(workflow)
        return [utc('2026-10-16T05:19:00')]
    copy = utc('2026-10-16T12:40:00')   # the Friday 05:17 slot, copied 7 hours on
    found = lj.judge_refresh(2026, sched(THU), CANCELLED, [], 'schedule', copy, REFRESH, fetch=fetch)
    assert found == [] and asked == ['nfl-weekend-refresh.yml']
    assert [f.check for f in lj.judge_refresh(2026, sched(THU), CANCELLED, [], 'schedule', copy, REFRESH,
                                              fetch=served_at())] == ['on-time']


def test_the_weekly_update_judge_passes_the_dispatches_to_the_on_time_check(tmp_path):
    before_kickoff = utc('2026-10-15T20:00:00')
    kwargs = dict(pred_dir=tmp_path, skipped_dir=tmp_path, results_dir=tmp_path)
    ok = lj.judge(2026, sched(THU), before_kickoff, lambda p: None, CANCELLED, 'schedule', COPY, WORKFLOW,
                  fetch=served_at('2026-10-15T11:00:41'), **kwargs)
    assert ok == []
    late = lj.judge(2026, sched(THU), before_kickoff, lambda p: None, CANCELLED, 'schedule', COPY, WORKFLOW,
                    fetch=served_at(), **kwargs)
    assert [f.check for f in late] == ['on-time']


def test_the_command_line_reads_the_actions_api_by_default():
    """The workflows call main() with no fetch of their own."""
    import inspect

    from src.core import missed_dispatch
    assert inspect.signature(lj.main).parameters['fetch'].default is missed_dispatch._gh_fetch


@pytest.mark.parametrize('workflow, judged', [('nfl-weekly-update.yml', 'judge'),
                                              ('nfl-weekend-refresh.yml', 'judge_refresh')],
                         ids=['weekly-update', 'weekend-refresh'])
def test_the_command_line_hands_the_dispatches_to_the_judge_it_runs(workflow, judged, monkeypatch):
    import src.sports.nfl.data_loader as data_loader
    import src.sports.nfl.weekend_refresh as weekend_refresh
    seen = {}

    def spy(name):
        def run(*args, **kwargs):
            seen[name] = kwargs.get('fetch')
            return []
        return run
    monkeypatch.setattr(data_loader, 'load_schedule', lambda season: sched(THU))
    monkeypatch.setattr(lj, 'load_cancelled_pairs', lambda season: set())
    monkeypatch.setattr(weekend_refresh, 'weeks_to_refresh', lambda season: [])
    monkeypatch.setattr(lj, 'judge', spy('judge'))
    monkeypatch.setattr(lj, 'judge_refresh', spy('judge_refresh'))
    fetch = served_at()
    assert lj.main(['--season', '2026', '--workflow', workflow], NOW, fetch) == 0
    assert seen == {judged: fetch}


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


# --- the Weekend refresh (Stage 44 item 2) ---------------------------------------

REFRESH = (REPO / '.github' / 'workflows' / 'nfl-weekend-refresh.yml').read_text(encoding='utf-8')
PICKS6 = [{'home': 'DEN', 'away': 'SEA'}, {'home': 'JAX', 'away': 'HOU'}]


def shown(*rows):
    return {'season': 2026, 'week': 6, 'games': [
        {'home': h, 'away': a, 'status': st, 'home_score': hs, 'away_score': as_} for h, a, st, hs, as_ in rows]}


def test_a_snapshot_that_matches_the_schedule_holds():
    games = sched(game(6, 'DEN', 'SEA', '2026-10-15 20:15', (24, 17)), SUN)
    snap = shown(('DEN', 'SEA', 'final', 24, 17), ('JAX', 'HOU', 'upcoming', None, None))
    assert lj.check_snapshot(6, PICKS6, games, snap, CANCELLED) == []


@pytest.mark.parametrize('row', [('DEN', 'SEA', 'started', None, None), ('DEN', 'SEA', 'final', 17, 24)])
def test_a_final_score_the_snapshot_does_not_show_is_flagged(row):
    games = sched(game(6, 'DEN', 'SEA', '2026-10-15 20:15', (24, 17)), SUN)
    found = lj.check_snapshot(6, PICKS6, games, shown(row, ('JAX', 'HOU', 'upcoming', None, None)), CANCELLED)
    assert [f.check for f in found] == ['snapshot'] and 'SEA at DEN ended 17-24' in found[0].message


def test_a_kept_week_with_no_snapshot_or_a_missing_game_is_flagged():
    games = sched(THU, SUN)
    assert [f.check for f in lj.check_snapshot(6, PICKS6, games, None, CANCELLED)] == ['snapshot']
    found = lj.check_snapshot(6, PICKS6, games, shown(('DEN', 'SEA', 'upcoming', None, None)), CANCELLED)
    assert len(found) == 1 and 'HOU at JAX is picked and missing' in found[0].message


def test_a_listed_cancelled_game_must_read_cancelled():
    games = sched(THU, SUN)
    snap = shown(('DEN', 'SEA', 'started', None, None), ('JAX', 'HOU', 'upcoming', None, None))
    found = lj.check_snapshot(6, PICKS6, games, snap, {('DEN', 'SEA')})
    assert [f.check for f in found] == ['snapshot'] and 'cancelled' in found[0].message
    snap['games'][0]['status'] = 'cancelled'
    assert lj.check_snapshot(6, PICKS6, games, snap, {('DEN', 'SEA')}) == []


def test_judge_refresh_reads_each_kept_week_and_the_refreshs_own_slots(tmp_path):
    pred, status = tmp_path / 'pred', tmp_path / 'status'
    pred.mkdir()
    status.mkdir()
    (pred / '2026_week6.json').write_text(json.dumps(PICKS6))
    (status / '2026_week6.json').write_text(json.dumps(shown(('DEN', 'SEA', 'started', None, None),
                                                              ('JAX', 'HOU', 'upcoming', None, None))))
    games = sched(game(6, 'DEN', 'SEA', '2026-10-15 20:15', (24, 17)), SUN)
    # Friday 05:17 UTC is a refresh slot; 12:30 is 7.2 hours after it.
    found = lj.judge_refresh(2026, games, CANCELLED, [6], 'schedule', utc('2026-10-16T12:30:00'), REFRESH, pred, status)
    assert [f.check for f in found] == ['on-time', 'snapshot']
    assert lj.report(found, 2026, 'Weekend refresh').startswith('Line Judge found 2 thing(s) the 2026 Weekend refresh')


def test_line_judge_runs_after_a_green_weekend_refresh():
    body = REFRESH[REFRESH.index('\n  line-judge:\n'):]
    lines = [ln.strip() for ln in body.splitlines()]
    assert 'needs: [refresh]' in lines and "if: ${{ needs.refresh.result == 'success' }}" in lines
    assert 'ref: main' in lines
    assert '--workflow nfl-weekend-refresh.yml' in body and '--run-started "$started" --report line-judge.md' in body
    assert '--title "NFL: Line Judge found the Weekend refresh left something wrong"' in body
    assert 'exit 1' in body.split('--body-file line-judge.md')[1]
