"""The NHL's day-sport v2, its history and its backtest (experiments/nhl/stage95_v2/registry.json).

Stage 95 item 35 with Stage 94 items 28 and 29, from audit 7, registered as a shadow before anything here was
fitted. Each change is one function, named for its item:

- 29, `drop_bad_prices`: a price is not used (the game counts as unpriced for Model B) when its two implied
  probabilities sum outside their market's band: [1.00, 1.20] for ESPN's native two-way moneyline (from 2024-25),
  [0.75, 1.00] for the two sides of the three-way regulation line (to 2023-24), whose third outcome is not in the
  sum. `unusable_boxes`: a box score without both teams' shots on goal is not used for the ratings; the game is
  still forecast and scored from the ratings of the games before it;
- 28, `walk_forward`: a neutral-site game gets no home edge: the fitted intercept is not added to its forecast. Its
  row still enters the fit as listed. Which games are neutral is the league's own word: `neutralSite` in its
  schedule feed, read by `src/sports/nhl/schedule.py` (`neutral_ids`). The league flags its outdoor games and
  international games that way, and every game of the 2020 playoffs' two hub cities;
- 35, `tune`: H_days and K_shots over the registered grid, K_shots `None` being the goalie term removed, chosen by
  Model A's pooled log loss on the validation seasons only.

`main` tunes on the validation seasons, then measures v2 against the registered models on the confirmation seasons
(MV1). It is a measurement: those seasons have been seen, and nothing here decides anything. The decision is the
live forward test's, once, after the regular season (the registration's V1 and V2).

Run with: python -m src.sports.nhl.v2 (with NHL_CACHE set, the league's schedules are read from disk)
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

from . import backtest, history, ratings
from . import schedule as nhl_schedule
from .market import implied

PATHS = sport_paths('nhl')
FOLDER = PATHS.experiments / 'stage95_v2'
REGISTRY = FOLDER / 'registry.json'
RESULTS = FOLDER / 'results'
#: Item 29's bands on the two implied probabilities' sum: the native two-way line, and the three-way line's two sides.
TWO_WAY_SUM = (1.00, 1.20)
THREE_WAY_SUM = (0.75, 1.00)
#: Item 35's grid. None is the goalie term removed.
GRID: dict[str, list[Any]] = {'H_days': [60, 120, 240], 'K_shots': [1000, 2000, 4000, 8000, 16000, None]}
#: MV1 is reported at 95%; it decides nothing, so it spends no alpha.
MEASURE_LEVEL = 0.95
TEAM_COLUMNS = ['goal_matchup', 'shot_matchup']


def registry() -> dict[str, Any]:
    reg: dict[str, Any] = json.loads(REGISTRY.read_text(encoding='utf-8'))
    return reg


def drop_bad_prices(market: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Item 29: the prices whose two implied probabilities sum within their line's band, and the ids of the rest.
    `converted` marks a price read from the three-way regulation line."""
    total = market['home_price'].map(implied) + market['away_price'].map(implied)
    three = market['converted'].astype(bool)
    lo = np.where(three, THREE_WAY_SUM[0], TWO_WAY_SUM[0])
    hi = np.where(three, THREE_WAY_SUM[1], TWO_WAY_SUM[1])
    ok = (total >= lo) & (total <= hi)
    return market[ok].copy(), sorted(market.loc[~ok, 'game_id'].astype(str))


def unusable_boxes(box: pd.DataFrame) -> set[str]:
    """Item 29: the games whose box score lacks either team's shots on goal."""
    return set(box.loc[box['home_sog'].isna() | box['away_sog'].isna(), 'game_id'].astype(str))


def neutral_ids(seasons: Iterable[int], load: Callable[[int], pd.DataFrame] = nhl_schedule.load_schedule) -> set[str]:
    """Item 28: the games the league's schedule feed marks neutral-site."""
    out: set[str] = set()
    for s in seasons:
        sched = load(s)
        out |= set(sched.loc[sched['neutral_site'].astype(bool), 'game_id'].astype(str))
    return out


def goalie_column(k: float) -> str:
    return backtest.goalie_column(k)


def model_a_columns(k: float | None) -> list[str]:
    return TEAM_COLUMNS if k is None else [*TEAM_COLUMNS, goalie_column(k)]


def features(games: pd.DataFrame, half_life: float, ks: Iterable[float],
             unusable: AbstractSet[str] = frozenset()) -> pd.DataFrame:
    """`ratings.features`, except item 29: a game in `unusable` is never in the ratings' training rows. It is still
    a row here, forecast from the games before its day."""
    ks = list(ks)
    usable = games[~games['game_id'].astype(str).isin(unusable)]
    out = []
    for day in sorted(games['day'].unique()):
        day = pd.Timestamp(day)
        train = usable[usable['day'] < day]
        if len(train) < 100:
            continue
        rated = ratings.day_ratings(train, day, half_life)
        for g in games[games['day'] == day].itertuples():
            row: dict[str, object] = {'game_id': g.game_id, 'day': day, 'season': g.season,
                                      'game_type': g.game_type, 'home': g.home, 'away': g.away,
                                      'home_win': g.home_win}
            row.update(rated.matchup(g.home, g.away, g.home_goalie_id, g.away_goalie_id, ks))
            out.append(row)
    return pd.DataFrame(out)


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
        z = np.where(neutral, z - float(model[-1].intercept_[0]), z)
        preds.update(zip(today['game_id'], 1.0 / (1.0 + np.exp(-z))))
    return pd.Series(preds, name='p')


