"""The NHL's daily run (Stage 58): save each game's pick before it starts, grade
the ones that have finished.

Each run, in order:

1. **History.** Reads the stored box scores (`data/nhl/history/`) and adds
   any of this season's games that have finished since (`refresh_season`).
2. **Lock.** Asks `GameLock` which of today's and tomorrow's games must be
   saved now. Nothing else is predicted: a held game waits for a later run,
   a started one is never predicted.
3. **Inputs.** For each game to save: the projected goalies (Daily Faceoff,
   matched to the league's player ids through the clubs' rosters), and the
   market's two-way price from the league's odds feed. A goalie the page
   does not name, or that no roster matches, falls back to the club's last
   starter, and the pick says so. A game with no market price gets Model A
   only, and says that too. Each club's injury list, as context only
   (`src/sports/nhl/injuries.py`); a failed read stores none and the pick
   is saved regardless.
4. **Models.** Model A and Model B as registered
   (`experiments/nhl/stage56/registry.json`), with the half-life and K the
   backtest chose (`results/confirmation.json`), fitted on every finished
   game since 2015-16 (Model B on those with a market price).
5. **Save.** One file per game, `predictions/nhl/<season>/<game_id>.json`,
   written once and never rewritten: a file already there is left alone.
6. **Grade.** Every saved pick whose game is final is scored;
   a cancelled game is marked cancelled and never counted
   (`results/nhl/graded_<season>.json`).

7. **Standings.** In a run that saves picks, the rest of the regular season
   is simulated from Model A with today's ratings
   (`src/sports/nhl/standings.py`; `results/nhl/standings_<season>.json`).
8. **Page inputs.** Every run writes the season's schedule and today's
   ratings for the NHL's pages (`src/sports/nhl/page_inputs.py`).

`.github/workflows/nhl-daily.yml` runs this at 14:00 and 21:00 UTC.

Run by hand: python -m src.sports.nhl.daily
"""
from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.core.sport import GameStatus, sport_paths
from src.sports.nhl import (
    backtest,
    drift,
    goalies,
    history,
    injuries,
    market,
    page_inputs,
    ratings,
    roster,
    standings,
)
from src.sports.nhl import schedule as nhl_schedule
from src.sports.nhl.lock import GameLock

PATHS = sport_paths('nhl')
CODE_VERSION = 'nhl-stage56'

Json = Any


def chosen() -> tuple[float, float]:
    """The half-life and K the Stage 56 backtest chose on validation."""
    doc = json.loads((backtest.RESULTS / 'confirmation.json').read_text(encoding='utf-8'))
    return float(doc['H_days']), float(doc['K_shots'])


def refresh_season(season: int, sched: pd.DataFrame, folder: Path = history.HISTORY,
                   get: Callable[[str], bytes] = history.fetch) -> pd.DataFrame:
    """This season's stored box scores plus any final game not stored yet."""
    path = folder / f'boxscores_{season}.csv'
    have = pd.read_csv(path, dtype={'game_id': str}) if path.exists() else pd.DataFrame(columns=list(history.BOX_FIELDS))
    finals = sched[sched['status'] == GameStatus.FINAL.value]
    missing = finals[~finals['game_id'].isin(set(have['game_id']))]
    if missing.empty:
        return have
    new = []
    for gid in missing['game_id']:
        try:
            new.append(history.boxscores(season, get=get, schedule=missing[missing['game_id'] == gid], pause=0))
        except history.HistoryError as exc:
            # Just after the final horn the league's box score can lack the
            # starter flags (seen 2026-10-05: state FINAL, flags None, set
            # once the game is OFF). Not stored, so the next run tries again.
            print(f'box score not settled yet, retried next run: {exc}')
    if not new:
        return have
    out = pd.concat([have, *new], ignore_index=True).sort_values(['game_date', 'game_id'], kind='stable')
    history.write(out, path)
    return out


def last_starters(box: pd.DataFrame) -> dict[str, Any]:
    """Each club's most recent starting goalie, by franchise."""
    last: dict[str, Any] = {}
    for g in box.sort_values(['game_date', 'game_id'], kind='stable').itertuples():
        last[ratings.franchise(g.home)] = g.home_goalie_id
        last[ratings.franchise(g.away)] = g.away_goalie_id
    return last


def fit_models(table: pd.DataFrame, k: float) -> tuple[Any, Any]:
    a_cols = ['goal_matchup', 'shot_matchup', backtest.goalie_column(k)]
    model_a = backtest.estimator().fit(table[a_cols], table['home_win'])
    priced = table.dropna(subset=['home_prob'])
    model_b = backtest.estimator().fit(
        priced[a_cols].assign(market_logit=np.log(priced['home_prob'] / (1 - priced['home_prob']))),
        priced['home_win'])
    return model_a, model_b


