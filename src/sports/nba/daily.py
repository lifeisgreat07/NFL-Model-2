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

from src.core import (
    after_save,
    day_picks,
    forward_test,
    priced,
    request_budget,
    schedule_guard,
    season_prices,
)
from src.core.day_picks import missed as missed
from src.core.day_picks import missed_line as missed_line
from src.core.day_picks import save_once as save_once
from src.core.provenance import code_identity, training
from src.core.sport import GameStatus, sport_paths
from src.sports.nba import (
    backtest,
    drift,
    history,
    injuries,
    m2,
    market,
    page_inputs,
    ratings,
    standings,
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


def fit_before(table: pd.DataFrame, day: pd.Timestamp, first: int) -> tuple[dict[str, Any], dict[str, Any]]:
    """The models and their provenance, fitted on every final game strictly
    before `day`, the pick's slate day, as experiments/nba/stage65/registry.json
    registers them ("to the day before"). Until Stage 85 item 4 one fit on
    every final game served the whole run, so a run after an afternoon game
    fitted on that game before picking the same day's evening ones."""
    before = table[pd.to_datetime(table['day']) < day]
    return fit_models(before), training(before, first)



def write_standings(sched: pd.DataFrame, games: pd.DataFrame, table: pd.DataFrame, h: float, lam: float,
                    first: int, today: pd.Timestamp, season: int, n_sim: int = 10000) -> Path:
    """The standings odds (Stage 104 item 4) to `results/nba/standings_<season>.json`:
    Model A without its availability term, fitted on every final game before today,
    with today's ratings held fixed, for every unplayed game and every pairing a
    play-in game could be."""
    day = today.tz_localize(None)
    models, _ = fit_before(table, day, first)
    model = models['a_no_availability']
    rated = ratings.day_ratings(games[games['day'] < day], day, h, lam)
    clubs = sorted(set(sched['home']) | set(sched['away']))
    left = sched[(sched['game_type'] == 'regular') & ~sched['status'].isin(['final', 'cancelled'])]
    rows = list(zip(left['game_id'].astype(str), left['home'], left['away'], strict=True))
    pairs = [(a, b) for a in clubs for b in clubs if a != b]
    x = pd.DataFrame([dict(rated.matchup(hm, aw)) for _, hm, aw in rows]
                     + [dict(rated.matchup(a, b)) for a, b in pairs])[NO_AVAIL]
    p = model.predict_proba(x)[:, 1]
    home_prob = {gid: float(v) for (gid, _, _), v in zip(rows, p[:len(rows)], strict=True)}
    pair_prob = {ab: float(v) for ab, v in zip(pairs, p[len(rows):], strict=True)}
    odds = standings.simulate(sched, home_prob, pair_prob, n_sim=n_sim)
    out = PATHS.results / f'standings_{season}.json'
    page_inputs.write(out, standings.to_json(odds, str(today.date()), n_sim, standings.games_listed(sched)))
    return out


def availability_for(minutes: pd.DataFrame, day_of: dict[str, pd.Timestamp], team: str, day: pd.Timestamp,
                     h: float, out: set[str]) -> float:
    """The share of the team's expected minutes whose players are not listed Out."""
    expected = ratings.expected_minutes(minutes, day_of, team, day, h)
    return ratings.availability(expected, [p for p in expected if p not in out])


def game_availability(report: injuries.Report | None, home: str, away: str, minutes: pd.DataFrame,
                      day_of: dict[str, pd.Timestamp], day: pd.Timestamp, h: float, now: datetime
                      ) -> tuple[float | None, dict[str, Any] | None, dict[str, Any] | None, str]:
    """(availability_matchup, what the pick stores of it, the injury list, why
    not) for one game. No report, or a row of either team's that could not be
    read (Stage 83 item 5), means no availability for this game, and why says
    which; every other game uses the report."""
    if report is None:
        return None, None, None, 'injury report not read'
    unread = [t for t in (home, away) if t in report.unread]
    if unread:
        return None, None, None, 'injury report rows not read for ' + '; '.join(
            f"{t} ({', '.join(report.unread[t])})" for t in unread)
    ah = availability_for(minutes, day_of, home, day, h, injuries.out_ids(report.rows, home))
    aa = availability_for(minutes, day_of, away, day, h, injuries.out_ids(report.rows, away))
    return (ah - aa, {'read': True, 'home': round(ah, 4), 'away': round(aa, 4)},
            injuries.for_game(report.rows, home, away, now), '')


def pick_record(game: pd.Series, feats: dict[str, float], models: dict[str, Any], price: dict[str, Any],
                avail: dict[str, Any] | None, injury_list: dict[str, Any] | None, now: datetime,
                why: str = 'injury report not read') -> dict[str, Any]:
    """The saved pick. `avail` is None when availability could not be read for
    this game (`why` says what was not read): both models then run without the
    availability term, and the pick says so."""
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
                                                         'note': f'{why}; both models ran without availability'},
        'features': {key: round(float(v), 6) for key, v in feats.items() if key in cols},
        'market': price, 'injuries': injury_list,
        'saved_utc': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'code': CODE_VERSION,
    }


