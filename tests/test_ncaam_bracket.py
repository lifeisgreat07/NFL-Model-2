"""The bracket's odds and filled-in bracket (Stage 103 item 3), on fields built by hand.

Run with: pytest tests/test_ncaam_bracket.py -v
"""
import itertools
import math
import random

import numpy as np
import pandas as pd
import pytest

from src.sports.ncaam import bracket as b
from src.sports.ncaam import ratings
from src.sports.ncaam.collector import CollectorError

REGIONS = ('East', 'Midwest', 'South', 'West')


def a_field(first_four=(('East', 16), ('West', 11), ('South', 16), ('Midwest', 11))):
    """Sixty-eight clubs named by region and seed (E1 ... W16); each First Four slot holds two (E16a, E16b)."""
    regions = {}
    for r in REGIONS:
        slots = {}
        for s in range(1, 17):
            name = f'{r[0]}{s}'
            slots[s] = [name + 'a', name + 'b'] if (r, s) in first_four else [name]
        regions[r] = slots
    return b.Field(2024, regions, [['East', 'West'], ['Midwest', 'South']])


def by_strength(strength):
    """A forecast from club strengths: the curve on the difference, one minus itself when swapped."""
    return b.pair_forecast(strength, 0.15)


def strengths(field, seed=1):
    rng = random.Random(seed)
    return {c: rng.uniform(-10, 25) for c in field.clubs()}


def simulate(tree, p, rng):
    """One tournament played out at random, for checking the exact odds: each club's furthest round."""
    reached = {}

    def play(node, depth):
        if isinstance(node, str):
            winner = node
        else:
            x, y = (play(n, depth + 1) for n in node)
            winner = x if rng.random() < p(x, y) else y
        if depth <= 6:
            reached[winner] = b.ROUNDS[6 - depth]
        return winner

    play(tree, 0)
    return reached


def test_the_field_is_four_regions_of_sixteen_seeds_with_the_first_four_in_pairs():
    f = a_field()
    f.check()
    assert len(f.clubs()) == 68
    tree = f.tree()
    # The final's two halves are the two semifinals; the East plays the West.
    east_west = tree[0]
    assert 'E1' in str(east_west[0]) and 'W1' in str(east_west[1])


@pytest.mark.parametrize('broken, words', [
    (lambda f: f.regions['East'].pop(5), 'no club for seeds [5]'),
    (lambda f: f.regions['West'][3].append('E1'), 'clubs in two slots'),
    (lambda f: f.regions['South'][2].extend(['x', 'y']), '3 clubs'),
    (lambda f: setattr(f, 'semifinals', [['East', 'Midwest'], ['East', 'South']]), 'do not pair'),
], ids=['missing-seed', 'club-twice', 'three-in-a-slot', 'bad-semifinals'])
def test_a_broken_field_is_refused_with_the_fault_named(broken, words):
    f = a_field()
    broken(f)
    with pytest.raises(CollectorError, match=words.replace('[', r'\[').replace(']', r'\]')):
        f.check()


def test_the_first_round_pairs_seeds_that_add_up_to_seventeen_in_the_brackets_order():
    f = a_field(first_four=())
    region = f.tree()[0][0]  # the East
    games = []

    def walk(node, depth):
        if depth == 3:
            games.append(tuple(int(c[1:]) for c in node))
            return
        for n in node:
            walk(n, depth + 1)
    walk(region, 0)
    assert games == [(1, 16), (8, 9), (5, 12), (4, 13), (6, 11), (3, 14), (7, 10), (2, 15)]


def test_every_round_s_odds_add_up_to_the_clubs_left_in_it():
    f = a_field()
    chances = b.odds(f.tree(), by_strength(strengths(f)))
    left = {'round_of_64': 64, 'round_of_32': 32, 'sweet_16': 16, 'elite_8': 8, 'final_four': 4, 'final': 2,
            'champion': 1}
    for r, n in left.items():
        assert sum(c[r] for c in chances.values()) == pytest.approx(n)
    for c in chances.values():
        assert all(c[x] >= c[y] - 1e-12 for x, y in zip(b.ROUNDS, b.ROUNDS[1:]))


