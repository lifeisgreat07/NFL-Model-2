"""The March Madness backtest (Stage 103 item 2), as `experiments/ncaam/stage103/registry.json` fixes it.

The tuning: the registered grid is searched on the validation seasons, by Model A's log loss over their games
from 1 January on, walking forward a game day at a time.

The confirmation: on the 2021 to 2026 tournaments, with the tuned settings fixed, every game of a tournament is
forecast from before its first game (the lock), by Model A and by the seed model, and compared with each other
and with the market: H1, H2, M1 and M2.

Run by hand: python -m src.sports.ncaam.backtest            (tuning; writes results/tuning.json once)
             python -m src.sports.ncaam.backtest confirm    (confirmation; writes results/confirmation.json once)
"""
from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.day_backtest import label, log_losses
from src.core.forward_test import interval
from src.core.sport import sport_paths
from src.sports.ncaam import market, ratings
from src.sports.ncaam.collector import HISTORY, CollectorError

PATHS = sport_paths('ncaam')
FOLDER = PATHS.experiments / 'stage103'
REGISTRY = FOLDER / 'registry.json'
RESULTS = FOLDER / 'results'
#: The registered bootstrap seed (protocol.bootstrap).
SEED = 20261115


def registry() -> dict[str, Any]:
    reg: dict[str, Any] = json.loads(REGISTRY.read_text(encoding='utf-8'))
    return reg


def checked_seasons(folder: Path = HISTORY) -> set[int]:
    path = folder / 'checks.json'
    if not path.exists():
        return set()
    doc = json.loads(path.read_text(encoding='utf-8'))
    return {int(s) for s, c in doc.items() if c['checked']}


def load_history(first: int, last: int, folder: Path = HISTORY) -> pd.DataFrame:
    """Seasons `first` to `last`. Raises if any of them has not passed the fallback check."""
    unchecked = sorted(set(range(first, last + 1)) - checked_seasons(folder))
    if unchecked:
        raise CollectorError(f'seasons not checked against the fallback, so not used: {unchecked}')
    return ratings.load(first, last, folder)


def walk_forward(table: pd.DataFrame) -> pd.Series:
    """Model A's probability for every row of `table` (ratings.margins' output) that has an earlier row: before
    each game day the curve is refitted on every row strictly earlier. The first day has no earlier row and is
    not forecast."""
    preds: dict[str, float] = {}
    for day in sorted(table['day'].unique()):
        train = table[table['day'] < day]
        if train.empty:
            continue
        today = table[table['day'] == day]
        coef = ratings.slope(train['walk'].to_numpy(float), train['home_win'].to_numpy())
        preds.update(zip(today['game_id'], ratings.prob(coef, today['walk'].to_numpy(float))))
    return pd.Series(preds, name='p', dtype=float)


def scores(p: pd.Series, table: pd.DataFrame) -> dict[str, float]:
    y = table.set_index('game_id').loc[p.index, 'home_win'].to_numpy(float)
    q = p.to_numpy(float)
    return {'games': int(len(q)), 'log_loss': float(log_losses(q, y).mean()),
            'brier': float(((q - y) ** 2).mean()), 'accuracy': float(((q > 0.5) == (y == 1)).mean())}


def tune(games: pd.DataFrame, reg: dict[str, Any]) -> dict[str, Any]:
    """Every grid entry's scores on `games` (the validation seasons), and the entry with the lowest log loss,
    ties to the earlier entry."""
    grid = reg['models']['model_a']['grid']
    results = []
    for h in grid['H_days']:
        for lam in grid['lambda']:
            table = ratings.margins(games, h, lam)
            s = scores(walk_forward(table), table)
            results.append({'H_days': h, 'lambda': lam, **s})
            print(f'H={h} lambda={lam}: log loss {s["log_loss"]:.5f} over {s["games"]} games', flush=True)
    best = min(results, key=lambda r: r['log_loss'])  # min keeps the first of equals
    return {'seasons': sorted(int(s) for s in games['season'].unique()), 'grid': results,
            'chosen': {'H_days': best['H_days'], 'lambda': best['lambda']}}


