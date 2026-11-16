"""Model A's ratings and curve (Stage 103 item 2), on seasons built by hand.

Run with: pytest tests/test_ncaam_ratings.py -v
"""
import numpy as np
import pandas as pd
import pytest

from src.sports.ncaam import ratings as r

CLUBS = list('ABCDEF')


def table(rows, season=2020):
    df = pd.DataFrame(rows, columns=['game_id', 'day', 'home', 'away', 'margin', 'neutral', 'tournament'])
    df['day'] = pd.to_datetime(df['day'])
    df['season'] = season
    df['margin'] = df['margin'].astype(float)
    df['home_win'] = (df['margin'] > 0).astype(int)
    return df.sort_values(['day', 'game_id'], kind='stable').reset_index(drop=True)


def a_season(first_four=7.0):
    """Ninety games from 1 December to 10 March among six clubs, a third of them neutral, then three tournament
    games: A v B (the First Four), A v C, C v D."""
    rng = np.random.default_rng(3)
    days = pd.date_range('2020-12-01', '2021-03-10')
    rows = []
    for i in range(90):
        h, a = rng.choice(len(CLUBS), size=2, replace=False)
        rows.append((f'g{i:02d}', str(days[i * len(days) // 90].date()), CLUBS[h], CLUBS[a],
                     float(rng.integers(1, 25) * rng.choice([-1, 1])), bool(i % 3 == 0), False))
    rows += [('t1', '2021-03-16', 'A', 'B', first_four, True, True), ('t2', '2021-03-18', 'A', 'C', 4.0, True, True),
             ('t3', '2021-03-20', 'C', 'D', -9.0, True, True)]
    return table(rows)


def fresh_ridge(games, day, h_days, lam):
    """The same regression from a fresh table: weights 0.5^(days ago / H), the edge unpenalised."""
    train = games[games['day'] < day]
    idx = {c: i + 1 for i, c in enumerate(sorted(set(games['home']) | set(games['away'])))}
    x = np.zeros((len(train), len(idx) + 1))
    x[:, 0] = (~train['neutral']).to_numpy(float)
    x[np.arange(len(train)), train['home'].map(idx).to_numpy()] = 1.0
    x[np.arange(len(train)), train['away'].map(idx).to_numpy()] = -1.0
    age = (day - train['day']).dt.days.to_numpy(float)
    w = np.ones(len(train)) if h_days is None else 0.5 ** (age / h_days)
    penalty = np.full(x.shape[1], lam)
    penalty[0] = 0.0
    beta = np.linalg.solve((x.T * w) @ x + np.diag(penalty), (x.T * w) @ train['margin'].to_numpy())
    return beta, idx


@pytest.mark.parametrize('h_days', [30, None], ids=['half-life-30', 'no-decay'])
def test_the_running_sums_give_the_same_margins_as_a_fresh_weighted_ridge(h_days):
    games = a_season()
    out = r.season_margins(games, h_days, 3.0).set_index('game_id')
    for gid in ('g45', 'g80', 't2'):
        g = games.set_index('game_id').loc[gid]
        beta, idx = fresh_ridge(games, g['day'], h_days, 3.0)
        want = beta[idx[g['home']]] - beta[idx[g['away']]] + (0.0 if g['neutral'] else beta[0])
        assert out.loc[gid, 'walk'] == pytest.approx(want, abs=1e-8)


def test_a_games_own_day_never_feeds_its_expected_margin():
    games = a_season()
    day = games.set_index('game_id').loc['g60', 'day']
    changed = games.copy()
    changed.loc[changed['day'] == day, 'margin'] += 40.0
    before = r.season_margins(games, 60, 3.0).set_index('game_id')['walk']
    after = r.season_margins(changed, 60, 3.0).set_index('game_id')['walk']
    same_day = games.loc[games['day'] == day, 'game_id']
    assert (before[same_day] == after[same_day]).all()
    assert before['g80'] != after['g80'], 'a later day does read it'


def test_the_lock_never_reads_a_tournament_game_and_the_walk_does():
    one = r.season_margins(a_season(first_four=7.0), 60, 3.0).set_index('game_id')
    other = r.season_margins(a_season(first_four=-30.0), 60, 3.0).set_index('game_id')
    assert (one.loc[['t1', 't2', 't3'], 'lock'] == other.loc[['t1', 't2', 't3'], 'lock']).all()
    assert one.loc['t2', 'walk'] != other.loc['t2', 'walk']
    assert one.loc['t1', 'lock'] == one.loc['t1', 'walk'], "on the tournament's first day the two are one"
    assert one['lock'].drop(['t1', 't2', 't3']).isna().all(), 'only tournament games are locked'


def test_a_neutral_game_gets_no_home_edge_and_a_home_game_does():
    rows = [(f'g{i}', f'2020-12-{i + 1:02d}', 'AB'[i % 2], 'BA'[i % 2], 10.0, False, False) for i in range(20)]
    rows += [('home', '2021-01-05', 'A', 'B', 1.0, False, False), ('neutral', '2021-01-05', 'A', 'B', 1.0, True, False)]
    out = r.season_margins(table(rows), None, 3.0).set_index('game_id')['walk']
    assert out['home'] == pytest.approx(10.0) and out['neutral'] == pytest.approx(0.0, abs=1e-9)


def test_swapping_the_two_clubs_flips_the_margin_and_the_forecast():
    base = a_season()
    listed = pd.concat([base, table([('x', '2021-02-20', 'A', 'D', 1.0, True, False)])])
    swapped = pd.concat([base, table([('x', '2021-02-20', 'D', 'A', -1.0, True, False)])])
    a = r.season_margins(listed.sort_values('day'), 60, 3.0).set_index('game_id').loc['x', 'walk']
    b = r.season_margins(swapped.sort_values('day'), 60, 3.0).set_index('game_id').loc['x', 'walk']
    assert a == pytest.approx(-b) and a != 0
    assert r.prob(0.1, np.array([a]))[0] == pytest.approx(1 - r.prob(0.1, np.array([b]))[0])


def test_a_club_with_no_earlier_game_is_rated_zero():
    games = pd.concat([a_season(), table([('new', '2021-02-20', 'Y', 'Z', 5.0, True, False)])]).sort_values('day')
    assert r.season_margins(games, 60, 3.0).set_index('game_id').loc['new', 'walk'] == pytest.approx(0.0, abs=1e-9)


def test_the_curve_has_no_intercept():
    rng = np.random.default_rng(5)
    x = rng.normal(0.0, 8.0, 400)
    y = (rng.random(400) < 1 / (1 + np.exp(-(1.0 + 0.15 * x)))).astype(int)  # the listed home wins more than x says
    coef = r.slope(x, y)
    want = 0.1
    for _ in range(50):  # Newton on b^2 / 2 + the log loss: the optimum with no intercept
        p = 1 / (1 + np.exp(-want * x))
        want -= (want + ((p - y) * x).sum()) / (1 + (p * (1 - p) * x * x).sum())
    assert coef == pytest.approx(want, rel=1e-3)
    assert r.prob(coef, np.array([0.0]))[0] == 0.5
    assert r.slope(-x, 1 - y) == pytest.approx(coef, rel=1e-6), 'the listing does not matter'


def test_margins_keeps_only_the_curve_rows_and_runs_each_season_on_its_own():
    two = pd.concat([a_season(), a_season().assign(season=2021, day=lambda d: d['day'] + pd.DateOffset(years=1),
                                                   game_id=lambda d: 'n' + d['game_id'])])
    out = r.margins(two, 60, 3.0)
    assert set(out['season']) == {2020, 2021}
    assert out.loc[out['season'] == 2020, 'day'].min() == pd.Timestamp('2021-01-01'), 'g28 is played that day'
    assert out.loc[out['season'] == 2021, 'day'].min() == pd.Timestamp('2022-01-01')
    alone = r.margins(a_season(), 60, 3.0).set_index('game_id')['walk']
    assert out.set_index('game_id').loc['g80', 'walk'] == alone['g80']
    assert out.set_index('game_id').loc['ng80', 'walk'] == pytest.approx(alone['g80'])


def test_the_history_is_read_with_tournament_games_neutral_whatever_the_flag_says(tmp_path):
    (tmp_path / 'games_2020.csv').write_text(
        'game_id,season,day,start_utc,home_id,away_id,home,away,home_score,away_score,neutral_site,tournament_id,'
        'note,conference_game,read_utc\n'
        '2,2020,2021-03-18,,10,11,A,B,60,70,False,22,East Region - 1st Round,False,x\n'
        '1,2020,2020-12-01,,10,11,A,B,80,70,False,,,False,x\n', encoding='utf-8')
    g = r.load(2020, 2020, tmp_path)
    assert list(g['game_id']) == ['1', '2'] and list(g['margin']) == [10.0, -10.0]
    assert list(g['neutral']) == [False, True] and list(g['home_win']) == [1, 0] and list(g['tournament']) == [False, True]
