"""The NBA's daily run (Stage 65): save each game's pick before it starts,
grade the ones that have finished.

`experiments/nba/stage65/registry.json` is what this carries out. Each run,
in order:

1. **History.** Reads the stored seasons (`data/nba/history/`) and adds
   this season's games that have finished since (`refresh_season`): each
   final game's ESPN box score, one game at a time, so a box score not yet
   settled is retried next run rather than stopping the others.
2. **Lock.** Asks `GameLock` which of today's and tomorrow's games must be
   saved now. Nothing else is predicted: a held game waits for a later run,
   a started one is never predicted.
3. **Inputs.** For each game to save: the market price in the registered
   order (`src/sports/nba/market.py`: ESPN, then Kalshi only for a game
   ESPN did not price, then "no price"), and ESPN's injury report for the
   availability term (`src/sports/nba/injuries.py`). An unreadable report
   means both models run without the availability term, refitted the same
   way without it, and the pick says so.
4. **Models.** Model A and Model B as registered in Stage 61, with the
   half-life and ridge strength its validation chose, fitted on every final
   game from 2015-16 on (Model B on those with a market price).
5. **Save.** One file per game, `predictions/nba/<season>/<game_id>.json`,
   written once and never rewritten.
6. **Grade.** Every saved pick whose game is final is scored; a cancelled
   game is marked cancelled and never counted (`results/nba/graded_<season>.json`).
7. **Page inputs.** The season's schedule as ESPN lists it now, for the
   board (`src/sports/nba/page_inputs.py`), written every run.
8. **Drift.** Model A's per-game log loss against the registered baseline
   (`results/nba/drift_<season>.json`); a flag prints a line the workflow
   turns into an alert.

Run by hand: python -m src.sports.nba.daily
"""
from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.core.provenance import training
from src.core.sport import GameStatus, sport_paths
from src.sports.nba import (
    backtest,
    drift,
    history,
    injuries,
    market,
    page_inputs,
    ratings,
)
from src.sports.nba import schedule as nba_schedule
from src.sports.nba.lock import GameLock

PATHS = sport_paths('nba')
CODE_VERSION = 'nba-stage61'
A_COLUMNS = list(backtest.A_COLUMNS)
NO_AVAIL = A_COLUMNS[:2]

Json = Any


def chosen() -> tuple[float, float]:
    """The half-life and ridge strength Stage 61's validation chose."""
    doc = json.loads((backtest.RESULTS / 'tuning.json').read_text(encoding='utf-8'))
    return float(doc['chosen']['H_days']), float(doc['chosen']['lambda'])


def refresh_season(season: int, sched: pd.DataFrame, folder: Path = history.HISTORY,
                   get: Callable[[str], bytes] = history.fetch) -> tuple[pd.DataFrame, pd.DataFrame]:
    """This season's stored games and minutes, plus any final game not
    stored yet. A game whose box score cannot be read yet is left for the
    next run."""
    gpath, mpath = folder / f'games_{season}.csv', folder / f'minutes_{season}.csv'
    games = (pd.read_csv(gpath, dtype={'game_id': str}) if gpath.exists()
             else pd.DataFrame(columns=list(history.GAME_FIELDS)))
    minutes = (pd.read_csv(mpath, dtype={'game_id': str, 'player_id': str}) if mpath.exists()
               else pd.DataFrame(columns=list(history.MINUTE_FIELDS)))
    finals = sched[sched['status'] == GameStatus.FINAL.value]
    missing = finals[~finals['game_id'].isin(set(games['game_id']))]
    new_g, new_m = [], []
    for gid in missing['game_id']:
        try:
            g, m, skipped = history.boxscores(season, get=get, schedule=missing[missing['game_id'] == gid], pause=0)
        except (history.HistoryError, OSError, ValueError) as exc:
            print(f'box score not settled yet, retried next run: {exc}')
            continue
        for note in skipped:
            print(f'box score empty, retried next run: {note}')
        new_g.append(g)
        new_m.append(m)
    if not any(len(g) for g in new_g):
        return games, minutes
    games = pd.concat([games, *new_g], ignore_index=True).sort_values(['slate', 'game_id'], kind='stable')
    minutes = pd.concat([minutes, *new_m], ignore_index=True)
    history.write(games, gpath)
    history.write(minutes, mpath)
    return games, minutes


def fit(table: pd.DataFrame, columns: Sequence[str], priced: bool) -> Any:
    rows = table.dropna(subset=['home_prob']) if priced else table
    x = rows[list(columns)]
    if priced:
        x = x.assign(market_logit=np.log(rows['home_prob'] / (1 - rows['home_prob'])))
    return backtest.estimator().fit(x, rows['home_win'])


def fit_models(table: pd.DataFrame) -> dict[str, Any]:
    """Model A and Model B, each with and without the availability term."""
    return {'a': fit(table, A_COLUMNS, False), 'b': fit(table, A_COLUMNS, True),
            'a_no_availability': fit(table, NO_AVAIL, False), 'b_no_availability': fit(table, NO_AVAIL, True)}


