"""
Stage 44 item 2: Line Judge's checks for the NHL's and the NBA's daily runs
(src/core/day_line_judge.py). Each check is shown holding and failing at its
edges, `added_at` reads git's add times from a recorded log, a whole judged
folder is built in tmp_path, and both daily workflows are held to running
the judge after a green run.

Run with: pytest tests/test_day_line_judge.py -v
"""
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.core import day_line_judge as dlj

REPO = Path(__file__).resolve().parents[1]


def utc(text):
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


def wf(sport):
    return (REPO / '.github' / 'workflows' / f'{sport}-daily.yml').read_text(encoding='utf-8')


# --- on-time ------------------------------------------------------------------

@pytest.mark.parametrize('sport, slot', [('nhl', '2026-10-15T14:00:00'), ('nba', '2026-10-15T16:00:00')])
def test_a_run_inside_the_hour_is_on_time_and_one_past_it_is_flagged(sport, slot):
    on_time = utc(slot) + timedelta(minutes=40)
    late = utc(slot) + timedelta(hours=1, minutes=5)
    assert dlj.check_on_time(sport, 'workflow_dispatch', on_time, wf(sport)) == []
    found = dlj.check_on_time(sport, 'schedule', late, wf(sport))
    assert [f.check for f in found] == ['on-time'] and '1.1 hours' in found[0].message


def test_no_start_given_is_not_judged():
    assert dlj.check_on_time('nhl', 'schedule', None, wf('nhl')) == []


# Seen 2026-10-16: cron-job.org dispatched the 21:00 slot at 21:02, and GitHub's own
# cron started a copy at 23:04 that committed nothing. The copy was judged 2.1 hours late.
SLOT = utc('2026-10-15T21:00:00')
COPY = utc('2026-10-15T23:04:00')


def served_at(*starts):
    return lambda workflow, slot: [utc(t) for t in starts]


def test_githubs_late_copy_of_a_slot_a_dispatch_served_is_not_judged():
    fetch = served_at('2026-10-15T21:02:00')
    assert dlj.check_on_time('nhl', 'schedule', COPY, wf('nhl'), fetch) == []


def test_a_late_run_for_a_slot_no_dispatch_served_is_still_flagged():
    for fetch in (served_at(), served_at('2026-10-15T14:01:00'), served_at('2026-10-15T21:20:00')):
        found = dlj.check_on_time('nhl', 'schedule', COPY, wf('nhl'), fetch)
        assert [f.check for f in found] == ['on-time'] and '2.1 hours' in found[0].message


def test_a_late_run_is_flagged_when_the_actions_api_cannot_be_read():
    def broken(workflow, slot):
        raise RuntimeError('HTTP 502')
    assert [f.check for f in dlj.check_on_time('nhl', 'schedule', COPY, wf('nhl'), broken)] == ['on-time']


def test_a_dispatched_run_is_judged_even_when_a_dispatch_served_its_slot():
    """The dispatched run is the one that does the work: its own lateness counts."""
    late_dispatch = SLOT + timedelta(hours=1, minutes=5)
    found = dlj.check_on_time('nhl', 'workflow_dispatch', late_dispatch, wf('nhl'),
                               served_at('2026-10-15T21:02:00', '2026-10-15T22:05:00'))
    assert [f.check for f in found] == ['on-time']


def test_the_slot_is_looked_up_only_for_a_run_that_is_late():
    asked = []

    def fetch(workflow, slot):
        asked.append((workflow, slot))
        return []
    assert dlj.check_on_time('nhl', 'schedule', SLOT + timedelta(minutes=10), wf('nhl'), fetch) == []
    assert asked == []
    dlj.check_on_time('nhl', 'schedule', COPY, wf('nhl'), fetch)
    assert asked == [('nhl-daily.yml', SLOT)]


def test_the_command_line_reads_the_dispatched_runs_and_skips_the_copy(tmp_path, monkeypatch):
    build(tmp_path)
    (tmp_path / '.github' / 'workflows').mkdir(parents=True)
    (tmp_path / '.github' / 'workflows' / 'nhl-daily.yml').write_text(wf('nhl'))
    monkeypatch.setattr(dlj, 'added_at', lambda folder, root: {'1': utc('2026-10-06T22:07:32')})
    args = ['--sport', 'nhl', '--run-event', 'schedule', '--run-started', '2026-10-15T23:04:00Z']
    assert dlj.main(args, NOW, tmp_path, served_at('2026-10-15T21:02:00')) == 0
    assert dlj.main(args, NOW, tmp_path, served_at()) == 1


