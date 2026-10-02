"""
The rest of the weekly pipeline, run for real on the synthetic league in
tests/synthetic_league.py.

Stage 33 item 20, second part. tests/test_weekly_update_end_to_end.py runs
weekly_update.main(). This file follows the week it locks through the
steps that come after:

  weekend_refresh  -- the Saturday/Sunday status snapshot of a locked week
  grade_predictions -- grading the locked picks against the final scores,
                      including a tie
  check_drift      -- the drift check reading those graded files
  backtest         -- the walk-forward evaluation, on the same fixture
  simulate_season  -- the playoff simulation, checked on invariants it
                      must hold whatever the ratings are

Each step reads what the one before it wrote, so a change to a file's shape
that one step would accept and the next would not fails here. The loaders
are the only substitutes, plus the simulation's draw count.

Run with: pytest tests/test_pipeline_chain_end_to_end.py -v
"""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from src.research import backtest as bt  # noqa: E402
from src.pipeline import check_drift as cd  # noqa: E402
from src.pipeline import data_loader  # noqa: E402
from src.pipeline import grade_predictions as gp  # noqa: E402
from src.pipeline import simulate_season as ss  # noqa: E402
import synthetic_league as league  # noqa: E402
from src.pipeline import weekend_refresh as wr  # noqa: E402
from src.pipeline import weekly_update as wu  # noqa: E402
from src.pipeline.ratings_engine import build_qb_ratings, build_team_ratings, prep_plays  # noqa: E402

H = pd.Timedelta(hours=1)
S, W = league.TARGET, league.TARGET_WEEK
# Week 5's results, in round_robin(5) order: a tie, then two home wins and
# an away win.
SCORES = [(20, 20), (27, 17), (31, 24), (10, 13)]
FEATURES = ['off_matchup', 'def_matchup', 'qb_matchup', 'qb_change_diff']


@pytest.fixture
def chain(monkeypatch, tmp_path):
    """Lock week 5 with weekly_update.main(), then return
    (dirs, the schedules with week 5 played, now)."""
    dirs = {'pred': tmp_path / 'predictions', 'results': tmp_path / 'results',
            'status': tmp_path / 'data' / 'game_status', 'data': tmp_path / 'data'}
    for p in dirs.values():
        p.mkdir(parents=True, exist_ok=True)
    for name, path in (('PRED_DIR', dirs['pred']), ('SKIPPED_DIR', dirs['pred'] / 'skipped'),
                       ('PREVIEW_DIR', dirs['pred'] / 'preview'), ('DATA_DIR', dirs['data']),
                       ('LINE_HISTORY_DIR', dirs['data'] / 'line_history'),
                       ('QB_OVERRIDE_DIR', dirs['data'] / 'qb_overrides')):
        path.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(wu, name, path)
    real_simulate = wu.simulate_season
    monkeypatch.setattr(wu, 'simulate_season',
                        lambda *a, n_sim=10000, **k: real_simulate(*a, n_sim=200, **k))
    now = pd.Timestamp.now(tz='UTC')
    pbp, schedules = league.build(now, [H, 2 * H, 3 * H, 4 * H])
    monkeypatch.setattr(wu, 'load_plays', lambda seasons: pbp[pbp['season'].isin(seasons)])
    monkeypatch.setattr(wu, 'load_schedule',
                        lambda season: schedules.get(season, league.empty_schedule()))
    wu.main(S, W)
    assert (dirs['pred'] / f'{S}_week{W}.json').exists(), "the week did not lock"

    played = league.play_week(schedules, W, SCORES)
    monkeypatch.setattr(gp, 'PRED_DIR', dirs['pred'])
    monkeypatch.setattr(gp, 'RESULTS_DIR', dirs['results'])
    monkeypatch.setattr(data_loader, 'load_schedule', lambda season: played[season])
    monkeypatch.setattr(cd, 'RESULTS_DIR', dirs['results'])
    return dirs, played, now


def refresh(dirs, schedules, now):
    return wr.main(['--season', str(S)], now=now, load=lambda season: schedules[season],
                   pred_dir=dirs['pred'], results_dir=dirs['results'], status_dir=dirs['status'])


def graded(dirs):
    return json.loads((dirs['results'] / f'{S}_week{W}_graded.json').read_text(encoding='utf-8'))


# --- weekend refresh -> grading -> drift ------------------------------------

def test_the_weekend_refresh_reads_the_locked_week_as_final(chain):
    dirs, played, now = chain
    assert refresh(dirs, played, now + 6 * H) == 0
    snap = json.loads((dirs['status'] / f'{S}_week{W}.json').read_text(encoding='utf-8'))
    assert [g['status'] for g in snap['games']] == ['final'] * 4
    by_pair = {(g['home'], g['away']): (g['home_score'], g['away_score']) for g in snap['games']}
    assert by_pair == {pair: score for pair, score in zip(league.round_robin(W), SCORES)}


