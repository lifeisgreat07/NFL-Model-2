"""The bracket: each club's odds of reaching each round, and one filled-in bracket (Stage 103 item 3).

The confirmation (#760) found H1 INCONCLUSIVE, so Model A makes the bracket, as the registration's consequence says,
and the page prints the verdict beside it. Nothing here is fitted or chosen: Model A's setting is the tuning's
(`backtest.chosen()`), the ratings are those of the lock (the season's games strictly before the tournament's first
game, `ratings.ratings_before`) and the curve is fitted on every curve row before that day, as the confirmation's
`lock_forecasts` fits it. Every tournament game is neutral, so a pair's forecast is the curve applied to one rating
minus the other, and one minus itself when the two are swapped.

The field: four regions of sixteen seeds, a seed's slot holding one club or the two clubs of a First Four game, and
the two semifinals naming which regions meet. Within a region the slots meet in the bracket's fixed order (1 v 16,
8 v 9, 5 v 12, 4 v 13, 6 v 11, 3 v 14, 7 v 10, 2 v 15, the winners in that order).

The odds are exact, not simulated: a club wins a game of the bracket with its chance of winning its own half times
the sum, over each club that could come out of the other half, of that club's chance of doing so and the pair's
forecast. A simulation would only approximate these numbers.

The filled-in bracket is chosen from the top: the champion is the club with the best title odds; in every game below
it, the club already placed there by a later round wins, and otherwise the club with the best odds of winning that
game's part of the bracket. So the filled bracket never contradicts itself and its champion is the likeliest one;
picking each game's favourite from the first round up can crown a club with worse title odds.

Run by hand: python -m src.sports.ncaam.bracket dryrun 2025   (a past tournament, from the stored history: writes
             data/ncaam/bracket/dryrun_2025.json, the field, every club's odds, the filled bracket and each game's
             grade, and checks every played game's forecast against the confirmation's locked one)
             python -m src.sports.ncaam.bracket lock 2027 <First Four and first-round days, comma-separated>
                    <the semifinals, as East-South,West-Midwest>
                    (the one lock, between Selection Sunday and the First Four: data/ncaam/bracket/lock_2027.json,
                    written once and never rewritten)
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import date
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.sports.ncaam import backtest, ratings
from src.sports.ncaam.collector import HISTORY, CollectorError, day_board
from src.sports.ncaam.seeds import round_of_64

NCAA = '22'
#: The seeds' slots in a region, in the order they meet.
ORDER = (1, 16, 8, 9, 5, 12, 4, 13, 6, 11, 3, 14, 7, 10, 2, 15)
#: The rounds a club can reach, in order. A club in a First Four game reaches the round of 64 by winning it.
ROUNDS = ('round_of_64', 'round_of_32', 'sweet_16', 'elite_8', 'final_four', 'final', 'champion')
#: The round a game is played in, by how many games below the final it is.
PLAYED = ('final', 'final_four', 'elite_8', 'sweet_16', 'round_of_32', 'round_of_64', 'first_four')
OUT = Path(__file__).resolve().parents[3] / 'data' / 'ncaam' / 'bracket'

Node = str | tuple[Any, Any]
Forecast = Callable[[str, str], float]


@dataclass
class Field:
    """A tournament's field: `regions[name][seed]` is the slot's clubs (one, or the two of a First Four game);
    `semifinals` is the two pairs of regions that meet in the Final Four."""
    season: int
    regions: dict[str, dict[int, list[str]]]
    semifinals: list[list[str]]
    names: dict[str, str] = field(default_factory=dict)

    def clubs(self) -> list[str]:
        return sorted(c for r in self.regions.values() for slot in r.values() for c in slot)

    def check(self) -> None:
        """Raise, naming each fault, unless there are four regions of sixteen seeds, each slot one club or two,
        no club twice, and two semifinals pairing the four regions."""
        problems = []
        if len(self.regions) != 4:
            problems.append(f'{len(self.regions)} regions, not 4')
        for name, slots in self.regions.items():
            missing = sorted(set(range(1, 17)) - set(slots))
            if missing:
                problems.append(f'{name}: no club for seeds {missing}')
            for seed, slot in slots.items():
                if len(slot) not in (1, 2):
                    problems.append(f'{name} {seed}: {len(slot)} clubs')
        clubs = self.clubs()
        twice = sorted({c for c in clubs if clubs.count(c) > 1})
        if twice:
            problems.append(f'clubs in two slots: {twice}')
        paired = sorted(r for pair in self.semifinals for r in pair)
        if len(self.semifinals) != 2 or paired != sorted(self.regions):
            problems.append(f'the semifinals {self.semifinals} do not pair the four regions')
        if problems:
            raise CollectorError('; '.join(problems))

    def tree(self) -> Node:
        """The bracket as nested pairs: a leaf is a club, a First Four game is a pair of clubs."""
        def region(name: str) -> Node:
            nodes: list[Node] = [(self.regions[name][s][0], self.regions[name][s][1]) if len(self.regions[name][s]) == 2
                                 else self.regions[name][s][0] for s in ORDER]
            while len(nodes) > 1:
                nodes = [(nodes[i], nodes[i + 1]) for i in range(0, len(nodes), 2)]
            return nodes[0]
        (a, b), (c, d) = self.semifinals
        return ((region(a), region(b)), (region(c), region(d)))


def region_of(note: str) -> str | None:
    m = re.search(r'-\s*([A-Za-z ]+?) Region', note)
    return m.group(1).strip() if m else None


def field_from_history(season: int, folder: Path = HISTORY) -> Field:
    """A past tournament's field from the stored history: each club's region and seed from its First Four or first
    round game, and the semifinals from the Final Four's two games. A season is labelled by its starting year."""
    g = pd.read_csv(folder / f'games_{season}.csv', dtype=str, keep_default_na=False)
    t = g[g['tournament_id'] == NCAA]
    seeds = pd.read_csv(folder / f'seeds_{season}.csv', dtype={'game_id': str}).set_index('game_id')
    regions: dict[str, dict[int, list[str]]] = {}
    where: dict[str, str] = {}
    names: dict[str, str] = {}
    for row in t.itertuples():
        note = str(row.note)
        names[row.home_id], names[row.away_id] = row.home, row.away
        first_games = 'first four' in note.lower() or round_of_64(note, season)
        name = region_of(note)
        if not first_games or name is None:
            continue
        s = seeds.loc[row.game_id]
        for club, seed in ((row.home_id, int(s['home_seed'])), (row.away_id, int(s['away_seed']))):
            slot = regions.setdefault(name, {}).setdefault(seed, [])
            if club not in slot:
                slot.append(club)
            where[club] = name
    semis = [[where[r.home_id], where[r.away_id]] for r in t.itertuples() if 'final four' in str(r.note).lower()]
    for slots in regions.values():
        for slot in slots.values():
            slot.sort()
    out = Field(season, {k: dict(sorted(v.items())) for k, v in sorted(regions.items())}, semis,
                {c: names[c] for c in where})
    out.check()
    return out