def test_a_first_four_club_reaches_the_round_of_sixty_four_only_by_winning_its_game():
    f = a_field()
    p = by_strength(strengths(f))
    chances = b.odds(f.tree(), p)
    assert chances['E16a']['round_of_64'] == pytest.approx(p('E16a', 'E16b'))
    assert chances['E16a']['round_of_64'] + chances['E16b']['round_of_64'] == pytest.approx(1.0)
    assert chances['E1']['round_of_64'] == 1.0


def test_a_first_round_win_is_the_pair_s_forecast_and_the_odds_are_exact_not_simulated():
    f = a_field(first_four=())
    p = by_strength(strengths(f))
    chances = b.odds(f.tree(), p)
    assert chances['E1']['round_of_32'] == pytest.approx(p('E1', 'E16'))
    # Round of 32: the 1 seed meets the 8 or the 9.
    want = p('E1', 'E16') * (p('E8', 'E9') * p('E1', 'E8') + p('E9', 'E8') * p('E1', 'E9'))
    assert chances['E1']['sweet_16'] == pytest.approx(want)


def test_a_simulation_of_many_tournaments_agrees_with_the_exact_odds():
    f = a_field()
    p = by_strength(strengths(f, seed=7))
    tree = f.tree()
    chances = b.odds(tree, p)
    rng = random.Random(11)
    n = 20000
    counts = {c: {r: 0 for r in b.ROUNDS} for c in f.clubs()}
    for _ in range(n):
        for club, furthest in simulate(tree, p, rng).items():
            for r in b.ROUNDS[:b.ROUNDS.index(furthest) + 1]:
                counts[club][r] += 1
    worst = max(abs(counts[c][r] / n - chances[c][r]) for c in f.clubs() for r in b.ROUNDS)
    assert worst < 0.02


def test_swapping_who_is_listed_first_changes_no_forecast():
    p = by_strength({'A': 3.0, 'B': -1.5})
    assert p('A', 'B') == pytest.approx(1 - p('B', 'A'))
    assert p('A', 'A') == 0.5


def test_the_filled_bracket_has_sixty_seven_games_and_never_contradicts_itself():
    f = a_field()
    p = by_strength(strengths(f, seed=3))
    chances = b.odds(f.tree(), p)
    games = b.filled(f.tree(), p, chances)
    assert len(games) == 67
    assert [g['round'] for g in games].count('first_four') == 4
    won = {}
    for g in games:
        won.setdefault(g['depth'], set()).add(g['winner'])
    # Every club placed in a game won its game in the round below; a First Four club, its First Four game.
    for g in games:
        for c in g['clubs']:
            if g['depth'] < 5:
                assert c in won[g['depth'] + 1]
            elif g['depth'] == 5 and c[-1] in 'ab':
                assert c in won[6]
    for g in games:
        assert g['winner'] in g['clubs']
        loser = [c for c in g['clubs'] if c != g['winner']][0]
        assert g['forecast'] == pytest.approx(p(g['winner'], loser))


def test_the_filled_bracket_s_champion_is_the_club_with_the_best_title_odds():
    f = a_field()
    for seed in range(5):
        p = by_strength(strengths(f, seed=seed))
        chances = b.odds(f.tree(), p)
        final = b.filled(f.tree(), p, chances)[-1]
        assert final['round'] == 'final'
        assert final['winner'] == max(chances, key=lambda c: chances[c]['champion'])