def test_the_command_line_reads_the_actions_api_by_default():
    """The daily workflows call main() with no fetch of their own."""
    import inspect

    from src.core import missed_dispatch
    assert inspect.signature(dlj.main).parameters['fetch'].default is missed_dispatch._gh_fetch


# --- before-start ---------------------------------------------------------------

PICK = {'game_id': '1', 'home': 'TOR', 'away': 'MTL', 'pick': 'TOR', 'start_utc': '2026-10-06T23:00:00Z'}


def test_a_pick_committed_before_its_start_holds():
    assert dlj.check_before_start({'1': PICK}, {'1': '2026-10-06T23:00:00Z'}, {'1': utc('2026-10-06T22:07:32')}) == []


@pytest.mark.parametrize('committed', ['2026-10-06T23:00:00', '2026-10-06T23:30:00'])
def test_a_pick_committed_at_or_after_its_start_is_flagged(committed):
    found = dlj.check_before_start({'1': PICK}, {'1': '2026-10-06T23:00:00Z'}, {'1': utc(committed)})
    assert [f.check for f in found] == ['before-start'] and 'MTL at TOR' in found[0].message


def test_the_schedules_start_is_the_one_judged_not_the_picks_own():
    """A game moved earlier after its pick was saved: the real start counts."""
    moved = {'1': '2026-10-06T21:00:00Z'}
    assert dlj.check_before_start({'1': PICK}, moved, {'1': utc('2026-10-06T22:07:32')})


def test_a_pick_git_has_not_seen_is_not_judged():
    assert dlj.check_before_start({'1': PICK}, {'1': '2026-10-06T23:00:00Z'}, {}) == []


# --- graded-right -----------------------------------------------------------------

def final(home_score, away_score, status='final'):
    return {'1': {'game_id': '1', 'home': 'TOR', 'away': 'MTL', 'status': status,
                  'home_score': home_score, 'away_score': away_score}}


@pytest.mark.parametrize('scores, result', [((4, 2), 'correct'), ((2, 4), 'wrong')])
def test_a_grade_that_agrees_with_the_score_holds(scores, result):
    assert dlj.check_graded({'1': PICK}, final(*scores), [{'game_id': '1', 'result': result}]) == []


@pytest.mark.parametrize('scores, result', [((4, 2), 'wrong'), ((2, 4), 'correct'), ((4, 2), 'pending')])
def test_a_grade_that_disagrees_with_the_score_is_flagged(scores, result):
    found = dlj.check_graded({'1': PICK}, final(*scores), [{'game_id': '1', 'result': result}])
    assert [f.check for f in found] == ['graded-right'] and f'says {result}' in found[0].message


def test_a_final_game_with_no_graded_row_is_flagged():
    found = dlj.check_graded({'1': PICK}, final(4, 2), [])
    assert [f.check for f in found] == ['graded-right'] and 'no graded row' in found[0].message


def test_a_final_with_no_usable_score_is_flagged():
    assert [f.check for f in dlj.check_graded({'1': PICK}, final(None, 2), [])] == ['graded-right']
    assert [f.check for f in dlj.check_graded({'1': PICK}, final(3, 3), [])] == ['graded-right']


@pytest.mark.parametrize('status', ['scheduled', 'in_progress', 'postponed', 'cancelled'])
def test_a_game_not_final_is_not_due(status):
    assert dlj.check_graded({'1': PICK}, final(None, None, status), []) == []


# --- schedule-fresh ---------------------------------------------------------------

def test_the_schedule_is_fresh_on_its_eastern_day():
    # 02:30 UTC on the 16th is 22:30 on the 15th, Eastern.
    assert dlj.check_fresh('2026-10-15', utc('2026-10-16T02:30:00')) == []


@pytest.mark.parametrize('as_of', ['2026-10-14', None])
def test_a_stale_or_missing_date_is_flagged(as_of):
    found = dlj.check_fresh(as_of, utc('2026-10-15T15:00:00'))
    assert [f.check for f in found] == ['schedule-fresh'] and 'today is 2026-10-15' in found[0].message


# --- git's add times ----------------------------------------------------------------

LOG = ('\x002026-10-07T18:10:00-04:00\n\npredictions/nhl/2026/2.json\n'
       '\x002026-10-06T18:07:40-04:00\n\npredictions/nhl/2026/1.json\npredictions/nhl/2026/2.json\n')


