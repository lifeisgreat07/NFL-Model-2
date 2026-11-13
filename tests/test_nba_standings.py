"""The NBA's standings odds (Stage 104 item 4, src/sports/nba/standings.py):
the seeding and its ties, the play-in, and the simulation's shares.

Run with: pytest tests/test_nba_standings.py -v
"""
import numpy as np
import pandas as pd
import pytest

from src.sports.nba import standings


def h2h_of(table):
    return lambda a, b: table.get((a, b), 0.0)


def test_a_tie_is_broken_among_the_tied_then_by_conference_then_by_lots():
    teams = ['A', 'B', 'C', 'D']
    wins = {'A': 50, 'B': 40, 'C': 40, 'D': 40}
    played = dict.fromkeys(teams, 82)
    # Among B, C and D: C won 3 of 4, B 2 of 4, D 1 of 4.
    h2h = h2h_of({('C', 'B'): 2, ('C', 'D'): 1, ('B', 'D'): 2, ('D', 'C'): 1})
    conf = dict.fromkeys(teams, 30)
    lots = {'A': 0.1, 'B': 0.2, 'C': 0.3, 'D': 0.4}
    assert standings.seed(teams, wins, played, h2h, conf, dict.fromkeys(teams, 52), lots) == ['A', 'C', 'B', 'D']
    # Level among themselves, so conference record decides; level there too, so the draw.
    flat = h2h_of({})
    conf2 = {'A': 30, 'B': 28, 'C': 31, 'D': 28}
    assert standings.seed(teams, wins, played, flat, conf2, dict.fromkeys(teams, 52), lots) == ['A', 'C', 'D', 'B']


def test_the_play_in_seats_the_winner_of_seven_and_eight_then_the_best_of_the_rest():
    seeds = ['1', '2', '3', '4', '5', '6', 'S7', 'S8', 'S9', 'S10']
    rng = np.random.default_rng(0)
    # 7 beats 8; 10 beats 9; 8 beats 10 in the last game.
    prob = {('S7', 'S8'): 1.0, ('S9', 'S10'): 0.0, ('S8', 'S10'): 1.0}
    assert standings.play_in(seeds, prob, rng) == ('S7', 'S8')
    # 8 beats 7, 9 beats 10, and 9 beats 7 away from home.
    prob = {('S7', 'S8'): 0.0, ('S9', 'S10'): 1.0, ('S7', 'S9'): 0.0}
    assert standings.play_in(seeds, prob, rng) == ('S8', 'S9')


def league(final_share=0.5):
    """Every pair in a conference plays once at home and once away; the first
    `final_share` of games are final, the home side winning when its code is
    earlier in the alphabet."""
    rows = []
    for clubs in standings.CONFERENCES.values():
        for h in clubs:
            for a in clubs:
                if h != a:
                    rows.append({'game_id': f'{h}-{a}', 'home': h, 'away': a, 'game_type': 'regular'})
    sched = pd.DataFrame(rows)
    done = int(len(sched) * final_share)
    sched['status'] = ['final'] * done + ['scheduled'] * (len(sched) - done)
    sched['home_score'] = [100.0 if h < a else 90.0 for h, a in zip(sched['home'], sched['away'])]
    sched['away_score'] = [90.0 if h < a else 100.0 for h, a in zip(sched['home'], sched['away'])]
    sched.loc[sched['status'] != 'final', ['home_score', 'away_score']] = np.nan
    return sched


def test_each_conference_fills_six_places_four_play_in_places_and_eight_playoff_places():
    sched = league()
    left = sched[sched['status'] != 'final']
    clubs = sorted(set(sched['home']))
    out = standings.simulate(sched, dict.fromkeys(left['game_id'], 0.5),
                             {(a, b): 0.5 for a in clubs for b in clubs if a != b}, n_sim=200)
    assert len(out) == 30
    for conf in ('East', 'West'):
        rows = out[out['conference'] == conf]
        assert rows['top6_pct'].sum() == pytest.approx(6) and rows['playin_pct'].sum() == pytest.approx(4)
        assert rows['playoff_pct'].sum() == pytest.approx(8)
    assert list(out['projected_wins']) == sorted(out['projected_wins'], reverse=True)


def test_a_club_that_wins_every_game_is_always_a_top_six_seed():
    sched = league(final_share=1.0)
    clubs = sorted(set(sched['home']))
    out = standings.simulate(sched, {}, {(a, b): 0.5 for a in clubs for b in clubs if a != b}, n_sim=50)
    best = out.set_index('team').loc['ATL']   # first in the East's alphabet: won every game
    assert best['wins_now'] == 28 and best['losses_now'] == 0 and best['top6_pct'] == 1.0


def test_an_unplayed_game_without_a_probability_stops_the_simulation():
    sched = league()
    with pytest.raises(ValueError, match='have no probability'):
        standings.simulate(sched, {}, {}, n_sim=1)


def test_the_file_says_how_many_games_are_listed():
    sched = league(final_share=1.0)
    clubs = sorted(set(sched['home']))
    out = standings.simulate(sched, {}, {(a, b): 0.5 for a in clubs for b in clubs if a != b}, n_sim=1)
    doc = standings.to_json(out, '2026-11-11', 1, standings.games_listed(sched))
    assert doc['games_listed'] == [28, 28] and doc['teams'][0].keys() == {
        'team', 'conference', 'wins_now', 'losses_now', 'projected_wins', 'top6_pct', 'playin_pct', 'playoff_pct'}


def test_the_page_data_carries_the_standings_file(monkeypatch):
    from src.sports.nba import site
    real = site._maybe
    fake = {'as_of': '2026-11-11', 'teams': []}
    monkeypatch.setattr(site, '_maybe', lambda p: fake if p.name == 'standings_2026.json' else real(p))
    assert site.board(2026)['standings'] is fake