def recently_started(sched: pd.DataFrame, now: datetime) -> tuple[str, ...]:
    """Every game of yesterday's and today's slates (Eastern) that has started.

    Stage 92 item 11 (audit 7, R11): the run used to check only the games of
    the slates it was deciding, today's and tomorrow's, so a game of
    yesterday's slate that started after the last run that could have saved it
    was never named. Postponed and cancelled games are not started."""
    today = pd.Timestamp(now).tz_convert('America/New_York').normalize()
    days = {str((today - pd.Timedelta(days=1)).date()), str(today.date())}
    return GameLock().decide(sched[sched['slate'].isin(days)], now).started

def grade(folder: Path, sched: pd.DataFrame) -> list[dict[str, Any]]:
    """src/core/day_picks.grade, each row carrying the pick's market_source."""
    return day_picks.grade(folder, sched, extra=('market_source',))


def availability_read(pick: dict[str, Any]) -> bool:
    """Whether the pick was made with the injury report: `pick_record` saves
    {'read': False, ...} when it was not (Stage 85 item 2)."""
    return (pick.get('availability') or {}).get('read', True) is not False


def drift_picks(folder: Path, sched: pd.DataFrame) -> list[tuple[float | None, int | None, bool]]:
    """(Model A's home probability, home won, made with the injury report) for
    every saved pick whose game is final, in the order the games started."""
    finals = sched[sched['status'] == GameStatus.FINAL.value].set_index('game_id')
    keyed: list[tuple[tuple[str, str], tuple[float | None, int | None, bool]]] = []
    for path in sorted(folder.glob('*.json')) if folder.exists() else []:
        pick = json.loads(path.read_text(encoding='utf-8'))
        if pick['game_id'] in finals.index:
            keyed.append(((pick.get('start_utc') or '', pick['game_id']),
                          (pick.get('model_a'), int(finals.loc[pick['game_id'], 'home_win']),
                           availability_read(pick))))
    # Stage 85 item 1: in the order the games started, so a registered look's
    # first n picks are the first n games played, not the first n game ids.
    return [row for _, row in sorted(keyed, key=lambda kr: kr[0])]


def drift_days(folder: Path, sched: pd.DataFrame) -> list[str]:
    """Stage 95 item 32: each `drift_picks` row's slate day, in the same order."""
    finals = sched[sched['status'] == GameStatus.FINAL.value].set_index('game_id')
    keyed = []
    for path in sorted(folder.glob('*.json')) if folder.exists() else []:
        pick = json.loads(path.read_text(encoding='utf-8'))
        if pick['game_id'] in finals.index:
            keyed.append(((pick.get('start_utc') or '', pick['game_id']), str(pick['slate'])))
    return [day for _, day in sorted(keyed, key=lambda kd: kd[0])]


def drift_rows(folder: Path, sched: pd.DataFrame) -> list[tuple[float | None, int | None]]:
    """(Model A's home probability, home won) for every saved pick whose game is final."""
    return [(p, y) for p, y, _ in drift_picks(folder, sched)]


def read_injuries(get: Callable[[str], bytes], teams: set[str]) -> injuries.Report | None:
    """The injury report, or None when it cannot be read as registered. Rows
    it read only in part name their teams, whose games go without availability."""
    try:
        report = injuries.parse(json.loads(get(injuries.SOURCE)), teams)
    except (injuries.InjurySourceError, OSError, ValueError) as exc:
        print(f'DEGRADED: injuries: not read, picks made without availability: {exc}')
        return None
    for team, problems in sorted(report.unread.items()):
        print(f"DEGRADED: injuries: {team}'s rows not all read, its games picked without availability: "
              + '; '.join(problems))
    return report