def pick_record(game: pd.Series, feats: dict[str, float], k: float, model_a: Any, model_b: Any,
                line: dict[str, Any] | None, goalie_notes: dict[str, Any], now: datetime,
                injury_list: dict[str, Any] | None = None) -> dict[str, Any]:
    a_cols = ['goal_matchup', 'shot_matchup', backtest.goalie_column(k)]
    x = pd.DataFrame([feats])[a_cols]
    p_a = float(model_a.predict_proba(x)[0, 1])
    p_b = None
    if line is not None:
        xb = x.assign(market_logit=np.log(line['home_prob'] / (1 - line['home_prob'])))
        p_b = float(model_b.predict_proba(xb)[0, 1])
    lead = p_b if p_b is not None else p_a
    return {
        'game_id': str(game['game_id']), 'season': int(game['season']), 'slate': str(game['slate']),
        'start_utc': pd.Timestamp(game['start_utc']).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'home': game['home'], 'away': game['away'],
        'model_a': round(p_a, 4), 'model_b': None if p_b is None else round(p_b, 4),
        'pick': game['home'] if lead >= 0.5 else game['away'],
        'pick_model': 'model_b' if p_b is not None else 'model_a',
        'features': {key: round(v, 6) for key, v in feats.items()},
        'market': line, 'goalies': goalie_notes, 'injuries': injury_list,
        'saved_utc': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'code': CODE_VERSION,
    }


def read_injuries(season: int, get: Callable[[str], bytes]) -> tuple[str, pd.DataFrame] | None:
    """The latest injury list, or None when it cannot be read: injuries are
    context, so their source failing never stops a pick being saved."""
    try:
        return injuries.latest(get(injuries.source(season)))
    except (injuries.InjurySourceError, OSError) as exc:
        print(f'injuries: not read, picks saved without them: {exc}')
        return None


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


def grade(folder: Path, sched: pd.DataFrame) -> list[dict[str, Any]]:
    """One row per saved pick: correct, wrong, cancelled, or pending."""
    by_id = sched.set_index('game_id')
    rows = []
    for path in sorted(folder.glob('*.json')):
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
        rows.append({'game_id': pick['game_id'], 'pick': pick['pick'], 'result': result})
    return rows


def drift_rows(folder: Path, sched: pd.DataFrame) -> list[tuple[float | None, int | None]]:
    """(Model A's home probability, home won) for every saved pick whose game
    is final."""
    finals = sched[sched['status'] == GameStatus.FINAL.value].set_index('game_id')
    rows: list[tuple[float | None, int | None]] = []
    for path in sorted(folder.glob('*.json')):
        pick = json.loads(path.read_text(encoding='utf-8'))
        if pick['game_id'] in finals.index:
            rows.append((pick.get('model_a'), int(finals.loc[pick['game_id'], 'home_win'])))
    return rows


def write_standings(sched: pd.DataFrame, games: pd.DataFrame, rated: ratings.DayRatings, model_a: Any,
                    k: float, as_of: str, season: int, n_sim: int = 10000) -> Path:
    """The standings odds (Stage 57 item 3) from this run's Model A, written
    to `results/nhl/standings_<season>.json`. Overtime and shootout shares
    come from this season and the last."""
    cols = ['goal_matchup', 'shot_matchup', backtest.goalie_column(k)]
    probs = standings.unplayed_probabilities(
        sched, lambda h, a: rated.matchup(h, a, None, None, [k]), model_a, cols)
    ot = standings.overtime_share(games[games['season'] >= season - 1])
    table = standings.simulate(sched, probs, ot, n_sim=n_sim)
    out = PATHS.results / f'standings_{season}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(standings.to_json(table, as_of, n_sim, ot), indent=1) + '\n', encoding='utf-8')
    return out


def write_page_inputs(sched: pd.DataFrame, games: pd.DataFrame, folder: Path, h: float, k: float,
                      today: pd.Timestamp, season: int) -> None:
    """The schedule and the ratings as they stand, for the NHL's pages
    (`src/sports/nhl/page_inputs.py`). Written every run."""
    day = today.tz_localize(None)
    rated = ratings.day_ratings(games[games['day'] < day], day, h)
    recent = games[games['season'] >= season - 1]
    goalies_seen = pd.concat([recent['home_goalie_id'], recent['away_goalie_id']]).dropna()
    picks = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(folder.glob('*.json'))] if folder.exists() else []
    as_of = str(today.date())
    page_inputs.write(PATHS.results / f'schedule_{season}.json', page_inputs.schedule_json(sched, as_of))
    clubs = set(sched['home']) | set(sched['away'])
    page_inputs.write(PATHS.results / f'ratings_{season}.json', page_inputs.ratings_json(
        rated, k, clubs, goalies_seen, page_inputs.goalie_names(picks), as_of))


