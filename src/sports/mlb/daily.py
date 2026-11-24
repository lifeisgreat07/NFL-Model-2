"""MLB's daily run (Stage 101 item 3): save each game's pick before it starts, grade the ones that have finished.

`experiments/mlb/stage101/registry.json` is what this carries out. Each run, in order:

1. **History.** The stored seasons (`data/mlb/history/games_<season>.csv` and `pitchers_<season>.csv`) and this
   season's games that have finished since (`refresh_season`): each final game's box score, one at a time, so a box
   not yet settled is retried next run rather than stopping the others. Every stored season is read, checked
   against Retrosheet or not: the registry trains on every final game from 2010, and each pick names the seasons it
   read that are not checked yet (`unchecked_seasons`).
2. **Lock.** `GameLock` (`src/sports/mlb/lock.py`) says which of today's and tomorrow's games (Eastern) must be
   saved now. A held game waits; a started one is never predicted.
3. **Starters.** The Stats API's probable pitchers, read now, for both days (`schedule.DAY`). Every read is kept in
   `data/mlb/starters_<season>.csv` (`starters.append`), for M2. A side with no probable named gets the league rate,
   and the pick stores `named: false` for it.
4. **Market.** For each game to save, its price by the registered order (`src/sports/mlb/market.py`): ESPN, then
   Kalshi only for a game ESPN did not price, else "no price". Every price read is kept in
   `data/mlb/lines/<season>.json`.
5. **Models.** Model A and Model B as Stage 98 registers them, with the settings its validation chose, refitted on
   every final game strictly before the pick's official date. Model B trains on games with a price: past seasons'
   from the market history, read by Stage 98's market rules, and this season's with the price the runs recorded, the
   last read before each started. A neutral-site game's Model A forecast loses the fitted home edge, as in the
   backtest.
6. **Save.** One file per game and official date, `predictions/mlb/<season>/<gamePk>_<official date>.json`,
   written once and never rewritten. A game postponed after its pick was saved keeps that file, never scored; the
   game is picked again under the date it is played.
7. **Grade.** `results/mlb/graded_<season>.json`: a pick is scored only when its game is final on the pick's own
   official date ('Final' or 'Completed Early'); a suspended game keeps its official date, so it is scored once
   completed. A postponed or cancelled game's pick is never counted, and nor is an official tie.
8. **Drift.** `results/mlb/drift_<season>.json` from `src/sports/mlb/drift.py`: regular-season picks only; until the
   confirmation gives the baselines, the file says the check is not running and why.

Every step after the first save is guarded (`src/core/after_save.py`): a failure prints DEGRADED and the run goes on
to commit the picks.

Run by hand: python -m src.sports.mlb.daily
"""
from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.core import (
    after_save,
    pick_guard,
    request_budget,
    schedule_guard,
    season_prices,
)
from src.core.atomic_write import write_json_atomic
from src.core.day_backtest import estimator
from src.core.provenance import code_identity, training
from src.core.sport import GameStatus, sport_paths
from src.sports.mlb import backtest, drift, history, market, ratings, starters
from src.sports.mlb import schedule as mlb_schedule
from src.sports.mlb.lock import GameLock

PATHS = sport_paths('mlb')
CODE_VERSION = 'mlb-stage98'
FIRST_SEASON = 2010
ET = 'America/New_York'

Json = Any


def chosen() -> tuple[float, float, float]:
    """(H_days, lambda, K_outs) as Stage 98's validation chose them."""
    doc = json.loads((backtest.RESULTS / 'tuning.json').read_text(encoding='utf-8'))['chosen']
    return float(doc['H_days']), float(doc['lambda']), float(doc['K_outs'])


def columns(lam: float, k: float) -> list[str]:
    """Model A's two features, as `ratings.features` names them."""
    return [f'run_matchup_{lam:g}', f'starter_matchup_{k:g}']


