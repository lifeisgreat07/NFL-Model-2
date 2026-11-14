"""The NBA's day-sport v2, its history and its backtest (experiments/nba/stage95_v2/registry.json).

Stage 95 item 35 with Stage 94 items 24 and 27 to 30, from audit 7, registered as a shadow before anything here
was fitted. Each change is one function, named for its item:

- 27, `drop_exhibitions`: a game in which either team is not one of the league's 30 codes (the All-Star games,
  filed as regular season) leaves the history before anything is computed;
- 30, `place_slates`: a slate that lists one team twice is mended by each such game's date in ESPN's own record of
  it, read when the history is built; games ESPN's record still puts on one slate for one team are dropped and
  listed, no date guessed (amended 2026-11-12, before any fit: ESPN keeps both 2020-03-01 GS games on that day);
- 29, `drop_bad_prices` and `short_boxes`: a price whose two implied probabilities sum to under 1.00 or over 1.20
  is not used (the game counts as unpriced), and a box short of 240 minutes by more than half a minute a listed
  player is not used for minutes or availability (each player's minutes are rounded to whole minutes);
- 24, `availability_table`: a player counts as out when he has expected minutes for his team and did not appear in
  the team's previous game; the same rule in the backtest and live, so neither reads who played in the game
  itself or the injury report. A team's first game, or a game after a box that is not used, has availability 1.0;
- 28, `walk_forward`: a neutral-site game gets no home edge: the fitted intercept is not added to its forecast.

`main` tunes H and lambda over the registered grid on the validation seasons only, then measures v2 against the
registered models on the confirmation seasons (MV1) and v2 without availability beside v2 (MV2). Both are
measurements: those seasons have been seen, and nothing here decides anything. The decision is the live forward
test's, once, after the regular season (the registration's V1 and V2).

Run with: python -m src.sports.nba.v2
"""
from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from collections.abc import Set as AbstractSet
from typing import Any

import numpy as np
import pandas as pd

from src.core.day_backtest import base_rate, estimator, scores
from src.core.sport import sport_paths

from . import backtest, history, ratings, teams

PATHS = sport_paths('nba')
FOLDER = PATHS.experiments / 'stage95_v2'
REGISTRY = FOLDER / 'registry.json'
RESULTS = FOLDER / 'results'
#: Item 29's bounds on the two implied probabilities' sum, margin included.
PRICE_SUM = (1.00, 1.20)
#: A regulation game's team minutes, and what whole-minute rounding may take from it per listed player.
REGULATION_MINUTES = 240
ROUNDING_PER_PLAYER = 0.5
#: MV1 and MV2 are reported at 95%; they decide nothing, so they spend no alpha.
MEASURE_LEVEL = 0.95
A_COLUMNS = backtest.A_COLUMNS
ET = 'America/New_York'


def registry() -> dict[str, Any]:
    reg: dict[str, Any] = json.loads(REGISTRY.read_text(encoding='utf-8'))
    return reg


def drop_exhibitions(games: pd.DataFrame, codes: Iterable[str] = teams.NAMES) -> tuple[pd.DataFrame, list[str]]:
    """Item 27: the games whose two teams are both league clubs, and the ids of the rest."""
    known = set(codes)
    keep = games['home'].isin(known) & games['away'].isin(known)
    return games[keep].copy(), sorted(games.loc[~keep, 'game_id'].astype(str))


def doubled_slates(games: pd.DataFrame) -> dict[str, list[str]]:
    """Each slate on which a team appears more than once, with the ids of the games that list it."""
    out: dict[str, list[str]] = {}
    for slate, day in games.groupby('slate'):
        sides = pd.concat([day['home'], day['away']])
        twice = set(sides[sides.duplicated()])
        if twice:
            out[str(slate)] = sorted(day.loc[day['home'].isin(twice) | day['away'].isin(twice), 'game_id'].astype(str))
    return out