def odds(tree: Node, p: Forecast) -> dict[str, dict[str, float]]:
    """Each club's chance of reaching each round (ROUNDS), exactly."""
    out: dict[str, dict[str, float]] = {}

    def win(node: Node, depth: int) -> dict[str, float]:
        """The chance of each club winning `node`; `depth` counts the games from the top (the final is 0)."""
        if isinstance(node, str):
            dist = {node: 1.0}
        else:
            left, right = (win(n, depth + 1) for n in node)
            dist = {}
            for one, other in ((left, right), (right, left)):
                for a, pa in one.items():
                    dist[a] = pa * sum(pb * p(a, b) for b, pb in other.items())
        # Six games below the final is a seed's slot: a club placed there, or the winner of its First Four game,
        # reaches the round of 64. A First Four club's own leaf (seven below) reaches nothing yet.
        if depth <= 6:
            for club, q in dist.items():
                out.setdefault(club, {r: 0.0 for r in ROUNDS})[ROUNDS[6 - depth]] = q
        return dist

    win(tree, 0)
    return out


def filled(tree: Node, p: Forecast, chances: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    """The filled-in bracket, chosen from the top (see the module's docstring): one row per game, with the round
    it is played in, the two clubs placed in it, the winner and the pair's forecast for the winner."""
    games: list[dict[str, Any]] = []

    def clubs_in(node: Node) -> list[str]:
        return [node] if isinstance(node, str) else [c for n in node for c in clubs_in(n)]

    def best(node: Node, depth: int) -> str:
        """The club with the best odds of winning `node`; ties to the earlier club in name order."""
        return min(clubs_in(node), key=lambda c: (-chances[c][ROUNDS[6 - depth]], c))

    def place(node: Node, depth: int, winner: str) -> None:
        if isinstance(node, str):
            return
        left, right = node
        a = winner if winner in clubs_in(left) else best(left, depth + 1)
        b = winner if winner in clubs_in(right) else best(right, depth + 1)
        place(left, depth + 1, a)
        place(right, depth + 1, b)
        loser = b if winner == a else a
        games.append({'round': PLAYED[depth], 'depth': depth,
                      'clubs': [a, b], 'winner': winner, 'forecast': p(winner, loser)})

    place(tree, 0, best(tree, 0))
    games.sort(key=lambda g: -g['depth'])
    return games


def pair_forecast(rated: dict[str, float], coef: float) -> Forecast:
    """Model A for a neutral game: the curve applied to the first club's rating minus the second's."""
    def p(a: str, b: str) -> float:
        return 1.0 / (1.0 + math.exp(-coef * (rated.get(a, 0.0) - rated.get(b, 0.0))))
    return p


def lock_model(games: pd.DataFrame, table: pd.DataFrame, season: int, first_day: pd.Timestamp,
               setting: dict[str, Any]) -> tuple[dict[str, float], float]:
    """The lock's ratings and curve for a tournament whose first game is on `first_day`: the season's games before
    it, and every curve row of `table` (ratings.margins of `games`, the history to `season`) before it."""
    rows = table[table['day'] < first_day]
    coef = ratings.slope(rows['walk'].to_numpy(float), rows['home_win'].to_numpy())
    rated = ratings.ratings_before(games[games['season'] == season], first_day, setting['H_days'],
                                   setting['lambda'])
    return rated, coef


def grade(played: pd.DataFrame, p: Forecast) -> list[dict[str, Any]]:
    """Each played game scored on the saved forecast for the two clubs that met: the winner's forecast and the
    game's log loss."""
    out = []
    for g in played.itertuples():
        home_won = int(g.home_score) > int(g.away_score)
        q = p(g.home_id, g.away_id)
        won = q if home_won else 1 - q
        out.append({'game_id': g.game_id, 'day': g.day, 'home': g.home_id, 'away': g.away_id,
                    'home_forecast': q, 'winner': g.home_id if home_won else g.away_id,
                    'favourite_won': (q > 0.5) == home_won, 'log_loss': -math.log(won)})
    return out


def dry_run(tournament: int, folder: Path = HISTORY) -> dict[str, Any]:
    """The whole bracket for a past tournament (named by the year it is played), from the stored history, with
    every played game's forecast checked against the confirmation's locked one."""
    reg = backtest.registry()
    season = tournament - 1
    setting = backtest.chosen()
    f = field_from_history(season, folder)
    g = pd.read_csv(folder / f'games_{season}.csv', dtype=str, keep_default_na=False)
    played = g[g['tournament_id'] == NCAA]
    first_day = pd.Timestamp(played['day'].min())
    games = backtest.load_history(reg['protocol']['training_from_season'], season, folder)
    table = ratings.margins(games, setting['H_days'], setting['lambda'])
    rated, coef = lock_model(games, table, season, first_day, setting)
    p = pair_forecast(rated, coef)
    tree = f.tree()
    chances = odds(tree, p)
    locked = table[table['tournament'] & (table['season'] == season)].set_index('game_id')
    worst = max(abs(p(r.home, r.away) - float(ratings.prob(coef, np.array([r.lock]))[0])) for r in locked.itertuples())
    if worst > 1e-9:
        raise CollectorError(f'the bracket and the confirmation differ by up to {worst:.2e} on a played game')
    graded = grade(played, p)
    return {'tournament': tournament, 'H_days': setting['H_days'], 'lambda': setting['lambda'], 'curve': coef,
            'field': {'regions': f.regions, 'semifinals': f.semifinals}, 'names': f.names,
            'ratings': {c: rated.get(c, 0.0) for c in f.clubs()}, 'odds': chances,
            'filled': filled(tree, p, chances), 'graded': graded,
            'summary': {'games': len(graded), 'log_loss': sum(x['log_loss'] for x in graded) / len(graded),
                        'favourite_won': sum(x['favourite_won'] for x in graded)}}


def field_from_boards(boards: Iterable[Any], season: int, semifinals: list[list[str]]) -> Field:
    """The field from ESPN's scoreboards for the First Four's and the first round's days, read once the bracket is
    out (Selection Sunday): each club's region from its game's note and its seed from `curatedRank`, a side not
    yet known (the winner of a First Four game) left out. The scoreboard does not say which regions meet in the
    Final Four, so `semifinals` is given."""
    regions: dict[str, dict[int, list[str]]] = {}
    names: dict[str, str] = {}
    problems = []
    for board in boards:
        for e in board.get('events') or []:
            comp = (e.get('competitions') or [{}])[0]
            if str(comp.get('tournamentId') or '') != NCAA:
                continue
            note = '; '.join(str(n.get('headline')) for n in comp.get('notes') or [] if n.get('headline'))
            name = region_of(note)
            if name is None or not ('first four' in note.lower() or round_of_64(note, season)):
                continue
            for c in comp.get('competitors') or []:
                team = c.get('team') or {}
                seed = (c.get('curatedRank') or {}).get('current')
                if not str(team.get('id') or '').isdigit():
                    continue  # the winner of a First Four game, not known yet
                if not (isinstance(seed, int) and 1 <= seed <= 16):
                    problems.append(f'game {e.get("id")}: club {team.get("id")} has seed {seed}')
                    continue
                slot = regions.setdefault(name, {}).setdefault(seed, [])
                if str(team['id']) not in slot:
                    slot.append(str(team['id']))
                names[str(team['id'])] = str(team.get('abbreviation') or '')
    if problems:
        raise CollectorError('; '.join(problems))
    out = Field(season, {k: {s: sorted(v[s]) for s in sorted(v)} for k, v in sorted(regions.items())},
                semifinals, names)
    out.check()
    return out


def lock(tournament: int, f: Field, folder: Path = HISTORY, out: Path = OUT,
         now: str | None = None) -> dict[str, Any]:
    """The one lock (registry forward_test.lock): the ratings, the curve, every pair's forecast, every club's odds
    and the filled bracket, from every stored game. Written once and never rewritten; refused once any game of
    the tournament is stored, since the lock comes before the First Four's first game."""
    path = out / f'lock_{tournament}.json'
    if path.exists():
        raise CollectorError(f'{path.name} exists: the lock is saved once and never rewritten')
    season = tournament - 1
    g = pd.read_csv(folder / f'games_{season}.csv', dtype=str, keep_default_na=False)
    if (g['tournament_id'] == NCAA).any():
        raise CollectorError(f'the {tournament} tournament has begun: a lock comes before its first game')
    reg = backtest.registry()
    setting = backtest.chosen()
    games = backtest.load_history(reg['protocol']['training_from_season'], season, folder)
    table = ratings.margins(games, setting['H_days'], setting['lambda'])
    day = games['day'].max() + pd.Timedelta(days=1)
    rated, coef = lock_model(games, table, season, day, setting)
    unrated = sorted(c for c in f.clubs() if c not in rated)
    if unrated:
        raise CollectorError(f'clubs in the field with no game this season: {unrated}')
    p = pair_forecast(rated, coef)
    tree = f.tree()
    chances = odds(tree, p)
    clubs = f.clubs()
    doc = {'tournament': tournament, 'locked_utc': now or pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%dT%H:%M:%SZ'),
           'games_through': str((day - pd.Timedelta(days=1)).date()), 'H_days': setting['H_days'],
           'lambda': setting['lambda'], 'curve': coef,
           'field': {'regions': f.regions, 'semifinals': f.semifinals}, 'names': f.names,
           'ratings': {c: rated[c] for c in clubs},
           'pairs': {f'{a}|{b}': p(a, b) for a, b in combinations(clubs, 2)},
           'odds': chances, 'filled': filled(tree, p, chances)}
    out.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8')
    return doc


def saved_forecast(doc: dict[str, Any]) -> Forecast:
    """A lock's forecast for any two clubs of its field, read from its saved pairs, never recomputed."""
    pairs: dict[str, float] = doc['pairs']

    def p(a: str, b: str) -> float:
        if f'{a}|{b}' in pairs:
            return pairs[f'{a}|{b}']
        if f'{b}|{a}' in pairs:
            return 1.0 - pairs[f'{b}|{a}']
        raise CollectorError(f'no saved forecast for {a} v {b}: a club not in the locked field')
    return p


def graded(doc: dict[str, Any], folder: Path = HISTORY) -> list[dict[str, Any]]:
    """The tournament's stored games so far, each scored on the lock's saved forecast."""
    g = pd.read_csv(folder / f'games_{doc["tournament"] - 1}.csv', dtype=str, keep_default_na=False)
    return grade(g[g['tournament_id'] == NCAA], saved_forecast(doc))


def main(argv: Iterable[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) == 4 and args[0] == 'lock':
        # lock <tournament year> <day,day,...> <Region-Region,Region-Region>
        days = [date.fromisoformat(d) for d in args[2].split(',')]
        semis = [pair.split('-') for pair in args[3].split(',')]
        f = field_from_boards([day_board(d) for d in days], int(args[1]) - 1, semis)
        doc = lock(int(args[1]), f)
        champ = doc['filled'][-1]['winner']
        print(f"lock_{args[1]}.json: {len(doc['pairs'])} pairs; champion {doc['names'].get(champ, champ)} "
              f"({doc['odds'][champ]['champion']:.3f})")
        return 0
    if len(args) != 2 or args[0] != 'dryrun':
        raise SystemExit('usage: python -m src.sports.ncaam.bracket dryrun <tournament year>\n'
                         '       python -m src.sports.ncaam.bracket lock <tournament year> <days> <semifinals>')
    doc = dry_run(int(args[1]))
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f'dryrun_{args[1]}.json'
    path.write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8')
    champ = doc['filled'][-1]
    s = doc['summary']
    print(f"{path.name}: champion {doc['names'].get(champ['winner'], champ['winner'])} "
          f"({doc['odds'][champ['winner']]['champion']:.3f}); {s['games']} games graded, log loss "
          f"{s['log_loss']:.4f}, favourite won {s['favourite_won']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
