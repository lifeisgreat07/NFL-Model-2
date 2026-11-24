"""MLB's spring probables measurement and the rule that turns it into the daily runs' times (Stage 101 item 2).

Every schedule here is built by hand, so nothing is fetched.

Run with: pytest tests/test_mlb_probables_timing.py -v
"""
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.sports.mlb import probables_timing as p

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / 'experiments' / 'mlb' / 'stage101' / 'registry.json').read_text(encoding='utf-8'))
WORKFLOW = (ROOT / '.github' / 'workflows' / 'mlb-spring-probables.yml').read_text(encoding='utf-8')


def t(s):
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


def game(pk, start='2027-03-01T18:05:00Z', home=None, away=None, state='S', tbd=False, kind='S'):
    teams = {'home': {'team': {'id': 1}}, 'away': {'team': {'id': 2}}}
    if home:
        teams['home']['probablePitcher'] = {'id': home}
    if away:
        teams['away']['probablePitcher'] = {'id': away}
    return {'gamePk': pk, 'gameType': kind, 'gameDate': start, 'officialDate': start[:10], 'teams': teams,
            'status': {'codedGameState': state, 'startTimeTBD': tbd}}


def day(*games):
    return {'dates': [{'games': list(games)}]}


def test_the_first_read_naming_both_probables_is_kept_and_never_moved():
    s = {}
    assert p.record(s, day(game(1, home=10)), t('2027-02-28T12:07:00'))
    assert s['games']['1']['first_named_utc'] is None
    assert p.record(s, day(game(1, home=10, away=20)), t('2027-02-28T18:37:00'))
    assert not p.record(s, day(game(1, home=11, away=21)), t('2027-03-01T12:07:00'))
    row = s['games']['1']
    assert (row['first_named_utc'], row['home_probable'], row['away_probable']) == ('2027-02-28T18:37:00Z', 10, 20)


def test_a_game_read_after_it_started_is_closed_and_a_late_naming_does_not_count():
    s = {}
    p.record(s, day(game(1)), t('2027-03-01T12:07:00'))
    assert p.record(s, day(game(1, home=10, away=20, state='I')), t('2027-03-01T18:07:00'))
    row = s['games']['1']
    assert row['closed'] and row['first_named_utc'] is None and row['state'] == 'I'


def test_the_listed_start_follows_the_schedule_until_first_pitch():
    s = {}
    p.record(s, day(game(1, start='2027-03-01T18:05:00Z')), t('2027-02-28T12:07:00'))
    p.record(s, day(game(1, start='2027-03-01T20:10:00Z')), t('2027-03-01T12:07:00'))
    assert s['games']['1']['start_utc'] == '2027-03-01T20:10:00Z'


def test_only_spring_games_are_kept():
    s = {}
    p.record(s, day(game(1), game(2, kind='E')), t('2027-02-28T12:07:00'))
    assert list(s['games']) == ['1']


def test_nothing_is_read_after_the_registrys_last_day_or_in_another_year(tmp_path):
    assert p.window(t('2027-03-21T23:30:00')) == (p.LAST_DAY, p.LAST_DAY)
    assert p.window(t('2027-03-19T12:00:00'))[1] == p.LAST_DAY
    assert p.window(t('2027-03-22T12:00:00')) is None
    assert p.window(t('2028-02-25T12:00:00')) is None
    asked = []
    out = p.run_record(t('2027-03-22T12:00:00'), lambda url: asked.append(url), tmp_path / 'r.json')
    assert asked == [] and 'nothing read' in out and not (tmp_path / 'r.json').exists()


def test_a_read_with_no_change_writes_nothing(tmp_path):
    path = tmp_path / 'r.json'

    def got(url):
        return day(game(1, home=10, away=20))
    p.run_record(t('2027-02-27T12:07:00'), got, path)
    first = path.read_text(encoding='utf-8')
    assert 'nothing changed' in p.run_record(t('2027-02-27T12:37:00'), got, path)
    assert path.read_text(encoding='utf-8') == first


def test_the_saving_run_is_the_last_at_its_mark_an_hour_before_first_pitch():
    start = t('2027-03-01T18:05:00')
    assert p.saving_run(start, 17 * 60) == t('2027-03-01T17:00:00')
    assert p.saving_run(start, 17 * 60 + 30) == t('2027-02-28T17:30:00')
    assert p.saving_run(t('2027-03-01T17:00:00'), 16 * 60) == t('2027-03-01T16:00:00')


def test_postponed_unset_and_unstarted_games_are_not_measured():
    s = {'games': {
        'played': {'start_utc': '2027-03-01T18:05:00Z', 'closed': True, 'start_time_tbd': False, 'state': 'F',
                   'first_named_utc': None},
        'postponed': {'start_utc': '2027-03-01T18:05:00Z', 'closed': True, 'start_time_tbd': False, 'state': 'D',
                      'first_named_utc': None},
        'unset': {'start_utc': '2027-03-01T08:33:00Z', 'closed': True, 'start_time_tbd': True, 'state': 'F',
                  'first_named_utc': None},
        'later': {'start_utc': '2027-03-05T18:05:00Z', 'closed': False, 'start_time_tbd': False, 'state': 'S',
                  'first_named_utc': None}}}
    assert p.measured(s, t('2027-03-02T00:00:00')) == [(t('2027-03-01T18:05:00'), None)]