def validation_seasons(reg: dict[str, Any]) -> list[int]:
    """A tournament is named by the year it is played; its season starts the year before."""
    return [t - 1 for t in reg['protocol']['validation_tournaments']]


def seeds(seasons: Sequence[int], folder: Path = HISTORY) -> pd.DataFrame:
    """Each stored tournament game's two seeds and `seed_difference`, the away club's seed minus the home club's."""
    frames = [pd.read_csv(folder / f'seeds_{s}.csv', dtype={'game_id': str}) for s in seasons
              if (folder / f'seeds_{s}.csv').exists()]
    df = pd.concat(frames, ignore_index=True)
    home, away = df['home_seed'].astype(int), df['away_seed'].astype(int)
    return pd.DataFrame({'game_id': df['game_id'], 'home_seed': home, 'away_seed': away,
                         'seed_difference': (away - home).astype(float)})


def lock_forecasts(table: pd.DataFrame, seeded: pd.DataFrame, tournaments: Sequence[int]) -> dict[str, pd.Series]:
    """Model A's and the seed model's probability for every game of each tournament, frozen before its first
    game: Model A's curve is fitted on the curve rows strictly before that day and applied to the locked margins;
    the seed model learns from the stored tournaments before this one. A tournament is named by the year it is
    played."""
    games = table[table['tournament']].merge(seeded, on='game_id', how='left')
    unseeded = games.loc[games['seed_difference'].isna(), 'game_id']
    if len(unseeded):
        raise CollectorError(f'tournament games with no seeds: {sorted(unseeded)}')
    model_a: dict[str, float] = {}
    seed_model: dict[str, float] = {}
    for t in tournaments:
        mine = games[games['season'] == t - 1]
        earlier = games[games['season'] < t - 1]
        if mine.empty or earlier.empty:
            raise CollectorError(f'the {t} tournament needs its own games and an earlier tournament in the history')
        rows = table[table['day'] < mine['day'].min()]
        coef = ratings.slope(rows['walk'].to_numpy(float), rows['home_win'].to_numpy())
        model_a.update(zip(mine['game_id'], ratings.prob(coef, mine['lock'].to_numpy(float))))
        s_coef = ratings.slope(earlier['seed_difference'].to_numpy(float), earlier['home_win'].to_numpy())
        seed_model.update(zip(mine['game_id'], ratings.prob(s_coef, mine['seed_difference'].to_numpy(float))))
    return {'model_a': pd.Series(model_a, name='p', dtype=float),
            'seed_model': pd.Series(seed_model, name='p', dtype=float)}


def day_block_interval(a: pd.Series, b: pd.Series, table: pd.DataFrame, level: float) -> dict[str, Any]:
    """Mean log loss of (a - b) on the games both forecast, with the registered bootstrap: paired, whole game
    days, 5,000 resamples, the registered seed."""
    common = a.index.intersection(b.index)
    t = table.set_index('game_id').loc[common]
    y = t['home_win'].to_numpy(float)
    diff = log_losses(a.loc[common].to_numpy(float), y) - log_losses(b.loc[common].to_numpy(float), y)
    return interval(diff, t['day'].to_numpy(), SEED, level)