def availability_for(minutes: pd.DataFrame, day_of: dict[str, pd.Timestamp], team: str, day: pd.Timestamp,
                     h: float, out: set[str]) -> float:
    """The share of the team's expected minutes whose players are not listed Out."""
    expected = ratings.expected_minutes(minutes, day_of, team, day, h)
    return ratings.availability(expected, [p for p in expected if p not in out])


def pick_record(game: pd.Series, feats: dict[str, float], models: dict[str, Any], price: dict[str, Any],
                avail: dict[str, Any] | None, injury_list: dict[str, Any] | None, now: datetime) -> dict[str, Any]:
    """The saved pick. `avail` is None when the injury report was not read:
    both models then run without the availability term, and the pick says so."""
    cols = A_COLUMNS if avail is not None else NO_AVAIL
    suffix = '' if avail is not None else '_no_availability'
    x = pd.DataFrame([feats])[cols]
    p_a = float(models['a' + suffix].predict_proba(x)[0, 1])
    p_b = None
    if price.get('source') is not None:
        xb = x.assign(market_logit=np.log(price['home_prob'] / (1 - price['home_prob'])))
        p_b = float(models['b' + suffix].predict_proba(xb)[0, 1])
    lead = p_b if p_b is not None else p_a
    return {
        'game_id': str(game['game_id']), 'season': int(game['season']), 'slate': str(game['slate']),
        'start_utc': pd.Timestamp(game['start_utc']).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'home': game['home'], 'away': game['away'],
        'model_a': round(p_a, 4), 'model_b': None if p_b is None else round(p_b, 4),
        'pick': game['home'] if lead >= 0.5 else game['away'],
        'pick_model': 'model_b' if p_b is not None else 'model_a',
        'market_source': price.get('source'),
        'availability': avail if avail is not None else {'read': False,
                                                         'note': 'injury report not read; both models ran without availability'},
        'features': {key: round(float(v), 6) for key, v in feats.items() if key in cols},
        'market': price, 'injuries': injury_list,
        'saved_utc': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'code': CODE_VERSION,
    }


def save_once(record: dict[str, Any], folder: Path) -> bool:
    """Write the pick unless one is already saved. True when written."""
    path = folder / f"{record['game_id']}.json"
    if path.exists():
        return False
    folder.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(record, indent=1) + '\n', encoding='utf-8')
    tmp.replace(path)
    return True


def missed(started: tuple[str, ...] | list[str], folder: Path) -> list[str]:
    """Games of this slate that have started with no pick saved for them.

    A pick is written once, before its game, so one of these can never be
    made now; the daily workflow raises an alert on the line main prints
    (Stage 68 item 3, the 2026-10-09 audit)."""
    return sorted(str(g) for g in started if not (folder / f'{g}.json').exists())


def missed_line(started: tuple[str, ...] | list[str], folder: Path) -> str | None:
    """The line the workflow's alert step greps for, or None when nothing
    was missed."""
    lost = missed(started, folder)
    return f'MISSED PICKS: {len(lost)} started with no saved pick: {", ".join(lost)}' if lost else None


def grade(folder: Path, sched: pd.DataFrame) -> list[dict[str, Any]]:
    """One row per saved pick: correct, wrong, cancelled, or pending."""
    by_id = sched.set_index('game_id')
    rows = []
    for path in sorted(folder.glob('*.json')) if folder.exists() else []:
        pick = json.loads(path.read_text(encoding='utf-8'))
        g = by_id.loc[pick['game_id']] if pick['game_id'] in by_id.index else None
        status = None if g is None else g['status']
        if status == GameStatus.CANCELLED.value:
            result = 'cancelled'
        elif status == GameStatus.FINAL.value:
            assert g is not None
            winner = g['home'] if int(g['home_win']) == 1 else g['away']
            result = 'correct' if pick['pick'] == winner else 'wrong'
        else:
            result = 'pending'
        rows.append({'game_id': pick['game_id'], 'pick': pick['pick'], 'result': result,
                     'market_source': pick.get('market_source'), 'saved_utc': pick.get('saved_utc')})
    return rows


def drift_rows(folder: Path, sched: pd.DataFrame) -> list[tuple[float | None, int | None]]:
    """(Model A's home probability, home won) for every saved pick whose game is final."""
    finals = sched[sched['status'] == GameStatus.FINAL.value].set_index('game_id')
    rows: list[tuple[float | None, int | None]] = []
    for path in sorted(folder.glob('*.json')) if folder.exists() else []:
        pick = json.loads(path.read_text(encoding='utf-8'))
        if pick['game_id'] in finals.index:
            rows.append((pick.get('model_a'), int(finals.loc[pick['game_id'], 'home_win'])))
    return rows


def read_injuries(get: Callable[[str], bytes], teams: set[str]) -> list[dict[str, str]] | None:
    """The injury report's rows, or None when it cannot be read as registered."""
    try:
        return injuries.parse(json.loads(get(injuries.SOURCE)), teams)
    except (injuries.InjurySourceError, OSError, ValueError) as exc:
        print(f'injuries: not read, picks made without availability: {exc}')
        return None