def store_of(games):
    return {'games': {str(i): {'start_utc': p.stamp(start), 'closed': True, 'start_time_tbd': False, 'state': 'F',
                               'first_named_utc': p.stamp(named) if named else None}
                      for i, (start, named) in enumerate(games)}}


def test_the_rule_takes_the_latest_set_that_names_the_most():
    # Day games at 18:05 UTC, each named at 15:00 UTC that day: a set saves them named only with a run from 15:00
    # to 17:00. The latest such set on MLB's day has 17:00 and the two latest marks of the day, 09:00 and 09:30.
    games = [(t(f'2027-03-{d:02d}T18:05:00'), t(f'2027-03-{d:02d}T15:00:00')) for d in range(1, 21)]
    out = p.choose(store_of(games), t('2027-03-22T00:00:00'))
    assert (out['share'], out['best_share'], out['below_90'], out['games']) == (1.0, 1.0, False, 20)
    assert out['times_utc'] == ['17:00', '09:00', '09:30']


def test_every_set_of_three_is_scored_as_any_of_its_runs_naming_the_game():
    import itertools

    import numpy as np
    n = np.random.default_rng(7).random((40, 48)) < 0.2
    brute = [float(n[:, list(s)].any(axis=1).mean()) for s in itertools.combinations(range(48), 3)]
    assert p.shares(n) == pytest.approx(brute) and len(brute) == 17296


def test_latest_is_read_on_mlbs_day_so_half_past_midnight_utc_is_later_than_half_past_eleven():
    assert p.lateness([30]) > p.lateness([23 * 60 + 30]) > p.lateness([10 * 60])


def early_and_late(early_games):
    # 120 games at 17:05 UTC named at 11:00 (any run from 11:00 to 16:00 saves them named), and `early_games` at
    # 13:05 named at 11:00 (only a run at 11:00 to 12:00 does).
    late = [(t('2027-03-01T17:05:00') + timedelta(days=i % 20), t('2027-03-01T11:00:00') + timedelta(days=i % 20))
            for i in range(120)]
    early = [(t('2027-03-02T13:05:00'), t('2027-03-02T11:00:00'))] * early_games
    return p.choose(store_of(late + early), t('2027-03-22T00:00:00'))


def test_a_later_set_within_a_point_of_the_best_is_chosen():
    out = early_and_late(1)  # 16:00 names 120 of 121, 99.2%: within a point of 100%
    assert out['best_share'] == 1.0 and out['share'] == round(120 / 121, 4)
    assert out['times_utc'] == ['16:00', '09:00', '09:30']


def test_a_set_more_than_a_point_below_the_best_is_not():
    out = early_and_late(2)  # 16:00 names 120 of 122, 98.4%
    assert out['share'] == 1.0 and out['times_utc'] == ['12:00', '09:00', '09:30']


def test_below_ninety_the_times_stand_and_the_file_says_so():
    games = [(t(f'2027-03-{d:02d}T18:05:00'), None) for d in range(1, 11)]
    games += [(t('2027-03-11T18:05:00'), t('2027-03-11T15:00:00'))]
    out = p.choose(store_of(games), t('2027-03-22T00:00:00'))
    assert out['below_90'] and out['never_named'] == 10 and len(out['times_utc']) == 3


def test_nothing_measured_chooses_nothing():
    with pytest.raises(ValueError, match='no measured spring game'):
        p.choose({'games': {}}, t('2027-03-22T00:00:00'))


def test_the_module_measures_what_the_registry_registered():
    runs = REGISTRY['forward_test']['runs']
    assert 'every 30 minutes' in runs['measurement'] and '2027-03-21' in runs['measurement']
    assert p.LAST_DAY.isoformat() == '2027-03-21' and len(p.MARKS) == 48 and p.RUNS == 3
    assert '48 half-hour marks' in runs['rule'] and 'one percentage point' in runs['rule'] and '90%' in runs['rule']
    assert (p.WITHIN, p.FLOOR, p.SLACK) == (0.01, 0.90, timedelta(hours=1))
    assert p.CHOSEN.relative_to(ROOT).as_posix() in runs['times']


def test_the_workflow_reads_every_half_hour_in_february_and_march_and_commits_only_mlbs_data():
    assert "cron: '7,37 * * 2,3 *'" in WORKFLOW
    assert 'python -m src.sports.mlb.probables_timing record' in WORKFLOW
    assert 'git add data/mlb/spring_probables_2027.json' in WORKFLOW
