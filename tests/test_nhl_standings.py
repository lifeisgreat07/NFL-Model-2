"""The NHL's standings odds: the league's points and playoff rules, and a
simulation that keeps real results and draws only what is left.

Run with: pytest tests/test_nhl_standings.py -v
"""
import numpy as np
import pandas as pd
import pytest

from src.sports.nhl import standings as st

ALL = [t for teams in st.DIVISIONS.values() for t in teams]


def game(gid, home, away, status='final', home_win=1, period='REG', game_type='regular'):
    return {'game_id': gid, 'home': home, 'away': away, 'status': status,
            'home_win': home_win if status == 'final' else None,
            'last_period': period if status == 'final' else None, 'game_type': game_type}


def test_the_league_is_32_teams_in_four_divisions_of_eight():
    assert len(ALL) == len(set(ALL)) == 32
    assert all(len(t) == 8 for t in st.DIVISIONS.values())
    assert set(st.TEAM_CONFERENCE.values()) == {'Eastern', 'Western'}
    assert st.TEAM_DIVISION['UTA'] == 'Central' and st.TEAM_CONFERENCE['UTA'] == 'Western'


def test_a_win_is_two_points_and_a_loss_past_regulation_is_one():
    home, away = st._points(np.array([True, True, False]), np.array([0, 1, 2]))
    assert home.tolist() == [2, 2, 1] and away.tolist() == [0, 1, 2]


def test_overtime_share_counts_games_past_regulation_and_shootouts_among_them():
    g = pd.DataFrame({'last_period': ['REG', 'REG', 'OT', 'SO', None]})
    assert st.overtime_share(g) == (0.5, 0.5)


def test_three_per_division_and_two_wild_cards_per_conference():
    rng = np.random.default_rng(1)
    points = {t: 100 - i for i, t in enumerate(ALL)}
    zero = dict.fromkeys(ALL, 0)
    made, winners = st.playoff_teams(points, zero, zero, rng)
    assert len(made) == 16 and len(winners) == 4
    for divs in st.CONFERENCES.values():
        conf = [t for d in divs for t in st.DIVISIONS[d]]
        assert len([t for t in made if t in conf]) == 8
        for d in divs:
            assert set(st.DIVISIONS[d][:3]) <= made, 'the top three of each division'
    # The Atlantic's 4th and 5th (FLA, MTL) have more points than anyone in
    # the Metropolitan outside its top three, so they are the wild cards.
    assert {'FLA', 'MTL'} <= made and 'OTT' not in made and 'NYI' not in made


def test_regulation_wins_break_a_tie_in_points():
    rng = np.random.default_rng(1)
    points = dict.fromkeys(ALL, 80)
    rw = dict.fromkeys(ALL, 30)
    rw['TOR'] = 40
    made, winners = st.playoff_teams(points, rw, dict.fromkeys(ALL, 0), rng)
    assert 'TOR' in winners


def test_a_finished_game_keeps_its_result_and_an_overtime_loser_keeps_a_point():
    sched = pd.DataFrame([game('1', 'TOR', 'MTL', home_win=0, period='OT'),
                          game('2', 'BOS', 'BUF', home_win=1, period='REG')])
    out = st.simulate(sched, {}, (0.2, 0.3), n_sim=5).set_index('team')
    assert out.loc['MTL', 'points_now'] == 2 and out.loc['TOR', 'points_now'] == 1
    assert out.loc['BUF', 'points_now'] == 0
    assert out.loc['TOR', 'projected_points'] == 1, 'nothing left to draw'


def test_an_unplayed_game_is_drawn_from_its_probability():
    sched = pd.DataFrame([game(str(i), 'TOR', 'MTL', status='scheduled') for i in range(40)])
    sure = st.simulate(sched, {str(i): 1.0 for i in range(40)}, (0.0, 0.0), n_sim=20).set_index('team')
    assert sure.loc['TOR', 'projected_points'] == 80 and sure.loc['MTL', 'projected_points'] == 0
    coin = st.simulate(sched, {str(i): 0.5 for i in range(40)}, (1.0, 0.0), n_sim=200).set_index('team')
    assert coin.loc['TOR', 'projected_points'] + coin.loc['MTL', 'projected_points'] == pytest.approx(120)


def test_a_cancelled_or_playoff_game_counts_for_nobody():
    sched = pd.DataFrame([game('1', 'TOR', 'MTL', status='cancelled'),
                          game('2', 'TOR', 'MTL', game_type='playoff')])
    out = st.simulate(sched, {}, (0.2, 0.3), n_sim=5)
    assert out['points_now'].sum() == 0 and out['projected_points'].sum() == 0


def test_an_unplayed_game_without_a_probability_stops_the_simulation():
    sched = pd.DataFrame([game('1', 'TOR', 'MTL', status='scheduled')])
    with pytest.raises(ValueError, match='no probability'):
        st.simulate(sched, {}, (0.2, 0.3), n_sim=5)


def test_a_team_in_no_division_stops_the_simulation():
    sched = pd.DataFrame([game('1', 'TOR', 'ARI')])
    with pytest.raises(ValueError, match='in no division'):
        st.simulate(sched, {}, (0.2, 0.3), n_sim=5)


def test_the_simulation_is_seeded():
    sched = pd.DataFrame([game(str(i), ALL[i % 32], ALL[(i + 5) % 32], status='scheduled') for i in range(64)])
    probs = {str(i): 0.55 for i in range(64)}
    a = st.simulate(sched, probs, (0.23, 0.35), n_sim=50)
    b = st.simulate(sched, probs, (0.23, 0.35), n_sim=50)
    pd.testing.assert_frame_equal(a, b)
    assert a['playoff_pct'].sum() == pytest.approx(16) and a['division_pct'].sum() == pytest.approx(4)


class _Model:
    """A stand-in classifier: the probability is the first feature, clipped."""

    def predict_proba(self, x):
        p = np.clip(x.iloc[:, 0].to_numpy(dtype=float), 0, 1)
        return np.column_stack([1 - p, p])


def test_only_unplayed_regular_season_games_get_a_probability():
    sched = pd.DataFrame([game('1', 'TOR', 'MTL'), game('2', 'TOR', 'MTL', status='scheduled'),
                          game('3', 'TOR', 'MTL', status='cancelled'),
                          game('4', 'BOS', 'BUF', status='scheduled', game_type='playoff'),
                          game('5', 'BOS', 'BUF', status='postponed')])
    probs = st.unplayed_probabilities(sched, lambda h, a: {'f': 0.7 if h == 'TOR' else 0.4}, _Model(), ['f'])
    assert probs == {'2': pytest.approx(0.7), '5': pytest.approx(0.4)}


def test_the_file_carries_its_date_and_every_team():
    sched = pd.DataFrame([game('1', 'TOR', 'MTL', home_win=0, period='SO')])
    table = st.simulate(sched, {}, (0.22, 0.4), n_sim=5)
    doc = st.to_json(table, '2026-10-06', 5, (0.22, 0.4))
    assert doc['as_of'] == '2026-10-06' and doc['overtime_share'] == 0.22
    assert {t['team'] for t in doc['teams']} == {'TOR', 'MTL'}
    assert next(t for t in doc['teams'] if t['team'] == 'TOR')['points_now'] == 1