def stored_history(first: int, last: int, folder: Path = history.HISTORY) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(games, pitcher lines) of every stored season from `first` to `last`."""
    games, lines = [], []
    for s in range(first, last + 1):
        g, p = folder / f'games_{s}.csv', folder / f'pitchers_{s}.csv'
        if g.exists() and p.exists():
            games.append(pd.read_csv(g, dtype={'game_id': str, 'home': str, 'away': str}))
            lines.append(pd.read_csv(p, dtype={'game_id': str, 'pitcher_id': str, 'club': str}))
    empty_g, empty_p = pd.DataFrame(columns=list(history.GAME_FIELDS)), pd.DataFrame(columns=list(history.PITCHER_FIELDS))
    return (pd.concat(games, ignore_index=True) if games else empty_g,
            pd.concat(lines, ignore_index=True) if lines else empty_p)


def unchecked_seasons(first: int, last: int, folder: Path = history.HISTORY) -> list[int]:
    """The stored seasons not yet checked against Retrosheet."""
    path = folder / 'checks.json'
    checked = backtest.checked_seasons(folder) if path.exists() else set()
    return [s for s in range(first, last + 1) if (folder / f'games_{s}.csv').exists() and s not in checked]


def refresh_season(season: int, sched: pd.DataFrame, folder: Path = history.HISTORY,
                   get: Callable[[str], bytes] = history.fetch) -> tuple[pd.DataFrame, pd.DataFrame]:
    """This season's stored games and pitcher lines, plus every final game not stored yet. A box score that cannot be
    read or used yet is left for the next run."""
    gpath, ppath = folder / f'games_{season}.csv', folder / f'pitchers_{season}.csv'
    games = (pd.read_csv(gpath, dtype={'game_id': str, 'home': str, 'away': str}) if gpath.exists()
             else pd.DataFrame(columns=list(history.GAME_FIELDS)))
    lines = (pd.read_csv(ppath, dtype={'game_id': str, 'pitcher_id': str, 'club': str}) if ppath.exists()
             else pd.DataFrame(columns=list(history.PITCHER_FIELDS)))
    finals = sched[sched['status'] == GameStatus.FINAL.value]
    new = []
    for gid in finals.loc[~finals['game_id'].isin(set(games['game_id'])), 'game_id']:
        try:
            new.extend(history.pitcher_rows(json.loads(get(history.BOX.format(gid=gid))), str(gid)))
        except (history.HistoryError, OSError, ValueError) as exc:
            print(f'box score not settled yet, retried next run: {exc}')
    if not new:
        return games, lines
    added = pd.DataFrame(new, columns=list(history.PITCHER_FIELDS))
    new_games = history.game_rows(finals[finals['game_id'].isin(set(added['game_id']))], added)
    games = pd.concat([games, new_games], ignore_index=True).sort_values(['slate', 'game_id'], kind='stable')
    lines = pd.concat([lines, added], ignore_index=True)
    history.write(games, gpath)
    history.write(lines, ppath)
    return games, lines


def fit(table: pd.DataFrame, cols: Sequence[str], priced: bool) -> Any:
    rows = table.dropna(subset=['home_win'])
    if priced:
        rows = rows.dropna(subset=['home_prob'])
    x = rows[list(cols)]
    if priced:
        x = x.assign(market_logit=np.log(rows['home_prob'] / (1 - rows['home_prob'])))
    return estimator().fit(x, rows['home_win'])


def fit_before(table: pd.DataFrame, day: pd.Timestamp, cols: Sequence[str],
               first: int) -> tuple[dict[str, Any], dict[str, Any]]:
    """Model A and Model B fitted on every final game strictly before `day`, the pick's official date, and their
    provenance."""
    before = table[pd.to_datetime(table['day']) < day]
    return {'a': fit(before, cols, False), 'b': fit(before, cols, True)}, training(before, first)


def predict(models: Mapping[str, Any], feats: Mapping[str, float], cols: Sequence[str], neutral: bool,
            home_prob: float | None) -> tuple[float, float | None]:
    """(Model A, Model B or None) home probabilities. Model A loses the fitted home edge on a neutral-site game;
    Model B keeps it, since its price already carries the site (audit 8 S1)."""
    x = pd.DataFrame([dict(feats)])[list(cols)]
    a = models['a']
    z = float(a.decision_function(x)[0])
    if neutral:
        z -= float(a[-1].intercept_[0])
    p_a = 1.0 / (1.0 + np.exp(-z))
    if home_prob is None:
        return float(p_a), None
    xb = x.assign(market_logit=np.log(home_prob / (1 - home_prob)))
    return float(p_a), float(models['b'].predict_proba(xb)[0, 1])


def pick_path(folder: Path, game_id: str, slate: str) -> Path:
    return folder / f'{game_id}_{slate}.json'


def save_once(record: dict[str, Any], folder: Path) -> bool:
    """Write the pick unless one is already saved for its game and official date. True when written. A record that
    could have seen its result is refused first (`src/core/pick_guard.py`)."""
    path = pick_path(folder, record['game_id'], record['slate'])
    if path.exists():
        return False
    pick_guard.refuse_leak(record)
    folder.mkdir(parents=True, exist_ok=True)
    write_json_atomic(path, record, trailing_newline=True, indent=1)
    return True


def starter_side(probable: Any) -> dict[str, Any]:
    return {'id': None if probable is None else str(probable), 'named': probable is not None}


def pick_record(game: Mapping[str, Any], feats: Mapping[str, float], probables: tuple[Any, Any], p_a: float,
                p_b: float | None, price: Mapping[str, Any], now: datetime) -> dict[str, Any]:
    """The saved pick: Model B's side when priced, Model A's otherwise."""
    lead = p_b if p_b is not None else p_a
    return {
        'game_id': str(game['game_id']), 'season': int(game['season']), 'slate': str(game['slate']),
        'game_type': str(game['game_type']), 'game_number': int(game['game_number']),
        'start_utc': pd.Timestamp(game['start_utc']).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'start_time_tbd': bool(game.get('start_time_tbd', False)),
        'home': str(game['home']), 'away': str(game['away']), 'neutral_site': bool(game['neutral_site']),
        'model_a': round(p_a, 4), 'model_b': None if p_b is None else round(p_b, 4),
        'pick': str(game['home']) if lead >= 0.5 else str(game['away']),
        'pick_model': 'model_b' if p_b is not None else 'model_a',
        'market_source': price.get('source'),
        'starters': {'home': starter_side(probables[0]), 'away': starter_side(probables[1])},
        'features': {key: round(float(v), 6) for key, v in feats.items()},
        'market': dict(price), 'saved_utc': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'code': CODE_VERSION,
    }


def read_picks(folder: Path) -> list[dict[str, Any]]:
    return [json.loads(p.read_text(encoding='utf-8')) for p in sorted(folder.glob('*.json'))] if folder.exists() else []


def grade_one(pick: Mapping[str, Any], game: Mapping[str, Any] | None) -> str:
    """'correct', 'wrong', 'postponed', 'cancelled', 'tie' or 'pending' for one saved pick."""
    if game is None:
        return 'pending'
    if game['status'] == GameStatus.CANCELLED.value:
        return 'cancelled'
    if str(game['slate']) != str(pick['slate']) or game['status'] == GameStatus.POSTPONED.value:
        return 'postponed'
    if game['status'] != GameStatus.FINAL.value or pd.isna(game['home_score']):
        return 'pending'
    if pd.isna(game['home_win']):
        return 'tie'
    winner = str(game['home']) if int(game['home_win']) == 1 else str(game['away'])
    return 'correct' if winner == pick['pick'] else 'wrong'


def grade(folder: Path, sched: pd.DataFrame) -> list[dict[str, Any]]:
    """One row per saved pick. Only 'correct' and 'wrong' are scored."""
    by_id = {str(g['game_id']): g for g in sched.to_dict('records')}
    rows = []
    for pick in read_picks(folder):
        game = by_id.get(str(pick['game_id']))
        result = grade_one(pick, game)
        scored = result in ('correct', 'wrong')
        rows.append({'game_id': pick['game_id'], 'slate': pick['slate'], 'game_type': pick.get('game_type'),
                     'start_utc': pick.get('start_utc'), 'home': pick['home'], 'away': pick['away'],
                     'pick': pick['pick'], 'model_a': pick['model_a'], 'model_b': pick['model_b'],
                     'home_win': int(game['home_win']) if scored and game is not None else None,
                     'result': result, 'market_source': pick.get('market_source'),
                     'starters_named': all(s.get('named') for s in (pick.get('starters') or {}).values()),
                     'saved_utc': pick['saved_utc']})
    return rows


def drift_rows(graded: Iterable[Mapping[str, Any]]) -> list[tuple[float | None, int | None, str]]:
    """(Model A's home probability, home won, official date) for every scored regular-season pick, in the order
    their games started."""
    rows = [r for r in graded if r['result'] in ('correct', 'wrong') and r.get('game_type') == 'regular']
    rows.sort(key=lambda r: (str(r.get('start_utc') or ''), str(r['game_id'])))
    return [(r['model_a'], r['home_win'], str(r['slate'])) for r in rows]


def missed(started: Iterable[str], slates: Mapping[str, str], folder: Path) -> list[str]:
    """Started games with no pick saved for their official date."""
    return sorted(g for g in started if not pick_path(folder, g, slates[g]).exists())


def read_json(url: str, get: Callable[[str], bytes], what: str) -> Json | None:
    try:
        return json.loads(get(url))
    except (OSError, ValueError) as exc:
        print(f'DEGRADED: {what}: not read: {exc}')
        return None


def main(now: datetime | None = None, get: Callable[[str], bytes] = history.fetch) -> int:
    now = now or datetime.now(UTC)
    season = mlb_schedule.current_season(now)
    sched = mlb_schedule.load_schedule(season, get=request_budget.Budget().wrap(lambda u: json.loads(get(u))))
    schedule_guard.check(len(sched), PATHS.results / f'schedule_{season}.json')
    h, lam, k = chosen()
    cols = columns(lam, k)
    past_games, past_lines = stored_history(FIRST_SEASON, season - 1)
    cur_games, cur_lines = refresh_season(season, sched, get=get)
    lines_path = PATHS.data / 'lines' / f'{season}.json'
    prices = backtest.load_market(FIRST_SEASON, season - 1).set_index('game_id')['home_prob'].to_dict()
    prices.update(season_prices.read(lines_path))
    games = ratings.prepare(pd.concat([past_games, cur_games], ignore_index=True))
    lines = pd.concat([past_lines, cur_lines], ignore_index=True)
    lines = lines.assign(game_id=lines['game_id'].astype(str), pitcher_id=lines['pitcher_id'].astype(str))
    unchecked = unchecked_seasons(FIRST_SEASON, season)

    today = pd.Timestamp(now).tz_convert(ET).normalize()
    days = [str(today.date()), str((today + pd.Timedelta(days=1)).date())]
    slate = sched[sched['slate'].isin(days)]
    decision = GameLock().decide(slate, now)
    folder = PATHS.predictions / str(season)
    probables: dict[str, tuple[Any, Any]] = {}
    for day in days:
        url = mlb_schedule.DAY.format(day=day)
        data = read_json(url, get, f'probable pitchers for {day}')
        if data is not None:
            probables.update(mlb_schedule.probables(data))
            after_save.guarded('starters record', starters.append, PATHS.data / f'starters_{season}.csv',
                               starters.probable_rows(data, url, now))
    saved_prices: list[dict[str, Any]] = []
    if decision.lock:
        table = ratings.features(games, lines, h, [lam], [k])
        table = table.assign(home_prob=table['game_id'].astype(str).map(prices))
        day_of = pd.Series(games['day'].to_numpy(), index=games['game_id'])
        locking = slate[slate['game_id'].isin(decision.lock)]
        kalshi: dict[Any, Any] | None = None
        kalshi_read = False
        fitted: dict[pd.Timestamp, tuple[dict[str, Any], dict[str, Any]]] = {}
        for day, day_games in locking.groupby('slate', sort=True):
            board = read_json(market.SCOREBOARD.format(day=str(day).replace('-', '')), get, f'ESPN scoreboard {day}')
            matched, unmatched = (market.espn_match(day_games, market.espn_events(board)) if board is not None
                                  else ({}, []))
            for line in unmatched:
                print(f'no ESPN event: {line}')
            pick_day = pd.Timestamp(str(day))
            if pick_day not in fitted:
                fitted[pick_day] = fit_before(table, pick_day, cols, FIRST_SEASON)
            models, trained = fitted[pick_day]
            rated = ratings.day_ratings(games[games['day'] < pick_day], lines, day_of, pick_day, h, lam, k)
            for _, g in day_games.iterrows():
                gid = str(g['game_id'])
                espn = matched.get(gid)
                odds = read_json(market.ESPN_ODDS.format(e=espn[0]), get, f'ESPN odds for {gid}') if espn else None
                if market.espn_price(odds or {}, bool(espn and espn[1])) is None and not kalshi_read:
                    feed = read_json(market.KALSHI, get, 'Kalshi')
                    kalshi, kalshi_read = (market.kalshi_prices(feed) if feed is not None else None), True
                price = market.price_for(g.to_dict(), odds, bool(espn and espn[1]), kalshi if kalshi_read else None,
                                         now)
                saved_prices.append(price)
                pair = probables.get(gid, (None, None))
                feats = rated.matchup(str(g['home']), str(g['away']),
                                      None if pair[0] is None else str(pair[0]),
                                      None if pair[1] is None else str(pair[1]))
                feats = {cols[0]: feats['run_matchup'], cols[1]: feats['starter_matchup']}
                p_a, p_b = predict(models, feats, cols, bool(g['neutral_site']), price.get('home_prob'))
                record = (pick_record(g.to_dict(), feats, pair, p_a, p_b, price, now) | trained
                          | code_identity('mlb') | {'unchecked_seasons': unchecked})
                fresh = save_once(record, folder)
                print(('saved ' if fresh else 'already saved ') + f"{gid} {record['slate']}"
                      + f" (price: {record['market_source'] or 'none'}; starters named: "
                      + f"{record['starters']['home']['named']}/{record['starters']['away']['named']})")
    # From here on the picks are saved, and no step may lose them.
    after_save.guarded('market record', market.record, saved_prices, lines_path)
    PATHS.results.mkdir(parents=True, exist_ok=True)

    def write_grades() -> list[dict[str, Any]]:
        graded = grade(folder, sched)
        write_json_atomic(PATHS.results / f'graded_{season}.json', graded, trailing_newline=True, indent=1)
        return graded

    graded = after_save.guarded('grading', write_grades) or []

    def write_drift() -> None:
        report = drift.check(drift_rows(graded), drift.BASELINE)
        write_json_atomic(PATHS.results / f'drift_{season}.json', report, trailing_newline=True, indent=1)
        if report['flagged']:
            print('DRIFT CHECK: FLAGGED (Model A log loss is significantly above its backtest)')
        elif not report['running']:
            print(f"drift check not running: {report['why']}")

    after_save.guarded('drift check', write_drift)
    lost = missed(decision.started, dict(zip(slate['game_id'].astype(str), slate['slate'].astype(str), strict=True)),
                  folder)
    if lost:
        print(f'MISSED PICKS: {len(lost)} started with no saved pick: {", ".join(lost)}')
    print(f'lock {len(decision.lock)}, hold {len(decision.hold)}, started {len(decision.started)}; '
          f'graded {sum(r["result"] in ("correct", "wrong") for r in graded)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