def test_added_at_keeps_each_files_first_add():
    seen = []

    def git(args, cwd):
        seen.append(args)
        return LOG
    out = dlj.added_at(REPO / 'predictions' / 'nhl' / '2026', REPO, git)
    assert out == {'1': utc('2026-10-06T22:07:40'), '2': utc('2026-10-06T22:07:40')}
    assert seen[0][:2] == ['log', '--diff-filter=A'] and seen[0][-1] == 'predictions/nhl/2026'


# --- the whole judge, on a built folder -------------------------------------------------

def build(root, as_of='2026-10-15', result='correct'):
    (root / 'results' / 'nhl').mkdir(parents=True)
    (root / 'predictions' / 'nhl' / '2026').mkdir(parents=True)
    games = [{'game_id': '1', 'home': 'TOR', 'away': 'MTL', 'status': 'final', 'home_score': 4, 'away_score': 2,
              'start_utc': '2026-10-06T23:00:00Z'}]
    (root / 'results' / 'nhl' / 'schedule_2026.json').write_text(json.dumps({'as_of': as_of, 'games': games}))
    (root / 'results' / 'nhl' / 'graded_2026.json').write_text(json.dumps([{'game_id': '1', 'result': result}]))
    (root / 'predictions' / 'nhl' / '2026' / '1.json').write_text(json.dumps(PICK))


NOW = utc('2026-10-15T15:00:00')


def test_a_right_run_leaves_no_finding(tmp_path):
    build(tmp_path)
    assert dlj.judge('nhl', 2026, NOW, {'1': utc('2026-10-06T22:07:32')}, tmp_path) == []
    assert dlj.latest_season('nhl', tmp_path) == 2026


def test_each_wrong_thing_is_reported_once_in_check_order(tmp_path):
    build(tmp_path, as_of='2026-10-14', result='wrong')
    found = dlj.judge('nhl', 2026, NOW, {'1': utc('2026-10-06T23:05:00')}, tmp_path)
    assert [f.check for f in found] == ['before-start', 'graded-right', 'schedule-fresh']
    text = dlj.report(found, 'nhl', 2026)
    assert text.startswith('Line Judge found 3 thing(s) the NHL 2026 daily run left wrong:')


def test_the_command_line_exits_one_on_a_finding_and_writes_the_report(tmp_path, monkeypatch):
    build(tmp_path, as_of='2026-10-14')
    (tmp_path / '.github' / 'workflows').mkdir(parents=True)
    (tmp_path / '.github' / 'workflows' / 'nhl-daily.yml').write_text(wf('nhl'))
    monkeypatch.setattr(dlj, 'added_at', lambda folder, root: {})
    out = tmp_path / 'lj.md'
    assert dlj.main(['--sport', 'nhl', '--report', str(out)], NOW, tmp_path) == 1
    assert '**schedule-fresh**' in out.read_text()
    assert dlj.main(['--sport', 'nba'], NOW, tmp_path) == 0   # no NBA schedule: nothing to judge


# --- the workflows ----------------------------------------------------------------------

@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_each_daily_workflow_judges_after_a_green_run(sport):
    text = wf(sport)
    job = text[text.index('  line-judge:\n'):]
    assert '    needs: [daily]\n' in job and "    if: ${{ needs.daily.result == 'success' }}\n" in job
    assert '          ref: main\n          fetch-depth: 0\n' in job
    # The judge's own exit decides the step: nothing ahead of it on the line.
    assert f'          if python -m src.core.day_line_judge --sport {sport} --run-event "$GITHUB_EVENT_NAME" \\\n' in job
    assert '              --run-started "$started" --report line-judge.md; then\n' in job
    assert f'--title "{sport.upper()}: Line Judge found the daily run left something wrong"' in job
    assert '            exit 1\n' in job


def test_eastern_time_is_read_without_the_tz_database():
    """Windows Python ships no tz database, so ZoneInfo('America/New_York')
    fails at import on Mark's machine while passing on Linux CI (found running
    this judge there on 2026-10-15). pandas carries its own."""
    src = (Path(__file__).resolve().parents[1] / 'src' / 'core' / 'day_line_judge.py').read_text(encoding='utf-8')
    assert not re.search(r'^\s*(from zoneinfo import|import zoneinfo)', src, re.M)
    assert dlj.check_fresh('2026-10-15', datetime(2026, 10, 16, 3, 59, tzinfo=UTC)) == []
