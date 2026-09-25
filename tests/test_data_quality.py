"""
Every data-quality rule, run over synthetic data built to trip it.

src/data_quality.py stops the weekly run on an ERROR, which on a locking run
costs a week of picks. So each rule is proved twice: it stays quiet on a clean
season, and it fires on data broken in exactly the way it names. A rule that
has only ever seen clean data has never been shown to check anything.

Run with: pytest tests/test_data_quality.py -v
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import data_quality as dq  # noqa: E402
from data_loader import REQUIRED_PBP_COLS  # noqa: E402

SEASON = 2026
TEAMS = sorted(dq.NFL_TEAMS)


def schedule(completed_through=0):
    """A clean 272-game regular season: 17 weeks of 16 games."""
    rows = []
    for week in range(1, 18):
        order = TEAMS[week % 32:] + TEAMS[:week % 32]
        for i in range(16):
            done = week <= completed_through
            rows.append({
                'season': SEASON, 'week': week, 'game_type': 'REG',
                'away_team': order[i], 'home_team': order[i + 16],
                'home_score': 24.0 if done else np.nan,
                'away_score': 17.0 if done else np.nan,
                'spread_line': -3.0, 'gameday': '2026-09-13',
                'gametime': '13:00', 'weekday': 'Sunday',
            })
    return pd.DataFrame(rows)


def plays(weeks):
    rows = []
    for week in weeks:
        for kind in ('pass', 'run'):
            row = {c: 0 for c in REQUIRED_PBP_COLS}
            row.update(season=SEASON, week=week, season_type='REG',
                       posteam='KC', defteam='BUF', epa=0.1, play_type=kind,
                       passer_player_id='00-0000001', passer_player_name='A QB')
            rows.append(row)
    return pd.DataFrame(rows, columns=list(REQUIRED_PBP_COLS) + ['play_type'])


# --- the clean case ----------------------------------------------------------

def test_a_clean_season_has_no_findings():
    report = dq.run_checks(plays([1, 2, 3]), schedule(completed_through=3), SEASON)
    assert report.errors == [] and report.warnings == []


def test_enforce_passes_clean_data_and_says_so():
    lines = []
    dq.enforce(plays([1, 2]), schedule(completed_through=2), SEASON, out=lines.append)
    assert lines == ['  data quality: no findings']


# --- schedule errors -----------------------------------------------------------

def test_a_missing_schedule_column_is_an_error():
    report = dq.check_schedule(schedule().drop(columns=['gametime']), SEASON)
    assert any('gametime' in e for e in report.errors)


def test_a_short_season_is_only_a_warning():
    """An odd game count corrupts no single pick, and an ERROR on a locking
    run costs the whole week. So it is reported, and the run goes on."""
    s = schedule()
    report = dq.check_schedule(s[s['week'] != 17], SEASON)
    assert report.errors == []
    assert any('256 regular-season games' in w for w in report.warnings)


def test_a_game_listed_twice_is_an_error():
    s = schedule()
    s = pd.concat([s, s.iloc[[0]]], ignore_index=True)
    # 273 rows, so the count rule warns too; the duplicate rule must fire on
    # its own terms, as an error naming the game.
    report = dq.check_schedule(s, SEASON)
    first = s.iloc[0]
    assert any('twice' in e and f"{first.away_team}@{first.home_team}" in e
               for e in report.errors)


def test_an_unknown_team_is_an_error():
    s = schedule()
    s.loc[0, 'home_team'] = 'OAK'
    report = dq.check_schedule(s, SEASON)
    assert any("['OAK']" in e for e in report.errors)


def test_a_score_on_one_side_only_is_an_error():
    s = schedule(completed_through=1)
    s.loc[0, 'away_score'] = np.nan
    report = dq.check_schedule(s, SEASON)
    assert any('one side only' in e for e in report.errors)


def test_an_unpublished_schedule_is_a_warning_not_a_failure():
    """Spring runs happen before nflverse publishes the season. The weekly
    run exits cleanly there, and the check must not turn that red."""
    report = dq.check_schedule(schedule().iloc[0:0], SEASON)
    assert report.errors == [] and report.warnings


def test_placeholder_rows_are_not_duplicates():
    """Playoff rows can carry no teams yet. Two of them are not a game
    listed twice."""
    s = schedule()
    blank = {c: np.nan for c in s.columns}
    blank.update(season=SEASON, week=19, game_type='WC')
    s = pd.concat([s, pd.DataFrame([blank, blank])], ignore_index=True)
    assert dq.check_schedule(s, SEASON).errors == []


# --- play-by-play against the schedule -----------------------------------------

def test_a_missing_plays_column_is_an_error():
    report = dq.check_plays(plays([1]).drop(columns=['qb_epa']),
                            schedule(completed_through=1), SEASON)
    assert any('qb_epa' in e for e in report.errors)


def test_an_older_completed_week_with_no_plays_is_an_error():
    report = dq.check_plays(plays([1, 3]), schedule(completed_through=3), SEASON)
    assert any('week 2' in e for e in report.errors)
    assert not any('week 2' in w for w in report.warnings)


def test_the_latest_completed_week_with_no_plays_is_only_a_warning():
    """Tuesday's run can land before nflverse has rebuilt with Monday night
    in it. That is normal, and must not cost the week its picks."""
    report = dq.check_plays(plays([1, 2]), schedule(completed_through=3), SEASON)
    assert report.errors == []
    assert any('week 3' in w for w in report.warnings)


def test_plays_with_no_epa_are_a_warning():
    p = plays([1])
    p['epa'] = np.nan
    report = dq.check_plays(p, schedule(completed_through=1), SEASON)
    assert report.errors == []
    assert any('no EPA' in w for w in report.warnings)


def test_no_completed_weeks_means_nothing_to_check_in_plays():
    assert dq.check_plays(plays([]), schedule(), SEASON).lines() == []


# --- enforce --------------------------------------------------------------------

def test_enforce_stops_the_run_on_an_error_and_prints_it_first():
    s = schedule()
    s.loc[0, 'home_team'] = 'OAK'
    lines = []
    with pytest.raises(dq.DataQualityError):
        dq.enforce(None, s, SEASON, out=lines.append)
    assert any('OAK' in line for line in lines), (
        'the run stopped without saying why; the error must be in the log')


def test_enforce_does_not_stop_on_warnings():
    report = dq.enforce(plays([1, 2]), schedule(completed_through=3), SEASON,
                        out=lambda _line: None)
    assert report.ok and report.warnings


# --- wired into the weekly run -----------------------------------------------

def test_the_weekly_run_enforces_the_checks_before_fitting():
    """A check nothing calls checks nothing. It has to run before the models
    are fitted, or a bad week is already inside the picks when it fires."""
    src = (Path(__file__).parent.parent / 'src' / 'weekly_update.py').read_text(encoding='utf-8')
    main = src[src.index('def main(season, week):'):]
    assert 'enforce_data_quality(' in main
    assert main.index('enforce_data_quality(') < main.index('model_a.fit(')