def main(now: datetime | None = None, get: Callable[[str], bytes] = history.fetch) -> int:
    now = now or datetime.now(UTC)
    season = nhl_schedule.current_season(now)
    sched = nhl_schedule.load_schedule(season)
    first = backtest.registry()['protocol']['training_from_season']
    past = backtest.load_history(first, season - 1)
    current = refresh_season(season, sched)
    games = ratings.prepare(pd.concat([past, current], ignore_index=True))
    h, k = chosen()

    today = pd.Timestamp(now).tz_convert('America/New_York').normalize()
    days = {str(today.date()), str((today + pd.Timedelta(days=1)).date())}
    slate = sched[sched['slate'].isin(days)]
    decision = GameLock().decide(slate, now)
    folder = PATHS.predictions / str(season)
    if decision.lock:
        table = ratings.features(games, h, [k]).merge(games[['game_id', 'home_prob']], on='game_id', how='left')
        model_a, model_b = fit_models(table, k)
        lines, missing = market.parse(json.loads(get(market.SOURCE)), now)
        for m in missing:
            print(f'market: {m}')
        market.record(lines, PATHS.data / 'lines' / f'{season}.json')
        line_by_id = {r['game_id']: r for r in lines}
        projected = {}
        for day in sorted(days):
            try:
                rows = goalies.parse_faceoff(get(f'{goalies.SOURCE}/{day}').decode('utf-8', 'replace'), now)
                attached = goalies.attach_games(rows, sched[sched['slate'] == day].to_dict('records'))
            except goalies.GoalieSourceError as exc:
                print(f'goalies for {day}: {exc}')
                continue
            goalies.record(attached, PATHS.data / 'goalies' / f'{season}.json')
            projected.update({r['game_id']: r for r in attached})
        locking = slate[slate['game_id'].isin(decision.lock)]
        rosters = roster.goalie_ids(set(locking['home']) | set(locking['away']), get=lambda u: json.loads(get(u)))
        fallback = last_starters(games)
        injury_table = read_injuries(season, get)
        rated = ratings.day_ratings(games[games['day'] < today.tz_localize(None)], today.tz_localize(None), h)
        for _, g in locking.iterrows():
            notes, ids = {}, {}
            proj = projected.get(str(g['game_id']), {})
            for side in ('home', 'away'):
                pid, why = roster.match(proj.get(f'{side}_goalie'), rosters.get(g[side], []))
                if pid is None:
                    pid = fallback.get(ratings.franchise(g[side]))
                    notes[side] = {'player_id': pid, 'basis': 'last_start', 'note': why}
                else:
                    notes[side] = {'player_id': pid, 'name': proj.get(f'{side}_goalie'),
                                   'status': proj.get(f'{side}_status'), 'basis': 'projected',
                                   'report': proj.get(f'{side}_report')}
                ids[side] = pid
            feats = rated.matchup(g['home'], g['away'], ids['home'], ids['away'], [k])
            injury_list = None if injury_table is None else injuries.for_game(
                injury_table[0], injury_table[1], g['home'], g['away'], now)
            record = pick_record(g, feats, k, model_a, model_b, line_by_id.get(str(g['game_id'])), notes, now,
                                 injury_list)
            print(('saved ' if save_once(record, folder) else 'already saved ') + record['game_id'])
        print(f'standings: {write_standings(sched, games, rated, model_a, k, str(today.date()), season)}')
    graded = grade(folder, sched)
    out = PATHS.results / f'graded_{season}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(graded, indent=1) + '\n', encoding='utf-8')
    write_page_inputs(sched, games, folder, h, k, today, season)
    spec = drift.baseline()
    losses = drift.per_game_log_loss(drift_rows(folder, sched))
    flagged = drift.flags(losses, spec)
    (PATHS.results / f'drift_{season}.json').write_text(json.dumps(
        {'games': len(losses), 'mean_log_loss': (sum(losses) / len(losses)) if losses else None,
         'baseline': spec['baseline']['value'], 'flagged': flagged}, indent=1) + '\n', encoding='utf-8')
    if flagged:
        print('DRIFT CHECK: FLAGGED (Model A log loss is significantly above its backtest)')
    print(f'lock {len(decision.lock)}, hold {len(decision.hold)}, started {len(decision.started)}; '
          f'graded {sum(r["result"] in ("correct", "wrong") for r in graded)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