def espn_slate(gid: str, get: Callable[[str], bytes] = history.fetch) -> str:
    """The Eastern date of a game's start in ESPN's own record of it."""
    raw = json.loads(get(history.SUMMARY.format(gid=gid)))
    start = ((raw.get('header') or {}).get('competitions') or [{}])[0].get('date')
    if not start:
        raise LookupError(f'ESPN gives no start for game {gid}')
    return str(pd.Timestamp(start).tz_convert(ET).date())


def place_slates(games: pd.DataFrame, slate_of: Callable[[str], str]) -> tuple[pd.DataFrame, dict[str, str], list[str]]:
    """Item 30 as amended: every game on a doubled slate is placed on the date `slate_of` gives; games still
    doubled after that are dropped. Returns the games, where each was placed, and the ids dropped."""
    g = games.copy()
    moved: dict[str, str] = {}
    for gids in doubled_slates(g).values():
        for gid in gids:
            day = slate_of(gid)
            moved[gid] = day
            g.loc[g['game_id'].astype(str) == gid, 'slate'] = day
    dropped = sorted(gid for gids in doubled_slates(g).values() for gid in gids)
    return g[~g['game_id'].astype(str).isin(dropped)].copy(), moved, dropped


def drop_bad_prices(market: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Item 29: the prices whose two implied probabilities sum within PRICE_SUM, and the ids of the rest. A price
    whose `source` is Kalshi is already two probabilities (each side's mid), summed as they are (audit 8, S6)."""
    total = market['home_price'].map(history.implied) + market['away_price'].map(history.implied)
    if 'source' in market:
        kalshi = market['source'].fillna('').eq('kalshi')
        total = total.where(~kalshi, market['home_price'] + market['away_price'])
    ok = (total >= PRICE_SUM[0]) & (total <= PRICE_SUM[1])
    return market[ok].copy(), sorted(market.loc[~ok, 'game_id'].astype(str))


def short_boxes(minutes: pd.DataFrame) -> set[tuple[str, str]]:
    """Item 29: the (game, team) boxes short of 240 minutes by more than half a minute a listed player."""
    played = minutes[minutes['minutes'] > 0]
    t = played.groupby(['game_id', 'team']).agg(total=('minutes', 'sum'), players=('player_id', 'count'))
    short = t[REGULATION_MINUTES - t['total'] > ROUNDING_PER_PLAYER * t['players']]
    return {(str(g), str(team)) for g, team in short.index}


def availability_table(games: pd.DataFrame, minutes: pd.DataFrame, half_life: float,
                       unusable: AbstractSet[tuple[str, str]] = frozenset(), power: float = 1.0) -> pd.Series:
    """Item 24: availability_matchup for every game, indexed by game_id.

    As `ratings.availability_table`, each team's games are walked in date order with each player's weighted
    minutes carried forward and decayed by 0.5^(days / H). What differs is who is counted as available: the
    players who appeared (minutes above zero) in the team's previous game, not in the game itself. A box in
    `unusable` adds nothing to the carried minutes, and the game after it has availability 1.0 (nobody is known
    to be out).

    `power` weights each player by his expected minutes raised to it: 1, v2's own rule, is the minutes themselves;
    v3's star weighting (experiments/nba/stage105_v3) is 2."""
    m = minutes.copy()
    m['game_id'] = m['game_id'].astype(str)
    m['player_id'] = m['player_id'].astype(str)
    day_of = dict(zip(games['game_id'], games['day']))
    m = m[m['game_id'].isin(day_of)]
    by_game_team = {key: frame for key, frame in m.groupby(['game_id', 'team'])}
    avail: dict[tuple[str, str], float] = {}
    for team in sorted(set(games['home']) | set(games['away'])):
        own = games[(games['home'] == team) | (games['away'] == team)].sort_values(['day', 'game_id'], kind='stable')
        carried: dict[str, float] = {}
        weight_sum = 0.0
        last: pd.Timestamp | None = None
        previous: set[str] | None = None
        for gid, day in zip(own['game_id'], own['day']):
            if last is not None and day > last:
                decay = 0.5 ** ((day - last).days / half_life)
                carried = {p: v * decay for p, v in carried.items()}
                weight_sum *= decay
            last = day
            expected = {p: (v / weight_sum) ** power for p, v in carried.items()} if weight_sum else {}
            avail[(gid, team)] = 1.0 if previous is None else ratings.availability(expected, previous)
            rows = by_game_team.get((gid, team))
            if rows is None or (gid, team) in unusable:
                previous = None
                continue
            previous = set(rows.loc[rows['minutes'] > 0, 'player_id'])
            for p, mins in zip(rows['player_id'], rows['minutes'].astype(float)):
                carried[p] = carried.get(p, 0.0) + mins
            weight_sum += 1.0
    return pd.Series({gid: avail[(gid, h)] - avail[(gid, a)]
                      for gid, h, a in zip(games['game_id'], games['home'], games['away'])},
                     name='availability_matchup')


def walk_forward(table: pd.DataFrame, columns: Sequence[str], seasons: Sequence[int],
                 needs_market: bool = False) -> pd.Series:
    """`src.core.day_backtest.walk_forward`, except item 28: on a neutral-site game the fitted intercept, the home
    edge, is not added to the forecast. Its row still enters the fit as listed."""
    rows = table.dropna(subset=['home_prob']) if needs_market else table
    preds: dict[str, float] = {}
    for day in sorted(rows.loc[rows['season'].isin(seasons), 'day'].unique()):
        train = rows[rows['day'] < day]
        today = rows[rows['day'] == day]
        model = estimator().fit(train[list(columns)], train['home_win'])
        z = model.decision_function(today[list(columns)])
        neutral = today['neutral_site'].fillna(False).astype(bool).to_numpy()
        if not needs_market:  # Audit 8 S1: Model B's price already carries the site
            z = np.where(neutral, z - float(model[-1].intercept_[0]), z)
        preds.update(zip(today['game_id'], 1.0 / (1.0 + np.exp(-z))))
    return pd.Series(preds, name='p')


def build(raw: pd.DataFrame, minutes: pd.DataFrame, market: pd.DataFrame,
          slate_of: Callable[[str], str]) -> tuple[pd.DataFrame, set[tuple[str, str]], dict[str, Any]]:
    """v2's history: items 27 and 30 on the games, item 29 on the prices and the boxes. Returns the prepared games
    (with `home_prob` where a usable price exists), the boxes not used, and what each rule touched."""
    games, exhibitions = drop_exhibitions(raw)
    games, moved, doubled = place_slates(games, slate_of)
    prices, bad = drop_bad_prices(market)
    games = games.drop(columns=['home_prob'], errors='ignore').merge(
        prices[['game_id', 'home_prob']], on='game_id', how='left')
    unusable = short_boxes(minutes[minutes['game_id'].isin(set(games['game_id']))])
    touched = {'exhibitions_dropped': exhibitions, 'slates_placed': moved, 'still_doubled_dropped': doubled,
               'prices_not_used': bad,
               'boxes_not_used': sorted(f'{g} {t}' for g, t in unusable)}
    return ratings.prepare(games), unusable, touched


def features(games: pd.DataFrame, minutes: pd.DataFrame, h: float, lam: float, unusable: set[tuple[str, str]],
             avail: pd.Series | None = None) -> pd.DataFrame:
    if avail is None:
        avail = availability_table(games, minutes, h, unusable)
    table = ratings.features(games, minutes, h, lam, avail=avail)
    return table.merge(games[['game_id', 'home_prob', 'neutral_site']], on='game_id', how='left')


def tune(games: pd.DataFrame, minutes: pd.DataFrame, unusable: set[tuple[str, str]],
         grid: Mapping[str, Sequence[float]], seasons: Sequence[int]) -> dict[str, Any]:
    """H and lambda over the registered grid by Model A's pooled log loss on the validation seasons only; no
    game after the last validation season is read."""
    games = games[games['season'] <= max(seasons)]
    results = []
    for h in grid['H_days']:
        avail = availability_table(games, minutes, h, unusable)
        for lam in grid['lambda']:
            table = features(games, minutes, h, lam, unusable, avail)
            s = scores(walk_forward(table, A_COLUMNS, seasons), table)
            results.append({'H_days': h, 'lambda': lam, **s})
            print(f'v2 H={h} lambda={lam}: log loss {s["log_loss"]:.5f} over {s["games"]} games', flush=True)
    best = min(results, key=lambda r: r['log_loss'])  # min keeps the first of equals
    return {'seasons': list(seasons), 'grid': results, 'chosen': {'H_days': best['H_days'], 'lambda': best['lambda']}}


def measure(v2: Mapping[str, pd.Series], registered: Mapping[str, pd.Series], table: pd.DataFrame) -> dict[str, Any]:
    """MV1 (v2 against each registered model) and MV2 (v2 without availability beside v2), at 95%, on the games
    both forecast. Measurements: no label."""
    out = {}
    for key, cand, inc in (('MV1_model_a', v2['model_a'], registered['model_a']),
                           ('MV1_model_b', v2['model_b'], registered['model_b']),
                           ('MV2', v2['model_a_no_availability'], v2['model_a'])):
        out[key] = backtest.day_block_interval(cand, inc, table, MEASURE_LEVEL)
    return out


def main(get: Callable[[str], bytes] = history.fetch) -> int:
    reg = registry()
    base = backtest.registry()
    p = base['protocol']
    raw, minutes = backtest.load_history(p['training_from_season'], p['confirmation_seasons'][-1])
    market = pd.concat([pd.read_csv(f, dtype={'game_id': str}) for s in range(p['training_from_season'],
                        p['confirmation_seasons'][-1] + 1) if (f := history.HISTORY / f'market_{s}.csv').exists()],
                       ignore_index=True)
    games, unusable, touched = build(raw, minutes, market, lambda gid: espn_slate(gid, get))
    tuning = tune(games, minutes, unusable, base['models']['model_a']['grid'], p['validation_seasons'])
    h, lam = tuning['chosen']['H_days'], tuning['chosen']['lambda']
    seasons = p['confirmation_seasons']
    table = features(games, minutes, h, lam, unusable)
    table['market_logit'] = np.log(table['home_prob'] / (1 - table['home_prob']))
    v2 = {'model_a': walk_forward(table, A_COLUMNS, seasons),
          'model_a_no_availability': walk_forward(table, A_COLUMNS[:2], seasons),
          'model_b': walk_forward(table, [*A_COLUMNS, 'market_logit'], seasons, needs_market=True)}
    reg_conf = json.loads((backtest.RESULTS / 'confirmation.json').read_text(encoding='utf-8'))
    old_games = ratings.prepare(raw)
    old = backtest._table(old_games, minutes, reg_conf['H_days'], reg_conf['lambda'])
    old['market_logit'] = np.log(old['home_prob'] / (1 - old['home_prob']))
    registered = {'model_a': backtest.walk_forward(old, A_COLUMNS, seasons),
                  'model_b': backtest.walk_forward(old, [*A_COLUMNS, 'market_logit'], seasons, needs_market=True)}
    doc = {'registry': 'experiments/nba/stage95_v2/registry.json', 'family': reg['family'], 'touched': touched,
           'tuning': tuning, 'confirmation_seasons': seasons,
           'scores': {f'v2_{k}': scores(s, table) for k, s in v2.items()}
           | {'base_rate': scores(base_rate(table, seasons), table)},
           'measurements': measure(v2, registered, table)}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / 'backtest.json').write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8')
    for k, m in doc['measurements'].items():
        print(f"{k}: {m['diff']:+.5f} [{m['low']:+.5f}, {m['high']:+.5f}] over {m['games']} games (measurement)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