def confirm(games: pd.DataFrame, prices: pd.DataFrame, seeded: pd.DataFrame, reg: dict[str, Any],
            chosen: dict[str, Any]) -> dict[str, Any]:
    """H1, H2, M1 and M2 on the confirmation tournaments, with the tuned settings fixed and every forecast locked
    before its tournament's first game."""
    p = reg['protocol']
    tournaments = p['confirmation_tournaments']
    level = round(1 - p['alpha'] / p['budget_m'], 4)
    table = ratings.margins(games, chosen['H_days'], chosen['lambda'])
    preds = lock_forecasts(table, seeded, tournaments)
    scored = table[table['tournament'] & table['season'].isin([t - 1 for t in tournaments])]
    priced = prices[prices['game_id'].isin(scored['game_id'])]
    preds['market'] = pd.Series(priced['home_prob'].to_numpy(float), index=priced['game_id'], name='p')
    out: dict[str, Any] = {'tournaments': tournaments, 'H_days': chosen['H_days'], 'lambda': chosen['lambda'],
                           'scores': {name: scores(s, table) for name, s in preds.items()}, 'questions': {}}
    pairs = {'H1': ('model_a', 'seed_model'), 'H2': ('model_a', 'market'), 'M1': ('market', 'seed_model')}
    for hid, (cand, inc) in pairs.items():
        iv = day_block_interval(preds[cand], preds[inc], table, level)
        entry: dict[str, Any] = {'candidate': cand, 'incumbent': inc, **iv}
        if hid != 'M1':
            entry['label'] = label(iv)
        out['questions'][hid] = entry
    # M2: how often each picks the winner, on games between different seeds. Accuracy never decides.
    unequal = scored.merge(seeded, on='game_id')
    unequal = unequal[unequal['home_seed'] != unequal['away_seed']].set_index('game_id')
    won = unequal['home_win'] == 1
    m2: dict[str, Any] = {'games': int(len(unequal)),
                          'higher_seed': float(((unequal['home_seed'] < unequal['away_seed']) == won).mean())}
    for name in ('model_a', 'market'):
        s = preds[name][preds[name].index.isin(unequal.index)]
        m2[name] = float(((s > 0.5) == won.loc[s.index]).mean())
        m2[f'{name}_games'] = int(len(s))
    out['questions']['M2'] = m2
    return out


def main_confirm() -> int:
    """The confirmation, once: a result on file is never overwritten, the setting must be an entry of the
    registered grid, every confirmation season needs its market file, and every provider in those files must be
    classified by the registration."""
    reg = registry()
    p = reg['protocol']
    if (RESULTS / 'confirmation.json').exists():
        raise SystemExit('results/confirmation.json exists: the confirmation is run once and never rewritten')
    chosen = json.loads((RESULTS / 'tuning.json').read_text(encoding='utf-8'))['chosen']
    grid = reg['models']['model_a']['grid']
    if chosen['H_days'] not in grid['H_days'] or chosen['lambda'] not in grid['lambda']:
        raise SystemExit(f'tuning.json chose {chosen}, which is not in the registered grid')
    seasons = [t - 1 for t in p['confirmation_tournaments']]
    try:
        prices, unclassified = market.load(seasons, reg['data']['books'], reg['data']['not_books'])
    except FileNotFoundError as exc:
        raise SystemExit(f'a confirmation season has no market file: {exc}') from exc
    if unclassified:
        raise SystemExit(f'providers the registration does not classify, so an amendment is needed: {unclassified}')
    games = load_history(p['training_from_season'], max(seasons))
    seeded = seeds(range(p['training_from_season'], max(seasons) + 1))
    result = confirm(games, prices, seeded, reg, chosen)
    (RESULTS / 'confirmation.json').write_text(json.dumps(result, indent=1) + '\n', encoding='utf-8')
    for hid, q in result['questions'].items():
        if hid == 'M2':
            print(f"M2: higher seed {q['higher_seed']:.4f}, Model A {q['model_a']:.4f}, market {q['market']:.4f} "
                  f"over {q['games']} games", flush=True)
        else:
            print(f"{hid}: {q['candidate']} - {q['incumbent']} = {q['diff']:+.5f} "
                  f"[{q['low']:+.5f}, {q['high']:+.5f}] {q.get('label', '(measurement)')}", flush=True)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ['confirm']:
        return main_confirm()
    if args:
        raise SystemExit('usage: python -m src.sports.ncaam.backtest [confirm]')
    if (RESULTS / 'tuning.json').exists():
        raise SystemExit('results/tuning.json exists: the tuning is run once and never rewritten')
    reg = registry()
    seasons = validation_seasons(reg)
    if min(seasons) != reg['protocol']['training_from_season']:
        raise SystemExit('the validation seasons no longer start where the history does')
    tuning = tune(load_history(min(seasons), max(seasons)), reg)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / 'tuning.json').write_text(json.dumps(tuning, indent=1) + '\n', encoding='utf-8')
    print(f"chosen: H {tuning['chosen']['H_days']}, lambda {tuning['chosen']['lambda']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
