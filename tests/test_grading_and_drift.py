"""First tests for grading and for the drift check (Stage 24 item 9).

The 2026-09-28 audit, confirmed: `src/pipeline/grade_predictions.py` and
`check_drift.one_proportion_z_test` had no tests of their own. Grading is
what turns a saved pick into the season's record, and the drift test is
what raises "Model drift detected". These pin the behaviour they have
today. A TIE was graded as an away win until Stage 25 item 1; its test is
at the end of the grading section.
"""
import json
import math
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]

from src.pipeline import check_drift as cd  # noqa: E402
from src.pipeline import data_loader  # noqa: E402
from src.pipeline import grade_predictions as gp  # noqa: E402

PICKS = [
    {'home': 'GB', 'away': 'ATL', 'market_prob_home': 0.70,
     'model_a_home_win_prob': 0.60, 'model_b_home_win_prob': 0.68},
    {'home': 'MIA', 'away': 'KC', 'market_prob_home': 0.20,
     'model_a_home_win_prob': 0.57, 'model_b_home_win_prob': 0.14},
    {'home': 'SEA', 'away': 'SF', 'market_prob_home': 0.45,
     'model_a_home_win_prob': None, 'model_b_home_win_prob': 0.50},
]


def schedule(rows):
    return pd.DataFrame([dict(season=2026, week=3, **r) for r in rows])


@pytest.fixture
def week(tmp_path, monkeypatch):
    preds, results = tmp_path / 'predictions', tmp_path / 'results'
    preds.mkdir()
    results.mkdir()
    (preds / '2026_week3.json').write_text(json.dumps(PICKS), encoding='utf-8')
    monkeypatch.setattr(gp, 'PRED_DIR', preds)
    monkeypatch.setattr(gp, 'RESULTS_DIR', results)

    def grade(rows):
        monkeypatch.setattr(data_loader, 'load_schedule', lambda season: schedule(rows))
        gp.main(2026, 3)
        return json.loads((results / '2026_week3_graded.json').read_text(encoding='utf-8'))
    return grade


# ---- grading ---------------------------------------------------------------

def test_each_model_is_graded_on_the_side_it_favoured(week):
    graded = week([
        {'home_team': 'GB', 'away_team': 'ATL', 'home_score': 27, 'away_score': 20},
        {'home_team': 'MIA', 'away_team': 'KC', 'home_score': 24, 'away_score': 17},
        {'home_team': 'SEA', 'away_team': 'SF', 'home_score': 10, 'away_score': 13},
    ])
    by = {g['home']: g for g in graded}
    assert (by['GB']['actual_home_win'], by['GB']['market_correct'],
            by['GB']['model_a_correct'], by['GB']['model_b_correct']) == (1, 1, 1, 1)
    # MIA won: the market and Model B had KC, Model A had MIA.
    assert (by['MIA']['actual_home_win'], by['MIA']['market_correct'],
            by['MIA']['model_a_correct'], by['MIA']['model_b_correct']) == (1, 0, 1, 0)
    # A missing probability is not graded; exactly 0.50 counts as the home pick.
    assert by['SEA']['model_a_correct'] is None
    assert by['SEA']['model_b_correct'] == 0


def test_a_partial_week_grades_only_the_games_with_a_result(week):
    graded = week([
        {'home_team': 'GB', 'away_team': 'ATL', 'home_score': 27, 'away_score': 20},
        {'home_team': 'MIA', 'away_team': 'KC', 'home_score': float('nan'), 'away_score': float('nan')},
        {'home_team': 'SEA', 'away_team': 'SF', 'home_score': float('nan'), 'away_score': float('nan')},
    ])
    assert [g['home'] for g in graded] == ['GB']


def test_a_game_missing_from_the_schedule_is_not_graded(week):
    """A cancelled game never gets a row with a score."""
    graded = week([{'home_team': 'GB', 'away_team': 'ATL', 'home_score': 27, 'away_score': 20}])
    assert [g['home'] for g in graded] == ['GB']


def test_grading_the_same_week_twice_writes_the_same_file(week):
    rows = [{'home_team': 'GB', 'away_team': 'ATL', 'home_score': 27, 'away_score': 20},
            {'home_team': 'MIA', 'away_team': 'KC', 'home_score': 24, 'away_score': 17}]
    assert week(rows) == week(rows)


def test_a_tie_is_graded_with_no_winner_and_no_pick_scored(week):
    """Stage 25 item 1. Before, 20-20 made actual_home_win 0: every home
    pick scored wrong and every away pick right, for a game nobody won."""
    graded = week([
        {'home_team': 'GB', 'away_team': 'ATL', 'home_score': 20, 'away_score': 20},
        {'home_team': 'MIA', 'away_team': 'KC', 'home_score': 24, 'away_score': 17},
    ])
    by = {g['home']: g for g in graded}
    tie = by['GB']
    assert tie['result'] == 'tie'
    assert (tie['actual_home_win'], tie['market_correct'],
            tie['model_a_correct'], tie['model_b_correct']) == (None, None, None, None)
    assert 'result' not in by['MIA'] and by['MIA']['actual_home_win'] == 1