def test_the_locked_picks_are_graded_on_the_side_each_model_favoured(chain):
    dirs, _, _ = chain
    gp.main(S, W)
    rows = graded(dirs)
    assert len(rows) == 4
    result = {(r['home'], r['away']): r for r in rows}
    for (home, away), (hs, as_) in zip(league.round_robin(W), SCORES):
        r = result[(home, away)]
        if hs == as_:
            assert r['result'] == 'tie' and r['actual_home_win'] is None
            assert r['model_a_correct'] is r['model_b_correct'] is r['market_correct'] is None
            continue
        won = int(hs > as_)
        assert r['actual_home_win'] == won
        for model, prob in (('model_a', 'model_a_home_win_prob'), ('model_b', 'model_b_home_win_prob'),
                            ('market', 'market_prob_home')):
            assert r[f'{model}_correct'] == int((r[prob] >= 0.5) == bool(won)), (model, r)


def test_a_graded_week_leaves_nothing_for_the_weekend_refresh(chain, capsys):
    dirs, played, now = chain
    gp.main(S, W)
    capsys.readouterr()
    refresh(dirs, played, now + 6 * H)
    assert 'nothing to refresh' in capsys.readouterr().out


def test_the_drift_check_reads_the_graded_week_and_leaves_out_the_tie(chain, capsys):
    dirs, _, _ = chain
    gp.main(S, W)
    capsys.readouterr()
    assert cd.main() == 0
    out = capsys.readouterr().out
    assert 'Loaded 4 live' in out
    assert out.count('Live games graded: 3') == 2, out
    assert 'too early to test statistically' in out


# --- backtest and simulation on the same fixture ----------------------------

@pytest.fixture(scope='module')
def history():
    pbp, schedules = league.build(pd.Timestamp.now(tz='UTC'), [H, 2 * H, 3 * H, 4 * H])
    plays, week_keys, week_to_idx = prep_plays(pbp)
    ratings = build_team_ratings(plays, week_keys, upto_cutoff_i=None)
    qb = build_qb_ratings(pbp)
    lookup = wu.build_qb_change_lookup(qb, sorted(schedules))
    hist = wu.build_historical_features(plays, week_keys, week_to_idx, ratings, qb,
                                        schedules, ol_lookup=None, qb_change_lookup=lookup)
    return hist, schedules


def test_the_backtest_scores_every_target_game_it_has_features_for(history):
    hist, _ = history
    expected = len(hist[(hist['season'] == S)].dropna(subset=FEATURES + ['home_win']))
    assert expected == 4 * league.PLAYED_WEEKS
    weekly = bt.backtest(hist, FEATURES, [S])
    seasonal = bt.backtest(hist, FEATURES, [S], refit_every_n_weeks=None)
    for m in (weekly, seasonal):
        assert m['n'] == expected
        assert 0 <= m['accuracy'] <= 1 and 0 < m['brier'] < 1 and m['log_loss'] > 0
        assert 0 <= m['auc'] <= 1


def test_the_backtest_never_trains_on_the_week_it_scores(history, monkeypatch):
    """Walk-forward: every fit for week w sees only games before it."""
    hist, _ = history
    seen = []
    real = bt.LogisticRegression

    class Spy(real):
        def fit(self, X, y, *a, **k):
            seen.append(len(X))
            return super().fit(X, y, *a, **k)
    monkeypatch.setattr(bt, 'LogisticRegression', Spy)
    bt.backtest(hist, FEATURES, [S])
    d2 = hist.dropna(subset=FEATURES + ['home_win'])
    before = [len(d2[(d2['season'] < S) | ((d2['season'] == S) & (d2['week'] < w))])
              for w in range(1, league.PLAYED_WEEKS + 1)]
    assert seen == before


def test_the_simulation_holds_its_invariants_on_the_fixture(history):
    hist, schedules = history
    ratings = {t: (0.1 * (4 - i), 0.0) for i, t in enumerate(league.TEAMS)}
    out = ss.simulate_season(ratings, schedules[S], ss.fit_simple_win_model(hist), n_sim=300)
    assert set(out['team']) == set(ss.TEAM_DIV)
    for div, grp in out.groupby('division'):
        assert grp['division_win_pct'].sum() == pytest.approx(100, abs=0.5), div
    for conf in ('AFC', 'NFC'):
        teams = out[out['division'].str.startswith(conf)]
        assert teams['playoff_pct'].sum() == pytest.approx(700, abs=1), conf
    assert ((out['playoff_pct'] >= out['division_win_pct']) & (out['playoff_pct'] <= 100)).all()