def build(box: pd.DataFrame, market: pd.DataFrame, neutral: AbstractSet[str]
          ) -> tuple[pd.DataFrame, set[str], dict[str, Any]]:
    """v2's history: item 29 on the prices and the boxes, item 28's flag on the games. Returns the prepared games
    (with `home_prob` where a usable price exists, and `neutral_site`), the boxes not used, and what each rule
    touched."""
    prices, bad = drop_bad_prices(market)
    games = box.drop(columns=['home_prob'], errors='ignore').merge(
        prices[['game_id', 'home_prob']], on='game_id', how='left')
    games['neutral_site'] = games['game_id'].astype(str).isin(neutral)
    unusable = unusable_boxes(games)
    touched = {'prices_not_used': bad, 'boxes_not_used': sorted(unusable),
               'neutral_games': sorted(set(games.loc[games['neutral_site'], 'game_id'].astype(str)))}
    return ratings.prepare(games), unusable, touched


def table_for(games: pd.DataFrame, h: float, ks: Iterable[float], unusable: AbstractSet[str]) -> pd.DataFrame:
    return features(games, h, [k for k in ks if k is not None], unusable).merge(
        games[['game_id', 'home_prob', 'neutral_site']], on='game_id', how='left')


def tune(games: pd.DataFrame, unusable: AbstractSet[str], grid: Mapping[str, Sequence[Any]],
         seasons: Sequence[int]) -> dict[str, Any]:
    """H and K over the registered grid by Model A's pooled log loss on the validation seasons only; no game after
    the last validation season is read."""
    games = games[games['season'] <= max(seasons)]
    results = []
    for h in grid['H_days']:
        table = table_for(games, h, grid['K_shots'], unusable)
        for k in grid['K_shots']:
            s = scores(walk_forward(table, model_a_columns(k), seasons), table)
            results.append({'H_days': h, 'K_shots': k, **s})
            print(f'v2 H={h} K={k}: log loss {s["log_loss"]:.5f} over {s["games"]} games', flush=True)
    best = min(results, key=lambda r: r['log_loss'])  # min keeps the first of equals
    return {'seasons': list(seasons), 'grid': results, 'chosen': {'H_days': best['H_days'], 'K_shots': best['K_shots']}}


def measure(v2: Mapping[str, pd.Series], registered: Mapping[str, pd.Series], table: pd.DataFrame) -> dict[str, Any]:
    """MV1, v2 against each registered model at 95% on the games both forecast. A measurement: no label."""
    return {f'MV1_{key}': backtest.day_block_interval(v2[key], registered[key], table, MEASURE_LEVEL)
            for key in ('model_a', 'model_b')}


def main(load: Callable[[int], pd.DataFrame] = nhl_schedule.load_schedule) -> int:
    reg = registry()
    base = backtest.registry()
    p = base['protocol']
    first, last = p['training_from_season'], p['confirmation_seasons'][-1]
    box = backtest.load_history(first, last)
    market = pd.concat([pd.read_csv(f, dtype={'game_id': str}) for s in range(first, last + 1)
                        if (f := history.HISTORY / f'market_{s}.csv').exists()], ignore_index=True)
    games, unusable, touched = build(box, market, neutral_ids(range(first, last + 1), load))
    tuning = tune(games, unusable, GRID, p['validation_seasons'])
    h, k = tuning['chosen']['H_days'], tuning['chosen']['K_shots']
    seasons = p['confirmation_seasons']
    table = table_for(games, h, [k], unusable)
    table['market_logit'] = np.log(table['home_prob'] / (1 - table['home_prob']))
    a_cols = model_a_columns(k)
    v2 = {'model_a': walk_forward(table, a_cols, seasons),
          'model_b': walk_forward(table, [*a_cols, 'market_logit'], seasons, needs_market=True)}
    reg_conf = json.loads((backtest.RESULTS / 'confirmation.json').read_text(encoding='utf-8'))
    old_games = ratings.prepare(box)
    rk = reg_conf['K_shots']
    old = ratings.features(old_games, reg_conf['H_days'], [rk]).merge(
        old_games[['game_id', 'home_prob']], on='game_id', how='left')
    old['market_logit'] = np.log(old['home_prob'] / (1 - old['home_prob']))
    old_cols = [*TEAM_COLUMNS, goalie_column(rk)]
    registered = {'model_a': backtest.walk_forward(old, old_cols, seasons),
                  'model_b': backtest.walk_forward(old, [*old_cols, 'market_logit'], seasons, needs_market=True)}
    doc = {'registry': 'experiments/nhl/stage95_v2/registry.json', 'family': reg['family'], 'touched': touched,
           'tuning': tuning, 'confirmation_seasons': seasons,
           'scores': {f'v2_{key}': scores(s, table) for key, s in v2.items()}
           | {'base_rate': scores(base_rate(table, seasons), table)},
           'measurements': measure(v2, registered, table)}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / 'backtest.json').write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8')
    for key, m in doc['measurements'].items():
        print(f"{key}: {m['diff']:+.5f} [{m['low']:+.5f}, {m['high']:+.5f}] over {m['games']} games (measurement)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
