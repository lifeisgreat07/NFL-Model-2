"""
Stage 6's referee screen (R1), checked over synthetic inputs.

The registry words R1 exactly: penalty yards against the away team minus
those against the home team, per game; a referee's mean over 2016-2020 and
over 2021-2023, with at least 40 and 24 games; the two correlated across
referees, weighted by the smaller count; PASS only if the 95% interval's
lower end is above zero. Each test below holds one of those words.

Run with: pytest tests/test_stage6_referee.py -v
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).parent.parent

from src.sports.nfl.research import stage6_referee as rf
from src.sports.nfl.research import stage6_run as s6r


def sched_rows(rows):
    return pd.DataFrame([{'game_type': 'REG', **r} for r in rows])


def one_game(**kw):
    base = {'game_id': 'g1', 'season': 2018, 'home_team': 'HOM', 'away_team': 'AWY', 'referee': 'Ref One'}
    return sched_rows([{**base, **kw}])


# ------------------------------------------------------------- the games

def test_only_regular_season_games_that_name_a_referee_count():
    s = sched_rows([
        {'game_id': 'a', 'season': 2018, 'home_team': 'H', 'away_team': 'A', 'referee': 'Ref One'},
        {'game_id': 'b', 'season': 2018, 'home_team': 'H', 'away_team': 'A', 'referee': None},
        {'game_id': 'c', 'season': 2018, 'home_team': 'H', 'away_team': 'A', 'referee': '  '},
        {'game_id': 'd', 'season': 2018, 'home_team': 'H', 'away_team': 'A', 'referee': 'Ref One',
         'game_type': 'WC'},
    ])
    assert list(rf.named_referee_games(s)['game_id']) == ['a']


def test_the_screen_reads_no_season_after_2023():
    assert rf.R1_SEASONS[0] == 2016 and rf.R1_SEASONS[-1] == 2023
    assert rf.EARLY == (2016, 2020) and rf.LATE == (2021, 2023)
    s = sched_rows([
        {'game_id': 'a', 'season': 2023, 'home_team': 'H', 'away_team': 'A', 'referee': 'R'},
        {'game_id': 'b', 'season': 2024, 'home_team': 'H', 'away_team': 'A', 'referee': 'R'},
    ])
    assert list(rf.named_referee_games(s)['game_id']) == ['a']


def test_a_referees_name_is_one_name_however_it_is_spaced():
    s = sched_rows([
        {'game_id': 'a', 'season': 2018, 'home_team': 'H', 'away_team': 'A', 'referee': 'Walt Anderson'},
        {'game_id': 'b', 'season': 2019, 'home_team': 'H', 'away_team': 'A', 'referee': ' Walt  Anderson '},
    ])
    assert set(rf.named_referee_games(s)['referee']) == {'Walt Anderson'}


# ------------------------------------------------------ the differential

def test_the_differential_is_away_minus_home():
    pbp = pd.DataFrame([
        {'game_id': 'g1', 'home_team': 'HOM', 'away_team': 'AWY', 'penalty': 1, 'penalty_team': 'AWY', 'penalty_yards': 15},
        {'game_id': 'g1', 'home_team': 'HOM', 'away_team': 'AWY', 'penalty': 1, 'penalty_team': 'HOM', 'penalty_yards': 5},
        {'game_id': 'g1', 'home_team': 'HOM', 'away_team': 'AWY', 'penalty': 1, 'penalty_team': 'AWY', 'penalty_yards': 10},
    ])
    games, _ = rf.penalty_differential(pbp, rf.named_referee_games(one_game()))
    assert games['differential'].tolist() == [20.0]


def test_rows_that_are_not_penalties_or_name_neither_team_do_not_count():
    pbp = pd.DataFrame([
        {'game_id': 'g1', 'home_team': 'HOM', 'away_team': 'AWY', 'penalty': 0, 'penalty_team': 'AWY', 'penalty_yards': 15},
        {'game_id': 'g1', 'home_team': 'HOM', 'away_team': 'AWY', 'penalty': 1, 'penalty_team': None, 'penalty_yards': 5},
        {'game_id': 'g1', 'home_team': 'HOM', 'away_team': 'AWY', 'penalty': 1, 'penalty_team': 'HOM', 'penalty_yards': 5},
    ])
    games, counts = rf.penalty_differential(pbp, rf.named_referee_games(one_game()))
    assert games['differential'].tolist() == [-5.0]
    assert counts['penalty_rows_on_neither_team'] == 1


def test_a_game_without_play_by_play_is_dropped_not_scored_zero():
    s = rf.named_referee_games(sched_rows([
        {'game_id': 'g1', 'season': 2018, 'home_team': 'H', 'away_team': 'A', 'referee': 'R'},
        {'game_id': 'g2', 'season': 2018, 'home_team': 'H', 'away_team': 'A', 'referee': 'R'},
    ]))
    pbp = pd.DataFrame([{'game_id': 'g1', 'home_team': 'H', 'away_team': 'A', 'penalty': 0,
                         'penalty_team': None, 'penalty_yards': None}])
    games, counts = rf.penalty_differential(pbp, s)
    assert games['game_id'].tolist() == ['g1']
    assert games['differential'].tolist() == [0.0]   # loaded, no penalties: a real zero
    assert counts['games_without_play_by_play'] == 1


def test_a_relocated_team_is_matched_in_play_by_plays_own_spelling():
    # the schedule calls the 2018 Raiders OAK; play-by-play, and so penalty_team, calls them LV
    s = rf.named_referee_games(one_game(home_team='OAK', away_team='DEN'))
    pbp = pd.DataFrame([
        {'game_id': 'g1', 'home_team': 'LV', 'away_team': 'DEN', 'penalty': 1,
         'penalty_team': 'LV', 'penalty_yards': 15},
        {'game_id': 'g1', 'home_team': 'LV', 'away_team': 'DEN', 'penalty': 1,
         'penalty_team': 'DEN', 'penalty_yards': 5},
    ])
    games, counts = rf.penalty_differential(pbp, s)
    assert games['differential'].tolist() == [-10.0]
    assert counts['penalty_rows_on_neither_team'] == 0


# ------------------------------------------------------------ the windows

def ref_games(ref, early, late, early_value=0.0, late_value=0.0):
    rows = [{'referee': ref, 'season': 2016 + i % 5, 'differential': early_value} for i in range(early)]
    rows += [{'referee': ref, 'season': 2021 + i % 3, 'differential': late_value} for i in range(late)]
    return rows


@pytest.mark.parametrize('early, late, counts', [
    (40, 24, True), (39, 24, False), (40, 23, False),
])
def test_a_referee_needs_forty_early_and_twenty_four_late_games(early, late, counts):
    t = rf.window_means(pd.DataFrame(ref_games('R', early, late)))
    assert ('R' in t.index) is counts


def test_each_referee_is_weighted_by_his_smaller_count():
    t = rf.window_means(pd.DataFrame(ref_games('R', 50, 30) + ref_games('S', 41, 60)))
    assert t.loc['R', 'weight'] == 30 and t.loc['S', 'weight'] == 41


def test_the_windows_are_means_of_their_own_seasons():
    t = rf.window_means(pd.DataFrame(ref_games('R', 40, 24, early_value=3.0, late_value=-1.0)))
    assert t.loc['R', 'mean_early'] == 3.0 and t.loc['R', 'mean_late'] == -1.0


# ------------------------------------------------------------ correlation

def test_equal_weights_give_pearsons_r():
    rng = np.random.default_rng(1)
    x, y = rng.normal(size=20), rng.normal(size=20)
    assert rf.weighted_corr(x, y, np.ones(20)) == pytest.approx(np.corrcoef(x, y)[0, 1])


def test_the_weights_matter():
    x = np.array([0.0, 1.0, 2.0, 3.0])
    y = np.array([0.0, 1.0, 2.0, -9.0])
    light = rf.weighted_corr(x, y, [10, 10, 10, 1])
    heavy = rf.weighted_corr(x, y, [1, 1, 1, 10])
    assert light > heavy


def test_no_spread_is_undefined_not_zero():
    assert np.isnan(rf.weighted_corr([1.0, 1.0], [0.0, 2.0], [1, 1]))


def test_the_bootstrap_resamples_referees_and_repeats_with_its_seed():
    x = np.arange(8.0)
    y = x + np.random.default_rng(2).normal(scale=0.5, size=8)
    w = np.full(8, 30.0)
    a = rf.bootstrap_corr(x, y, w, 500, 7)
    b = rf.bootstrap_corr(x, y, w, 500, 7)
    assert np.array_equal(a, b, equal_nan=True)
    assert np.nanmedian(a) > 0.5


@pytest.mark.parametrize('ci, label', [
    ([0.01, 0.9], 'PASS'), ([0.0, 0.9], 'FAIL'), ([-0.2, 0.5], 'FAIL'),
])
def test_the_rule_is_the_registered_one(ci, label):
    assert rf.r1_label(ci) == label


# --------------------------------------------------------------- the run

def synthetic_inputs(persistent):
    rng = np.random.default_rng(3)
    sched, pbp = [], []
    edges = {f'Ref {k}': rng.normal(scale=8.0) for k in range(8)}
    n = 0
    for season in rf.R1_SEASONS:
        for ref, edge in edges.items():
            late = season >= rf.LATE[0]
            e = edge if (persistent or not late) else -edge
            for _ in range(10):
                n += 1
                gid = f'g{n}'
                sched.append({'game_id': gid, 'game_type': 'REG', 'season': season,
                              'home_team': 'HOM', 'away_team': 'AWY', 'referee': ref})
                pbp.append({'game_id': gid, 'season': season, 'season_type': 'REG', 'home_team': 'HOM', 'away_team': 'AWY', 'penalty': 1,
                            'penalty_team': 'AWY', 'penalty_yards': 30 + e + rng.normal(scale=3.0)})
                pbp.append({'game_id': gid, 'season': season, 'season_type': 'REG', 'home_team': 'HOM', 'away_team': 'AWY', 'penalty': 1,
                            'penalty_team': 'HOM', 'penalty_yards': 30.0})
    return pd.DataFrame(sched), pd.DataFrame(pbp)


@pytest.mark.parametrize('persistent, decision', [(True, 'PASS'), (False, 'FAIL')])
def test_run_r1_loads_only_2016_to_2023_and_scores_by_the_rule(monkeypatch, tmp_path, persistent, decision):
    sched, pbp = synthetic_inputs(persistent)
    asked = []
    monkeypatch.setattr(s6r.sd, 'load_schedule', lambda s: (asked.append(s), sched[sched['season'] == s])[1])

    def load_pbp(seasons, columns):
        asked.extend(seasons)
        assert set(columns) >= {'home_team', 'away_team', 'penalty', 'penalty_team', 'penalty_yards'}
        return pbp[pbp['season'].isin(seasons)]
    monkeypatch.setattr(s6r.s6, 'load_pbp', load_pbp)
    monkeypatch.setattr(s6r, 'RESULTS_DIR', tmp_path)
    monkeypatch.setattr(s6r, 'CACHE', tmp_path / 'no-build-needed')
    out = s6r.run('R1')
    assert max(asked) == 2023 and min(asked) == 2016
    assert out['decision'] == decision
    assert out['persistence']['n_referees'] == 8
    assert out['reached_confirmation'] is False
    assert 'build' not in out and 'ngs_column_map' not in out
    stored = json.loads((tmp_path / 'R1.json').read_text(encoding='utf-8'))
    assert stored['decision'] == rf.r1_label(stored['persistence']['corr_ci_95'])