def read_espn_odds(gid: str, get: Callable[[str], bytes]) -> Json | None:
    try:
        return json.loads(get(market.ESPN_ODDS.format(e=gid)))
    except (OSError, ValueError) as exc:
        print(f'ESPN odds for {gid}: not read: {exc}')
        return None


def read_kalshi(get: Callable[[str], bytes]) -> dict[Any, Any] | None:
    try:
        return market.kalshi_prices(json.loads(get(market.KALSHI)))
    except (OSError, ValueError) as exc:
        print(f'Kalshi: not read: {exc}')
        return None


def main(now: datetime | None = None, get: Callable[[str], bytes] = history.fetch) -> int:
    now = now or datetime.now(UTC)
    season = nba_schedule.current_season(now)
    sched = nba_schedule.load_schedule(season, get=lambda u: json.loads(get(u)))
    first = backtest.registry()['protocol']['training_from_season']
    past_games, past_minutes = backtest.load_history(first, season - 1)
    cur_games, cur_minutes = refresh_season(season, sched, get=get)
    cur_games = cur_games.assign(home_prob=np.nan)
    games = ratings.prepare(pd.concat([past_games, cur_games], ignore_index=True))
    minutes = pd.concat([past_minutes, cur_minutes], ignore_index=True)
    minutes = minutes.assign(game_id=minutes['game_id'].astype(str), player_id=minutes['player_id'].astype(str))
    h, lam = chosen()

    today = pd.Timestamp(now).tz_convert('America/New_York').normalize()
    days = {str(today.date()), str((today + pd.Timedelta(days=1)).date())}
    slate = sched[sched['slate'].isin(days)]
    decision = GameLock().decide(slate, now)
    folder = PATHS.predictions / str(season)
    if decision.lock:
        avail_table = ratings.availability_table(games, minutes, h)
        table = ratings.features(games, minutes, h, lam, avail=avail_table)
        table = table.merge(games[['game_id', 'home_prob']], on='game_id', how='left')
        models = fit_models(table)
        trained = training(table, first)
        teams = set(sched['home']) | set(sched['away'])
        report = read_injuries(get, teams)
        locking = slate[slate['game_id'].isin(decision.lock)]
        day_of = dict(zip(games['game_id'], games['day']))
        kalshi: dict[Any, Any] | None = None
        kalshi_read = False
        prices = []
        for _, g in locking.iterrows():
            odds = read_espn_odds(str(g['game_id']), get)
            if market.espn_price(odds or {}) is None and not kalshi_read:
                kalshi, kalshi_read = read_kalshi(get), True
            price = market.price_for(g.to_dict() | {'start_utc': pd.Timestamp(g['start_utc']).strftime(
                '%Y-%m-%dT%H:%M:%SZ')}, odds, kalshi if kalshi_read else None, now)
            prices.append(price)
            day = pd.Timestamp(str(g['slate']))
            rated = ratings.day_ratings(games[games['day'] < day], day, h, lam)
            feats: dict[str, float] = dict(rated.matchup(g['home'], g['away']))
            avail = None
            injury_list = None
            if report is not None:
                ah = availability_for(minutes, day_of, g['home'], day, h, injuries.out_ids(report, g['home']))
                aa = availability_for(minutes, day_of, g['away'], day, h, injuries.out_ids(report, g['away']))
                feats['availability_matchup'] = ah - aa
                avail = {'read': True, 'home': round(ah, 4), 'away': round(aa, 4)}
                injury_list = injuries.for_game(report, g['home'], g['away'], now)
            record = pick_record(g, feats, models, price, avail, injury_list, now) | trained
            print(('saved ' if save_once(record, folder) else 'already saved ') + record['game_id']
                  + f" (price: {record['market_source'] or 'none'})")
        market.record(prices, PATHS.data / 'lines' / f'{season}.json')
    graded = grade(folder, sched)
    PATHS.results.mkdir(parents=True, exist_ok=True)
    page_inputs.write(PATHS.results / f'schedule_{season}.json', page_inputs.schedule_json(sched, str(today.date())))
    (PATHS.results / f'graded_{season}.json').write_text(json.dumps(graded, indent=1) + '\n', encoding='utf-8')
    spec = drift.baseline()
    losses = drift.per_game_log_loss(drift_rows(folder, sched))
    flagged = drift.flags(losses, spec)
    (PATHS.results / f'drift_{season}.json').write_text(json.dumps(
        {'games': len(losses), 'mean_log_loss': (sum(losses) / len(losses)) if losses else None,
         'baseline': spec['baseline']['value'], 'flagged': flagged}, indent=1) + '\n', encoding='utf-8')
    if flagged:
        print('DRIFT CHECK: FLAGGED (Model A log loss is significantly above its backtest)')
    lost = missed_line(decision.started, folder)
    if lost:
        print(lost)
    print(f'lock {len(decision.lock)}, hold {len(decision.hold)}, started {len(decision.started)}; '
          f'graded {sum(r["result"] in ("correct", "wrong") for r in graded)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