def read_espn_odds(gid: str, get: Callable[[str], bytes]) -> Json | None:
    try:
        return json.loads(get(market.ESPN_ODDS.format(e=gid)))
    except (OSError, ValueError) as exc:
        print(f'DEGRADED: ESPN odds for {gid}: not read: {exc}')
        return None


def read_kalshi(get: Callable[[str], bytes]) -> dict[Any, Any] | None:
    try:
        return market.kalshi_prices(json.loads(get(market.KALSHI)))
    except (OSError, ValueError) as exc:
        print(f'DEGRADED: Kalshi: not read: {exc}')
        return None


def main(now: datetime | None = None, get: Callable[[str], bytes] = history.fetch) -> int:
    now = now or datetime.now(UTC)
    season = nba_schedule.current_season(now)
    # Stage 93 item 18: under a budget, so a slow feed stops cleanly inside the step's timeout.
    sched = nba_schedule.load_schedule(season, get=request_budget.Budget().wrap(lambda u: json.loads(get(u))))
    # Stage 91 item 2: an empty or shrunken feed stops the run before anything is written.
    schedule_guard.check(len(sched), PATHS.results / f'schedule_{season}.json')
    first = backtest.registry()['protocol']['training_from_season']
    past_games, past_minutes = backtest.load_history(first, season - 1)
    cur_games, cur_minutes = refresh_season(season, sched, get=get)
    # Stage 85 item 5: this season's games enter Model B's training rows with
    # the price the runs recorded, the last read before each game started.
    recorded = season_prices.read(PATHS.data / 'lines' / f'{season}.json')
    cur_games = cur_games.assign(home_prob=cur_games['game_id'].astype(str).map(recorded))
    games = ratings.prepare(pd.concat([past_games, cur_games], ignore_index=True))
    minutes = pd.concat([past_minutes, cur_minutes], ignore_index=True)
    minutes = minutes.assign(game_id=minutes['game_id'].astype(str), player_id=minutes['player_id'].astype(str))
    h, lam = chosen()

    today = pd.Timestamp(now).tz_convert('America/New_York').normalize()
    days = {str(today.date()), str((today + pd.Timedelta(days=1)).date())}
    slate = sched[sched['slate'].isin(days)]
    decision = GameLock().decide(slate, now)
    folder = PATHS.predictions / str(season)
    # Every run builds the availability and feature tables: the picks are
    # fitted on them, and M2 (Stage 84 item 4) reads them whether or not this
    # run saves a pick.
    avail_table = ratings.availability_table(games, minutes, h)
    table = ratings.features(games, minutes, h, lam, avail=avail_table)
    table = table.merge(games[['game_id', 'home_prob']], on='game_id', how='left')
    if decision.lock:
        fitted: dict[pd.Timestamp, tuple[dict[str, Any], dict[str, Any]]] = {}
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
            if day not in fitted:
                fitted[day] = fit_before(table, day, first)
            models, trained = fitted[day]
            trained = trained | code_identity('nba')  # Stage 95 item 39
            rated = ratings.day_ratings(games[games['day'] < day], day, h, lam)
            feats: dict[str, float] = dict(rated.matchup(g['home'], g['away']))
            matchup, avail, injury_list, why = game_availability(report, g['home'], g['away'], minutes, day_of,
                                                                 day, h, now)
            if matchup is not None:
                feats['availability_matchup'] = matchup
            record = pick_record(g, feats, models, price, avail, injury_list, now, why) | trained
            print(('saved ' if save_once(record, folder) else 'already saved ') + record['game_id']
                  + f" (price: {record['market_source'] or 'none'})")
        # Stage 92 item 7: odds that answered but priced none of the locking games say so.
        unpriced = priced.unpriced_line(locking['game_id'],
                                        (p['game_id'] for p in prices if p.get('home_prob') is not None))
        if unpriced:
            print(unpriced)
        # Stage 91 item 3: from here on the picks are saved, and no step may lose them.
        after_save.guarded('market record', market.record, prices, PATHS.data / 'lines' / f'{season}.json')
        # Stage 104 item 4: the standings odds, in a run that saves picks, as the NHL's.
        after_save.guarded('standings file', write_standings, sched, games, table, h, lam, first, today, season)
    PATHS.results.mkdir(parents=True, exist_ok=True)
    after_save.guarded('schedule file', lambda: page_inputs.write(PATHS.results / f'schedule_{season}.json',
                                                                  page_inputs.schedule_json(sched, str(today.date()))))
    # Stage 104 item 3: the ratings as they stand before today, for the Power Ratings and Teams pages.
    rated_on = today.tz_localize(None)
    after_save.guarded('ratings file', lambda: page_inputs.write(
        PATHS.results / f'ratings_{season}.json',
        page_inputs.ratings_json(ratings.day_ratings(games[games['day'] < rated_on], rated_on, h, lam),
                                 set(sched['home']) | set(sched['away']), str(today.date()))))

    def write_grades() -> list[dict[str, Any]]:
        graded = grade(folder, sched)
        (PATHS.results / f'graded_{season}.json').write_text(json.dumps(graded, indent=1) + '\n', encoding='utf-8')
        return graded

    def write_drift() -> None:
        spec = drift.baseline()
        # Stage 85 item 2: each pick is held to the backtest of the model it ran.
        picks = drift_picks(folder, sched)
        losses, bases = drift.per_game(picks, spec)
        days = drift.kept_days(picks, drift_days(folder, sched))   # Stage 95 item 32
        flagged = drift.flags(losses, spec, bases, days)
        without = sum(1 for b in bases if b == spec['baseline_no_availability']['value'])
        mean = (sum(losses) / len(losses)) if losses else None
        base = drift.look_baseline(spec, bases, len(bases)) if bases else spec['baseline']['value']
        # Stage 95 item 33: the other direction a leak shows in, said rather than flagged.
        leak = drift.leak_direction(mean, len(losses), base, drift.spread_range(), spec['rule']['checkpoints'][0],
                                    drift.leaked_picks(folder))
        (PATHS.results / f'drift_{season}.json').write_text(json.dumps(
            {'games': len(losses), 'mean_log_loss': mean, 'baseline': base,
             'without_availability': without, 'flagged': flagged,
             'looks': drift.looks(losses, spec, bases, days), 'next_look': drift.next_look(len(losses), spec),
             'leak': leak},
            indent=1) + '\n', encoding='utf-8')
        for line in drift.leak_lines(leak):
            print(line)
        if flagged:
            print('DRIFT CHECK: FLAGGED (Model A log loss is significantly above its backtest)')

    def write_forward() -> None:
        # Stage 84 item 1: the registered forward test, on every saved pick whose game is final.
        fwd = forward_test.write(PATHS.results / f'forward_{season}.json', 'nba', season,
                                 'experiments/nba/stage65/registry.json', folder, sched,
                                 games[['day', 'home_score', 'away_score']])
        print(f"forward test: {fwd['graded_picks']} graded picks through {fwd['through']}")
        # Stage 95 item 36: the deciding file, frozen once when the regular season is over.
        frozen = forward_test.freeze(PATHS.results / f'forward_{season}.json', sched, str(now.date()))
        if frozen is not None:
            print(f'forward test: the regular season is over; the deciding file is {frozen.name}')

    def write_m2() -> None:
        # Stage 84 item 4: Stage 61's M2, the injury report against who played.
        m2_out = m2.write(PATHS.results / f'm2_{season}.json', picks=forward_test.read_picks(folder), games=games,
                          minutes=minutes, table=table, box=avail_table, h=h, lam=lam, columns=A_COLUMNS,
                          fit=fit_models, report_availability=availability_for)
        print(f"M2: {m2_out['graded']} graded games")

    # Stage 91 item 3: each step below runs after the picks are saved; a failure prints
    # DEGRADED (which raises an issue) and the run goes on to commit the picks.
    graded = after_save.guarded('grading', write_grades) or []
    after_save.guarded('drift check', write_drift)
    after_save.guarded('forward test', write_forward)
    after_save.guarded('M2', write_m2)
    lost = missed_line(sorted(set(decision.started) | set(recently_started(sched, now))), folder)
    if lost:
        print(lost)
    print(f'lock {len(decision.lock)}, hold {len(decision.hold)}, started {len(decision.started)}; '
          f'graded {sum(r["result"] in ("correct", "wrong") for r in graded)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
