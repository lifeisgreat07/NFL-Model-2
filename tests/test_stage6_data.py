"""
Stage 6's Next Gen Stats machinery, checked over synthetic inputs.

The registry defines "trailing" as the production QB rating's shape applied
to any weekly statistic, so the first test holds stage6_data.Trailing to
ratings_engine.build_qb_ratings' trailing_rating on the same plays -- not to
a restatement of it. The rest: nothing a week produces reaches that week's
inputs, the screen's arithmetic points the right way, the N1 rule is the
registered one, and the matchup feature is home minus away.

Run with: pytest tests/test_stage6_data.py -v
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).parent.parent

from src.sports.nfl.ratings_engine import build_qb_ratings
from src.sports.nfl.research import stage6_data as s6
from src.sports.nfl.research import stage6_run as s6r


def synthetic_plays(seed=0, seasons=(2016, 2017), weeks=6):
    rng = np.random.default_rng(seed)
    rows = []
    for s in seasons:
        for w in range(1, weeks + 1):
            for pid, mu in (('A', 0.2), ('B', -0.1), ('C', 0.0)):
                if pid == 'C' and (s, w) < (2017, 3):
                    continue  # C first plays in 2017 week 3
                for _ in range(rng.integers(20, 40)):
                    rows.append({'season': s, 'week': w, 'season_type': 'REG', 'posteam': 'T' + pid,
                                 'qb_dropback': 1, 'qb_epa': rng.normal(mu, 1.0),
                                 'passer_player_id': pid, 'passer_player_name': pid})
    return pd.DataFrame(rows)


def weekly_epa(qb):
    g = qb['plays'].groupby(['gwidx', 'passer_player_id'])['qb_epa'].agg(['mean', 'count']).reset_index()
    return pd.DataFrame({'player': g['passer_player_id'], 'gwidx': g['gwidx'],
                         'volume': g['count'], 'value': g['mean']})


def test_trailing_is_the_production_qb_rating_on_the_same_plays():
    qb = build_qb_ratings(synthetic_plays())
    t = s6.Trailing(weekly_epa(qb), len(qb['week_keys']))
    checked = 0
    for pid in ('A', 'B', 'C', 'nobody'):
        for cutoff in range(0, len(qb['week_keys']) + 1):
            assert t.value(pid, cutoff) == pytest.approx(qb['trailing_rating'](pid, cutoff), abs=1e-12), (pid, cutoff)
            checked += 1
    assert checked == 4 * 13


def test_a_weeks_own_data_never_reaches_its_value():
    qb = build_qb_ratings(synthetic_plays())
    weekly = weekly_epa(qb)
    t = s6.Trailing(weekly, len(qb['week_keys']))
    changed = weekly.copy()
    changed.loc[changed['gwidx'] == 7, 'value'] += 10.0
    t2 = s6.Trailing(changed, len(qb['week_keys']))
    for pid in ('A', 'B', 'C'):
        assert t.value(pid, 7) == t2.value(pid, 7)
        assert t.value(pid, 8) != t2.value(pid, 8)


def test_no_history_is_the_league_mean_as_of_the_cutoff():
    weekly = pd.DataFrame({'player': ['A', 'A', 'B'], 'gwidx': [0, 1, 2],
                           'volume': [10.0, 30.0, 20.0], 'value': [1.0, 2.0, 100.0]})
    t = s6.Trailing(weekly, 4)
    assert t.value('new', 0) == 0.0
    assert t.value('new', 2) == pytest.approx((10 * 1 + 30 * 2) / 40)   # B's week 2 not yet in
    assert t.value('new', 3) == pytest.approx((10 + 60 + 2000) / 60)


def test_missing_values_and_empty_weeks_are_not_volume():
    weekly = pd.DataFrame({'player': ['A', 'A'], 'gwidx': [0, 1], 'volume': [10.0, 0.0], 'value': [1.0, 5.0]})
    t = s6.Trailing(weekly, 3)
    assert t.league_as_of(2) == pytest.approx(1.0)
    weekly2 = pd.DataFrame({'player': ['A', 'A'], 'gwidx': [0, 1], 'volume': [10.0, 10.0], 'value': [1.0, np.nan]})
    assert s6.Trailing(weekly2, 3).league_as_of(2) == pytest.approx(1.0)


def test_qb_games_keeps_only_games_with_enough_dropbacks():
    df = pd.DataFrame({'season': 2017, 'week': 1, 'gwidx': 0,
                       'passer_player_id': ['A'] * 15 + ['B'] * 14, 'qb_epa': [1.0] * 15 + [2.0] * 14})
    g = s6.qb_games(df)
    assert list(g['player']) == ['A'] and int(g['dropbacks'].iloc[0]) == 15 and g['target'].iloc[0] == 1.0


def test_wls_recovers_known_coefficients_and_uses_the_weights():
    rng = np.random.default_rng(4)
    X = rng.normal(size=(400, 2))
    y = 0.5 + 2.0 * X[:, 0] - 1.0 * X[:, 1]
    b = s6.wls(X, y, np.ones(400))
    assert b == pytest.approx([0.5, 2.0, -1.0], abs=1e-9)
    # Three points no line fits: two heavy ones on y = x and a light outlier.
    # Weighted, the fit follows the heavy pair; unweighted, the outlier drags
    # the slope far off. (A first version used two groups, which any line
    # fits exactly whatever the weights, and a mutation dropping the weights
    # survived it.)
    X2 = np.array([[0.0], [1.0], [2.0]])
    y2 = np.array([0.0, 1.0, 10.0])
    weighted = s6.wls(X2, y2, np.array([1e6, 1e6, 1.0]))
    assert weighted == pytest.approx([0.0, 1.0], abs=1e-3)
    assert s6.wls(X2, y2, np.ones(3))[1] > 4


def test_the_cluster_bootstrap_points_the_right_way():
    rng = np.random.default_rng(5)
    y = rng.normal(size=300)
    good, bad = y + rng.normal(0, 0.1, 300), y + rng.normal(0, 1.0, 300)
    w = np.ones(300)
    clusters = np.repeat(np.arange(60), 5)
    bs = s6.cluster_bootstrap_mse_diff(y, good, bad, w, clusters, 2000, 1)
    assert bs.max() < 0
    assert np.all(s6.cluster_bootstrap_mse_diff(y, good, good, w, clusters, 200, 1) == 0)
    full = s6.weighted_mse(y, good, w) - s6.weighted_mse(y, bad, w)
    assert np.median(bs) == pytest.approx(full, rel=0.1)


@pytest.mark.parametrize('diff, ci, label', [
    (-0.01, [-0.02, -0.001], 'PASS'), (-0.01, [-0.02, 0.001], 'FAIL'),
    (0.01, [0.001, 0.02], 'FAIL'), (-0.01, [-0.02, 0.0], 'FAIL'),
])
def test_the_screen_rule_is_the_registered_one(diff, ci, label):
    assert s6.screen_label(diff, ci) == label


def test_weekly_ngs_reports_weeks_the_index_does_not_know():
    ngs = pd.DataFrame({'player_gsis_id': ['A', 'A', None], 'season': [2016, 2016, 2016], 'week': [1, 19, 1],
                        'attempts': [30, 20, 10], 'aggressiveness': [15.0, 20.0, 9.0]})
    w2i = {(2016, 1): 0}
    out = s6.weekly_ngs(ngs, 'aggressiveness', w2i)
    assert list(out['gwidx']) == [0] and list(out['volume']) == [30.0]
    assert s6.unmatched_ngs_weeks(ngs, w2i) == [(2016, 19)]


def test_load_ngs_drops_season_totals_and_the_postseason(monkeypatch):
    import nflreadpy
    import polars as pl
    cols = {c: [1.0, 2.0, 3.0] for c in s6.NGS_COLUMNS}
    frame = pl.DataFrame({'season': [2016] * 3, 'week': [0, 1, 19], 'season_type': ['REG', 'REG', 'POST'],
                          'player_gsis_id': ['A'] * 3, 'attempts': [500, 30, 40], **cols})
    monkeypatch.setattr(nflreadpy, 'load_nextgen_stats', lambda seasons, stat_type: frame)
    out = s6.load_ngs([2016])
    assert list(out['week']) == [1]


def test_load_ngs_refuses_a_file_without_a_registered_column(monkeypatch):
    import nflreadpy
    import polars as pl
    frame = pl.DataFrame({'season': [2016], 'week': [1], 'season_type': ['REG'], 'player_gsis_id': ['A'],
                          'attempts': [30], 'aggressiveness': [1.0]})
    monkeypatch.setattr(nflreadpy, 'load_nextgen_stats', lambda seasons, stat_type: frame)
    with pytest.raises(SystemExit, match='completion_percentage_above_expectation'):
        s6.load_ngs([2016])


def test_the_matchup_feature_is_home_minus_away():
    games = pd.DataFrame({'game_id': ['g1', 'g2']})
    starters = pd.DataFrame({'game_id': ['g1', 'g1', 'g2', 'g2'], 'side': ['home', 'away', 'home', 'away'],
                             'x': [3.0, 1.0, 0.0, np.nan]})
    out = s6r.add_matchup(games, starters, {'intercept': 0.5, 'x': 2.0}, ['x'], 'm')
    assert out.loc[0, 'm'] == pytest.approx(4.0)
    assert np.isnan(out.loc[1, 'm']), "a starter with no inputs must leave the game out, not score it as zero"


def test_the_feature_sets_nest():
    assert s6.FEATURES['base'] == ['trailing_epa']
    assert s6.FEATURES['control'][:1] == s6.FEATURES['base']
    assert s6.FEATURES['candidate'][:2] == s6.FEATURES['control']
    assert len(s6.FEATURES['candidate']) == 2 + 4


def test_a_question_whose_precondition_failed_is_refused():
    entry = {'id': 'N3', 'requires': {'N2': 'ACCEPT'}}
    assert s6r.unmet_precondition(entry, {'N2': {'decision': 'ACCEPT'}}) is None
    assert 'INCONCLUSIVE' in s6r.unmet_precondition(entry, {'N2': {'decision': 'INCONCLUSIVE'}})
    assert 'None' in s6r.unmet_precondition(entry, {})


def test_the_fit_seasons_end_before_validation_and_the_loader_before_the_holdout():
    reg = s6r.registry()['protocol']
    assert max(s6r.FIT_SEASONS) < min(reg['validation_seasons'])
    assert s6r.LAST_SEASON < reg['forward_holdout_season']
