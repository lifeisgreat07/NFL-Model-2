"""The day sports' Model A points the right way (Stage 94 item 26, audit 7 T1).

A team that wins every game it plays must come out with a positive matchup
when it is at home and a negative one away, and a home probability above 0.5
at home and below it away. The suite checked that the ridge orders teams
(`test_the_ridge_ranks_the_strong_team_first...`) but nothing checked the
sign of the matchup a pick is made from, so a matchup taken away-minus-home
would have shipped every pick backwards with every test green.

The NHL league is `tests/test_nhl_model.py`'s, with SEA (its weakest team)
made to win every game it plays by three goals and eight shots; the NBA's is
`tests/test_nba_model.py`'s, with T00 (its weakest) winning every game by
fifteen. Taking the weakest team means a sign error cannot hide behind the
team's original strength.

Run with: pytest tests/test_direction.py -v
"""
from src.sports.nba import backtest as nba_backtest
from src.sports.nba import ratings as nba_ratings
from src.sports.nhl import backtest as nhl_backtest
from src.sports.nhl import ratings as nhl_ratings
from tests import test_nba_model as nba_m
from tests import test_nhl_model as nhl_m


def sides(table, team, p):
    home = table[table['home'] == team]
    away = table[table['away'] == team]
    return home, away, p.reindex(home['game_id']), p.reindex(away['game_id'])


def test_an_nhl_team_that_wins_every_game_is_favoured_at_home_and_away():
    raw = nhl_m.synthetic(days=120)
    for side, other in (('home', 'away'), ('away', 'home')):
        mine = raw[side] == 'SEA'
        raw.loc[mine, f'{side}_score'] = raw.loc[mine, f'{other}_score'] + 3
        raw.loc[mine, f'{side}_sog'] = raw.loc[mine, f'{other}_sog'] + 8
    raw['last_period'] = 'REG'
    g = nhl_ratings.prepare(raw)
    t = nhl_ratings.features(g, 60, [500])
    t.loc[t.index >= len(t) // 2, 'season'] = 2022
    p = nhl_backtest.walk_forward(t, nhl_m.COLS, [2022])
    late = t[t['season'] == 2022]
    home, away, p_home, p_away = sides(late, 'SEA', p)
    assert len(home) and len(away)
    assert (home['goal_matchup'] > 0).all() and (away['goal_matchup'] < 0).all()
    assert (p_home > 0.5).all() and (p_away < 0.5).all()


def test_an_nba_team_that_wins_every_game_is_favoured_at_home_and_away():
    games, minutes = nba_m.synthetic(seasons=(2020, 2021), days=60)
    raw = games[['game_id', 'slate', 'season', 'game_type', 'home', 'away', 'home_score', 'away_score',
                 'possessions', 'home_prob']].copy()
    for side, other in (('home', 'away'), ('away', 'home')):
        mine = raw[side] == 'T00'
        raw.loc[mine, f'{side}_score'] = raw.loc[mine, f'{other}_score'] + 15
    games = nba_ratings.prepare(raw)
    table = nba_backtest._table(games, minutes, 60.0, 1.0)
    p = nba_backtest.walk_forward(table, list(nba_backtest.A_COLUMNS), [2021])
    late = table[table['season'] == 2021]
    home, away, p_home, p_away = sides(late, 'T00', p)
    assert len(home) and len(away)
    assert (home['point_matchup'] > 0).all() and (away['point_matchup'] < 0).all()
    assert (p_home > 0.5).all() and (p_away < 0.5).all()