def test_graded_correct_edges():
    assert gp.graded_correct(None, 1) is None
    assert gp.graded_correct(0.5, 1) == 1 and gp.graded_correct(0.5, 0) == 0
    assert gp.graded_correct(0.49, 0) == 1


# ---- the drift test --------------------------------------------------------

def test_no_games_or_no_spread_gives_no_verdict():
    assert cd.one_proportion_z_test(0, 0, 0.6) == (None, False)
    assert cd.one_proportion_z_test(5, 10, 1.0) == (None, False)


def test_the_z_score_is_the_standard_one():
    # 30 of 100 against 0.6: the standard error comes from the EXPECTED
    # proportion (0.6 * 0.4), which differs here from the observed one
    # (0.3 * 0.7), so using the wrong one changes z. (40 of 100 would not
    # tell them apart: 0.4 * 0.6 is 0.6 * 0.4.)
    z, flagged = cd.one_proportion_z_test(30, 100, 0.6)
    assert math.isclose(z, (0.30 - 0.60) / math.sqrt(0.6 * 0.4 / 100))
    assert flagged, 'a z of about -6.1 is well past the threshold'


def test_only_underperformance_is_flagged():
    z, flagged = cd.one_proportion_z_test(80, 100, 0.6)
    assert z > cd.SIGNIFICANCE_Z and not flagged


def test_a_z_exactly_on_the_threshold_is_flagged(monkeypatch):
    """No whole number of games lands z exactly on -1.96, so the threshold is
    moved onto a z the test has computed: then 'on the line' is exact, and a
    strict < instead of <= goes red here."""
    z, _ = cd.one_proportion_z_test(40, 100, 0.5)
    monkeypatch.setattr(cd, 'SIGNIFICANCE_Z', -z)
    assert cd.one_proportion_z_test(40, 100, 0.5) == (z, True)
    monkeypatch.setattr(cd, 'SIGNIFICANCE_Z', -z + 1e-9)
    assert cd.one_proportion_z_test(40, 100, 0.5) == (z, False)


def test_below_the_minimum_sample_nothing_is_flagged(capsys):
    records = [{'model_a_correct': 0}] * (cd.MIN_GAMES_TO_TEST - 1)
    assert cd.check_model(records, 'model_a_correct', 0.65, 'Model A') is False
    assert 'too early' in capsys.readouterr().out


def test_live_results_leave_out_the_backtest_seasons(tmp_path, monkeypatch):
    backtest = min(cd.BACKTEST_SEASONS)
    (tmp_path / f'{backtest}_week1_graded.json').write_text('[{"x": 1}]', encoding='utf-8')
    (tmp_path / '2026_week1_graded.json').write_text('[{"x": 2}]', encoding='utf-8')
    monkeypatch.setattr(cd, 'RESULTS_DIR', tmp_path)
    assert cd.load_live_results() == [{'x': 2}]


# --- the baseline (Stage 35) --------------------------------------------------

def test_the_baseline_is_the_published_backtest():
    """The drift check compares with the numbers the page and README print:
    data/calibration.json, not a copy of them. The old literal was one game
    off each way (0.628 and 0.682 against 682 and 742 of 1087)."""
    cal = json.loads((ROOT / 'data' / 'calibration.json').read_text(encoding='utf-8'))['models']
    got = cd.backtest_baseline()
    assert set(got) == {'model_a', 'model_b'}
    for model in got:
        assert got[model] == cal[model]['metrics']
        assert got[model]['n'] == 1087


def test_main_compares_live_accuracy_with_the_file(tmp_path, monkeypatch, capsys):
    """main() reads accuracy from the baseline file, so a file saying 90%
    is what the printed baseline says."""
    cal = tmp_path / 'calibration.json'
    cal.write_text(json.dumps({'models': {m: {'metrics': {'accuracy': 0.9, 'n': 1087}}
                                          for m in ('model_a', 'model_b')}}), encoding='utf-8')
    monkeypatch.setattr(cd, 'CALIBRATION', cal)
    monkeypatch.setattr(cd, 'RESULTS_DIR', tmp_path)
    (tmp_path / '2026_week1_graded.json').write_text(
        json.dumps([{'model_a_correct': 1, 'model_b_correct': 1}]), encoding='utf-8')
    assert cd.main() == 0
    out = capsys.readouterr().out
    assert out.count('Backtest baseline: 90.0%') == 2, out


def test_a_missing_baseline_is_reported_and_does_not_fail_the_run(tmp_path, monkeypatch, capsys):
    """drift_alert.py promises the drift check never fails the weekly run, and
    a check that did not run must not read as clean: the verdict line says
    NOT RUN, which the run summary carries (weekly_summary reads the last
    'DRIFT CHECK:' line), with a WARNING line it also lists."""
    monkeypatch.setattr(cd, 'CALIBRATION', tmp_path / 'absent.json')
    monkeypatch.setattr(cd, 'RESULTS_DIR', tmp_path)
    assert cd.main() == 0
    out = capsys.readouterr().out
    assert 'DRIFT CHECK: NOT RUN (no backtest baseline)' in out
    assert 'DRIFT CHECK: OK' not in out
    assert 'WARNING: no backtest baseline in absent.json' in out