def test_the_lock_s_ratings_are_the_ones_the_confirmation_froze():
    rng = np.random.default_rng(5)
    days = pd.date_range('2021-12-01', '2022-03-10')
    clubs = list('ABCDEFGH')
    rows = []
    for i in range(160):
        h, a = rng.choice(len(clubs), size=2, replace=False)
        rows.append((f'g{i:03d}', days[i * len(days) // 160], clubs[h], clubs[a],
                     float(rng.integers(1, 25) * rng.choice([-1, 1])), bool(i % 4 == 0), False))
    rows += [('t1', pd.Timestamp('2022-03-15'), 'A', 'B', 5.0, True, True),
             ('t2', pd.Timestamp('2022-03-17'), 'C', 'D', -3.0, True, True)]
    g = pd.DataFrame(rows, columns=['game_id', 'day', 'home', 'away', 'margin', 'neutral', 'tournament'])
    g['season'] = 2021
    g['home_win'] = (g['margin'] > 0).astype(int)
    for h_days in (120, None):
        frozen = ratings.season_margins(g, h_days, 0.1).set_index('game_id')
        rated = ratings.ratings_before(g, pd.Timestamp('2022-03-15'), h_days, 0.1)
        for gid, (x, y) in {'t1': ('A', 'B'), 't2': ('C', 'D')}.items():
            assert rated[x] - rated[y] == pytest.approx(frozen.loc[gid, 'lock'], abs=1e-9)


def test_a_game_is_graded_on_the_saved_forecast_for_the_two_clubs_that_met():
    p = by_strength({'A': 5.0, 'B': 0.0, 'C': 1.0})
    played = pd.DataFrame([
        {'game_id': '1', 'day': '2025-03-20', 'home_id': 'A', 'away_id': 'B', 'home_score': '70', 'away_score': '60'},
        {'game_id': '2', 'day': '2025-03-20', 'home_id': 'C', 'away_id': 'A', 'home_score': '80', 'away_score': '61'},
    ])
    out = b.grade(played, p)
    assert out[0]['favourite_won'] and out[0]['log_loss'] == pytest.approx(-math.log(p('A', 'B')))
    assert not out[1]['favourite_won'] and out[1]['winner'] == 'C'
    assert out[1]['log_loss'] == pytest.approx(-math.log(p('C', 'A')))


def test_regions_are_read_from_the_tournament_s_notes():
    assert b.region_of("Men's Basketball Championship - South Region - First Four") == 'South'
    assert b.region_of("Men's Basketball Championship - Midwest Region - 1st Round") == 'Midwest'
    assert b.region_of("Men's Basketball Championship - Final Four") is None


def test_every_pair_s_forecast_is_used_once_each_way():
    f = a_field()
    p = by_strength(strengths(f))
    for x, y in itertools.islice(itertools.combinations(f.clubs(), 2), 200):
        assert p(x, y) + p(y, x) == pytest.approx(1.0)


# The lock: the field read from the scoreboards, saved once, graded on its saved pairs.

def board_event(gid, note, sides):
    """A scheduled tournament game as ESPN's scoreboard lists it: (club id, abbreviation, seed) per side, an id
    of -1 for a side not known yet."""
    return {'id': gid, 'competitions': [{'tournamentId': 22, 'notes': [{'headline': note}], 'competitors': [
        {'homeAway': ha, 'team': {'id': cid, 'abbreviation': abbr}, 'curatedRank': {'current': seed}}
        for ha, (cid, abbr, seed) in zip(('home', 'away'), sides)]}]}


def numbered_field():
    """The hand-built field with each club given a numeric id, as ESPN's are."""
    f = a_field()
    ids = {c: str(1000 + i) for i, c in enumerate(f.clubs())}
    return f, ids


def boards_for(f, ids):
    """The First Four's board and the first round's board for the field `f`."""
    first_four, first_round = [], []
    for region, slots in f.regions.items():
        for seed in b.ORDER[::2]:
            other = 17 - seed
            sides = []
            for s in (seed, other):
                if len(slots[s]) == 2:
                    x, y = slots[s]
                    first_four.append(board_event(f'ff{region}{s}', f"Men's Basketball Championship - {region} "
                                                  'Region - First Four',
                                                  [(ids[x], x, s), (ids[y], y, s)]))
                    sides.append(('-1', 'TBD', None))
                else:
                    sides.append((ids[slots[s][0]], slots[s][0], s))
            first_round.append(board_event(f'r{region}{seed}', f"Men's Basketball Championship - {region} Region "
                                           '- 1st Round', sides))
    other = {'id': 'x', 'competitions': [{'tournamentId': 5, 'notes': [], 'competitors': []}]}
    return [{'events': first_four + [other]}, {'events': first_round}]


def test_the_field_is_read_from_the_first_four_and_first_round_boards():
    f, ids = numbered_field()
    got = b.field_from_boards(boards_for(f, ids), 2026, f.semifinals)
    want = {r: {s: sorted(ids[c] for c in slot) for s, slot in slots.items()} for r, slots in f.regions.items()}
    assert got.regions == want
    assert len(got.clubs()) == 68
    assert got.names[ids['E16a']] == 'E16a'


def test_a_board_seed_outside_one_to_sixteen_is_refused_with_the_game_named():
    f, ids = numbered_field()
    boards = boards_for(f, ids)
    boards[1]['events'][0]['competitions'][0]['competitors'][0]['curatedRank']['current'] = 99
    with pytest.raises(CollectorError, match='has seed 99'):
        b.field_from_boards(boards, 2026, f.semifinals)


def lock_history(tmp_path, ids, tournament_started=False):
    """A season of games among the field's clubs, stored as the history keeps it, with the backtest's registry,
    setting and checked history replaced by hand-built ones."""
    rng = np.random.default_rng(9)
    clubs = sorted(ids.values())
    days = pd.date_range('2025-11-03', '2026-03-14')
    rows = []
    for i in range(700):
        h, a = rng.choice(len(clubs), size=2, replace=False)
        hs = int(rng.integers(50, 90))
        rows.append({'game_id': f'{i:04d}', 'season': '2025', 'day': str(days[i * len(days) // 700].date()),
                     'home_id': clubs[h], 'away_id': clubs[a], 'home': clubs[h], 'away': clubs[a],
                     'home_score': str(hs), 'away_score': str(hs + int(rng.integers(1, 20)) * int(rng.choice([-1, 1]))),
                     'neutral_site': str(bool(i % 5 == 0)), 'tournament_id': '', 'note': ''})
    if tournament_started:
        rows[-1]['tournament_id'] = '22'
    folder = tmp_path / 'history'
    folder.mkdir()
    pd.DataFrame(rows).to_csv(folder / 'games_2025.csv', index=False)
    return folder


@pytest.fixture
def no_registry(monkeypatch):
    from src.sports.ncaam import backtest
    monkeypatch.setattr(backtest, 'registry', lambda: {'protocol': {'training_from_season': 2025}})
    monkeypatch.setattr(backtest, 'chosen', lambda: {'H_days': 120, 'lambda': 0.1})
    monkeypatch.setattr(backtest, 'load_history', lambda first, last, folder: ratings.load(first, last, folder))


def test_the_lock_saves_every_pair_once_and_is_never_rewritten(tmp_path, no_registry):
    f, ids = numbered_field()
    folder = lock_history(tmp_path, ids)
    field_ = b.field_from_boards(boards_for(f, ids), 2025, f.semifinals)
    out = tmp_path / 'bracket'
    doc = b.lock(2026, field_, folder, out, now='2026-03-15T22:00:00Z')
    assert len(doc['pairs']) == 68 * 67 // 2
    assert doc['games_through'] == '2026-03-14'
    assert (out / 'lock_2026.json').exists()
    assert sum(c['champion'] for c in doc['odds'].values()) == pytest.approx(1.0)
    with pytest.raises(CollectorError, match='never rewritten'):
        b.lock(2026, field_, folder, out)


def test_the_lock_is_refused_once_the_tournament_has_begun(tmp_path, no_registry):
    f, ids = numbered_field()
    folder = lock_history(tmp_path, ids, tournament_started=True)
    field_ = b.field_from_boards(boards_for(f, ids), 2025, f.semifinals)
    with pytest.raises(CollectorError, match='has begun'):
        b.lock(2026, field_, folder, tmp_path / 'bracket')
    assert not (tmp_path / 'bracket').exists()


def test_a_game_is_graded_on_the_saved_pair_not_a_recomputed_one():
    doc = {'pairs': {'1|2': 0.7}}
    p = b.saved_forecast(doc)
    assert p('1', '2') == 0.7 and p('2', '1') == pytest.approx(0.3)
    with pytest.raises(CollectorError, match='not in the locked field'):
        p('1', '3')
