"""MLB's standings odds (Stage 100 item 3, src/sports/mlb/standings.py): the
divisions, the tie rules, the field of six per league, and the simulation's
shares. The real seasons 2022 to 2026 are seeded from the committed history and
held against the postseason MLB actually played.

Run with: pytest tests/test_mlb_standings.py -v
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.sports.mlb import standings, teams

HISTORY = Path(__file__).resolve().parents[1] / 'data' / 'mlb' / 'history'
CLUBS = sorted(teams.NAMES)
IDX = {t: i for i, t in enumerate(CLUBS)}
NYY, TOR, BAL, BOS, TB, CLE, HOU = '147', '141', '110', '111', '139', '114', '117'


def record(wins):
    """A Record from {(winner, loser): games won}."""
    h2h = np.zeros((len(CLUBS), len(CLUBS)))
    for (w, lo), k in wins.items():
        h2h[IDX[w], IDX[lo]] += k
    return standings.Record(h2h, IDX)


LOTS = {t: 0.5 for t in CLUBS}


def test_the_divisions_are_the_thirty_stats_api_clubs_five_to_a_division():
    assert sorted(standings.TEAM_DIVISION) == CLUBS
    assert all(len(c) == 5 for c in standings.DIVISIONS.values())
    assert {lg: len(c) for lg, c in standings.LEAGUE_CLUBS.items()} == {'AL': 15, 'NL': 15}


def test_two_clubs_level_go_by_head_to_head_then_division_then_league_then_lots():
    # Head to head: the Yankees won 7 of 13.
    rec = record({(NYY, TOR): 7, (TOR, NYY): 6})
    assert standings.best([TOR, NYY], rec, LOTS) == NYY
    # Level head to head, so each club's record in its division: the Blue Jays' is better, though the Yankees'
    # record in the league (Cleveland's six games with them) is better still.
    games = {(NYY, TOR): 6, (TOR, NYY): 6, (NYY, BAL): 5, (BAL, NYY): 8, (TOR, BAL): 7, (BAL, TOR): 6, (NYY, CLE): 6}
    assert record(games).league_pct(NYY) > record(games).league_pct(TOR)
    assert standings.best([NYY, TOR], record(games), LOTS) == TOR
    # Level in the division too, so the record in the league: the Yankees beat Cleveland more often.
    games.update({(TOR, BAL): 5, (BAL, TOR): 8, (NYY, CLE): 4, (CLE, NYY): 2, (TOR, CLE): 3, (CLE, TOR): 3})
    assert standings.best([NYY, TOR], record(games), LOTS) == NYY
    # Level everywhere: the draw.
    games.update({(NYY, CLE): 3, (CLE, NYY): 3})
    assert standings.best([NYY, TOR], record(games), {**LOTS, TOR: 0.9}) == TOR
    assert standings.best([NYY, TOR], record(games), {**LOTS, NYY: 0.9}) == NYY


def test_three_clubs_level_a_club_better_than_each_of_the_others_goes_first():
    # Boston beat both, narrowly; Tampa Bay has the best record among the three combined (it crushed New York).
    rec = record({(BOS, NYY): 7, (NYY, BOS): 6, (BOS, TB): 7, (TB, BOS): 6, (TB, NYY): 12, (NYY, TB): 1})
    assert standings.best([NYY, TB, BOS], rec, LOTS) == BOS


def test_three_clubs_level_go_by_games_among_them_and_two_left_level_go_back_to_head_to_head():
    # Nobody beat both others. Among the three, New York and Toronto are 14-12 and Baltimore 11-15.
    games = {(NYY, TOR): 5, (TOR, NYY): 8, (NYY, BAL): 9, (BAL, NYY): 4, (TOR, BAL): 6, (BAL, TOR): 7}
    rec = record(games)
    assert standings.best([NYY, TOR, BAL], rec, LOTS) == TOR
    # New York's record in the division and the league is better than Toronto's: a three-club step would pick it,
    # but once two are left level the two-club rules start again, and Toronto won the season series.
    games.update({(NYY, BOS): 10, (BOS, NYY): 3, (TOR, BOS): 3, (BOS, TOR): 10})
    assert standings.best([NYY, TOR, BAL], record(games), LOTS) == TOR


def test_a_tie_for_more_than_one_place_is_settled_one_place_at_a_time():
    games = {(NYY, TOR): 5, (TOR, NYY): 8, (NYY, BAL): 9, (BAL, NYY): 4, (TOR, BAL): 6, (BAL, TOR): 7}
    # Cleveland's games make all three 14-15: Toronto first (as above), then New York over Baltimore head to head.
    games.update({(CLE, NYY): 3, (CLE, TOR): 3, (BAL, CLE): 3})
    rec = record(games)
    assert rec.pct(NYY) == rec.pct(TOR) == rec.pct(BAL)
    assert standings.ordered([BAL, NYY, TOR], rec, LOTS) == [TOR, NYY, BAL]


def history(season):
    return pd.read_csv(HISTORY / f'games_{season}.csv', dtype={'home': str, 'away': str})


def real_postseason(games):
    """(the wild card series as {pair: hosts}, the clubs with a bye, the division series games)."""
    wc = games[games['game_type'] == 'wild_card']
    ds = games[games['game_type'] == 'division']
    hosts = {}
    for h, a in zip(wc['home'], wc['away']):
        hosts.setdefault(frozenset((h, a)), set()).add(h)
    byes = set(ds['home']) | set(ds['away'])
    return hosts, byes - set(wc['home']) - set(wc['away']), ds


@pytest.mark.parametrize('season', [2022, 2023, 2024, 2025, 2026])
def test_each_finished_twelve_club_season_seeds_as_mlb_did(season):
    """Seeds 3 and 4 host the wild card series against 6 and 5, all three games at home; 1 and 2 have the byes,
    and seed 1 meets the winner of 4 v 5. Several draws of lots, so a seeding that leans on the draw shows."""
    games = history(season)
    reg = games[games['game_type'] == 'regular']
    rec = standings.Record(standings.results(reg, IDX), IDX)
    hosts, byes, ds = real_postseason(games)
    for draw in range(5):
        rng = np.random.default_rng(draw)
        lots = {t: float(rng.random()) for t in CLUBS}
        for league in standings.LEAGUES:
            s1, s2, s3, s4, s5, s6 = standings.seeds(league, rec, lots)
            assert hosts[frozenset((s3, s6))] == {s3} and hosts[frozenset((s4, s5))] == {s4}
            assert {s1, s2} == byes & set(standings.LEAGUE_CLUBS[league])
            met = set(ds.loc[(ds['home'] == s1) | (ds['away'] == s1), ['home', 'away']].to_numpy().ravel()) - {s1}
            assert met & {s4, s5}


def test_a_division_winner_is_seeded_above_a_wild_card_with_a_better_record():
    # 2025: Cleveland won the AL Central at 88-74 and is seed 3; the Yankees, 94-68, are seed 4.
    games = history(2025)
    reg = games[games['game_type'] == 'regular']
    rec = standings.Record(standings.results(reg, IDX), IDX)
    top = standings.seeds('AL', rec, LOTS)
    assert top[2] == CLE and top[3] == NYY and rec.pct(NYY) > rec.pct(CLE)


def league(final_share=0.5):
    """Every pair in a league plays once at home and once away; the first `final_share` of games are final, the
    home side winning when its id sorts first."""
    rows = [{'game_id': f'{h}-{a}', 'home': h, 'away': a, 'game_type': 'regular'}
            for clubs in standings.LEAGUE_CLUBS.values() for h in clubs for a in clubs if h != a]
    sched = pd.DataFrame(rows)
    done = int(len(sched) * final_share)
    sched['status'] = ['final'] * done + ['scheduled'] * (len(sched) - done)
    sched['home_score'] = [5.0 if h < a else 3.0 for h, a in zip(sched['home'], sched['away'])]
    sched['away_score'] = [3.0 if h < a else 5.0 for h, a in zip(sched['home'], sched['away'])]
    sched.loc[sched['status'] != 'final', ['home_score', 'away_score']] = np.nan
    return sched


def test_each_league_fills_three_division_places_three_wild_cards_and_two_byes():
    sched = league()
    left = sched[sched['status'] != 'final']
    out = standings.simulate(sched, dict.fromkeys(left['game_id'], 0.5), n_sim=200)
    assert len(out) == 30
    for lg in ('AL', 'NL'):
        rows = out[out['league'] == lg]
        assert rows['division_pct'].sum() == pytest.approx(3) and rows['wildcard_pct'].sum() == pytest.approx(3)
        assert rows['bye_pct'].sum() == pytest.approx(2) and rows['playoff_pct'].sum() == pytest.approx(6)
    for div, clubs in standings.DIVISIONS.items():
        assert out[out['division'] == div]['division_pct'].sum() == pytest.approx(1)
    assert list(out['projected_wins']) == sorted(out['projected_wins'], reverse=True)


def test_a_club_that_wins_every_game_wins_its_division_with_a_bye():
    sched = league(final_share=1.0)
    out = standings.simulate(sched, {}, n_sim=20).set_index('team')
    first = min(standings.LEAGUE_CLUBS['AL'])  # sorts first in the AL: won every game
    assert out.loc[first, 'wins_now'] == 28 and out.loc[first, 'losses_now'] == 0
    assert out.loc[first, 'division_pct'] == 1.0 and out.loc[first, 'bye_pct'] == 1.0


def test_an_official_tie_counts_for_neither_club():
    sched = league(final_share=1.0)
    before = standings.simulate(sched, {}, n_sim=1).set_index('team')
    extra = pd.DataFrame([
        {'game_id': 'tie', 'home': NYY, 'away': TOR, 'game_type': 'regular', 'status': 'final',
         'home_score': 1.0, 'away_score': 1.0},
        {'game_id': 'won', 'home': NYY, 'away': TOR, 'game_type': 'regular', 'status': 'final',
         'home_score': 4.0, 'away_score': 2.0}])
    out = standings.simulate(pd.concat([sched, extra], ignore_index=True), {}, n_sim=1).set_index('team')
    for club, change in ((NYY, (1, 0)), (TOR, (0, 1))):
        got = (out.loc[club, 'wins_now'] - before.loc[club, 'wins_now'],
               out.loc[club, 'losses_now'] - before.loc[club, 'losses_now'])
        assert got == change


def test_an_unplayed_game_without_a_probability_stops_the_simulation():
    with pytest.raises(ValueError, match='have no probability'):
        standings.simulate(league(), {}, n_sim=1)


def test_a_club_in_no_division_stops_the_simulation():
    sched = league(final_share=1.0)
    sched.loc[0, 'home'] = '999'
    with pytest.raises(ValueError, match='clubs in no division'):
        standings.simulate(sched, {}, n_sim=1)


def test_a_schedule_missing_a_club_stops_the_simulation():
    sched = league(final_share=1.0)
    sched = sched[(sched['home'] != NYY) & (sched['away'] != NYY)]
    with pytest.raises(ValueError, match=f"no regular-season game listed: \\['{NYY}'\\]"):
        standings.simulate(sched, {}, n_sim=1)


def test_the_file_says_how_many_games_are_listed():
    sched = league(final_share=1.0)
    out = standings.simulate(sched, {}, n_sim=1)
    doc = standings.to_json(out, '2026-11-23', 1, standings.games_listed(sched))
    assert doc['games_listed'] == [28, 28] and doc['teams'][0].keys() == {
        'team', 'league', 'division', 'wins_now', 'losses_now', 'projected_wins', 'division_pct', 'bye_pct',
        'wildcard_pct', 'playoff_pct'}
