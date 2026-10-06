"""The NHL's history for the Stage 56 backtest, read once and kept in the repository.

The registration (`experiments/nhl/stage56/registry.json`) asks for each
past game's shots on goal and starting goalies, and for the market's price,
read by the backtest's own code and stored so that a re-run reads the same
inputs. This file does both, one season at a time:

- `data/nhl/history/boxscores_<season>.csv`: one row per final game from the
  league's box score (`gamecenter/<id>/boxscore`): each team's shots on goal
  and its flagged starting goalie, with the shots he faced and the goals he
  allowed while in net.
- `data/nhl/history/market_<season>.csv`: one row per regular-season game
  ESPN priced, matched to the league's game id: the provider, both moneyline
  prices, and the home team's two-way probability with the margin out. Up to
  2023-24 ESPN's line is the three-way regulation market, converted by the
  logit fit in `docs/nhl-data.md` (`CONVERSION`); from 2024-25 it is native.

Before a box-score season is written, it is checked against the fallback
(SportsDataverse's `team_box`): shots on goal must agree on at least 99% of
the games both have, as the registration says, and every disagreement is
listed. Nothing here is guessed: a game the league lists as final without a
box score, or an ESPN game that matches no league game, stops the season
with its id.

Run by hand: python -m src.sports.nhl.history 2015 2025
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import time
import urllib.request
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.sport import sport_paths
from src.sports.nhl import schedule as nhl_schedule
from src.sports.nhl.market import implied

HISTORY = sport_paths('nhl').data / 'history'
BOX = 'https://api-web.nhle.com/v1/gamecenter/{gid}/boxscore'
FALLBACK = ('https://raw.githubusercontent.com/sportsdataverse/fastRhockey-nhl-data/main/'
            'nhl/team_box/parquet/team_box_{end_year}.parquet')
ESPN_SCOREBOARD = 'https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard?dates={d}'
ESPN_ODDS = ('https://sports.core.api.espn.com/v2/sports/hockey/leagues/nhl/'
             'events/{e}/competitions/{e}/odds')

#: docs/nhl-data.md: logit(two-way) = a + b * logit(three-way, draw left out),
#: fitted on 2020-21 and 2021-22, checked on 2022-23.
CONVERSION = (0.003, 0.824)
#: The first season whose ESPN line is the two-way moneyline.
NATIVE_FROM = 2024
#: ESPN's abbreviations where they differ from the league's.
ESPN_ABBR = {'NJ': 'NJD', 'SJ': 'SJS', 'TB': 'TBL', 'LA': 'LAK', 'UTAH': 'UTA'}
#: The registration's agreement floor for shots on goal against the fallback.
AGREEMENT = 0.99

BOX_FIELDS = ('game_id', 'season', 'game_date', 'game_type', 'home', 'away', 'home_score', 'away_score',
              'last_period', 'home_sog', 'away_sog',
              'home_goalie_id', 'home_goalie_sa', 'home_goalie_ga',
              'away_goalie_id', 'away_goalie_sa', 'away_goalie_ga')
MARKET_FIELDS = ('game_id', 'season', 'game_date', 'home', 'away', 'provider',
                 'home_price', 'away_price', 'home_prob', 'converted')

Json = Any


class HistoryError(ValueError):
    """A season that cannot be written without guessing."""


def fetch(url: str, timeout: int = 30, tries: int = 3) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': 'NFL-Model-2 NHL history'})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body: bytes = r.read()
                return body
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    raise AssertionError('unreachable')


def _starter(side: Json, gid: Any, which: str) -> Json:
    starters = [g for g in (side or {}).get('goalies', []) if g.get('starter')]
    if len(starters) != 1:
        raise HistoryError(f'game {gid} {which}: {len(starters)} starting goalies flagged, not 1')
    return starters[0]


def box_row(box: Json, game_type: str) -> dict[str, Any]:
    """One stored row from a league box score."""
    gid = box.get('id')
    stats = box.get('playerByGameStats') or {}
    home, away = box['homeTeam'], box['awayTeam']
    hs, as_ = _starter(stats.get('homeTeam'), gid, 'home'), _starter(stats.get('awayTeam'), gid, 'away')
    for team in (home, away):
        if not isinstance(team.get('sog'), int):
            raise HistoryError(f'game {gid}: no shots on goal for {team.get("abbrev")}')
    return {
        'game_id': str(gid), 'season': int(str(box['season'])[:4]), 'game_date': box['gameDate'],
        'game_type': game_type, 'home': home['abbrev'], 'away': away['abbrev'],
        'home_score': home['score'], 'away_score': away['score'],
        'last_period': (box.get('gameOutcome') or {}).get('lastPeriodType'),
        'home_sog': home['sog'], 'away_sog': away['sog'],
        'home_goalie_id': hs['playerId'], 'home_goalie_sa': hs['shotsAgainst'], 'home_goalie_ga': hs['goalsAgainst'],
        'away_goalie_id': as_['playerId'], 'away_goalie_sa': as_['shotsAgainst'], 'away_goalie_ga': as_['goalsAgainst'],
    }


def boxscores(season: int, get: Callable[[str], bytes] = fetch,
              schedule: pd.DataFrame | None = None, pause: float = 0.05) -> pd.DataFrame:
    """Every final game of a season, one box score each. With `NHL_CACHE` set,
    each raw box score is kept there too, so an interrupted season resumes."""
    sched = schedule if schedule is not None else nhl_schedule.load_schedule(season)
    finals = sched[sched['status'] == 'final']
    cache = nhl_schedule.cache_dir()
    rows = []
    for g in finals.itertuples():
        raw_path = cache / 'box' / str(season) / f'{g.game_id}.json' if cache is not None else None
        if raw_path is not None and raw_path.exists():
            raw = raw_path.read_bytes()
        else:
            raw = get(BOX.format(gid=g.game_id))
            if raw_path is not None:
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_path.write_bytes(raw)
            if pause:
                time.sleep(pause)
        rows.append(box_row(json.loads(raw), str(g.game_type)))
    return pd.DataFrame(rows, columns=list(BOX_FIELDS))


def fallback_disagreements(box: pd.DataFrame, team_box: pd.DataFrame) -> tuple[int, list[str]]:
    """(games compared, sentences for each game whose shots on goal differ)
    against SportsDataverse's team_box for the same season."""
    tb = team_box.assign(game_id=team_box['game_id'].astype(str))
    side = tb.pivot_table(index='game_id', columns='home_away', values='shots_on_goal', aggfunc='first')
    side = side.rename(columns={'home': 'fb_home', 'away': 'fb_away'})
    both = box.set_index('game_id').join(side, how='inner')
    out = [f'game {gid}: league {r.home_sog}-{r.away_sog}, fallback {r.fb_home:.0f}-{r.fb_away:.0f}'
           for gid, r in both.iterrows() if (r.home_sog, r.away_sog) != (r.fb_home, r.fb_away)]
    return len(both), out


def check_against_fallback(box: pd.DataFrame, team_box: pd.DataFrame) -> list[str]:
    """Empty when the season meets the registration's floor; otherwise the
    reason and every disagreement."""
    n, bad = fallback_disagreements(box, team_box)
    if n == 0:
        return ['the fallback has none of this season\'s games']
    if (n - len(bad)) / n < AGREEMENT:
        return [f'shots on goal agree on {n - len(bad)} of {n} games, under {AGREEMENT:.0%}', *bad]
    return []


def two_way(home_price: float, away_price: float, season: int) -> tuple[float, bool]:
    """The home team's two-way probability from ESPN's two prices, and
    whether it was converted from the three-way line."""
    h, a = implied(home_price), implied(away_price)
    p = h / (h + a)
    if season >= NATIVE_FROM:
        return p, False
    intercept, slope = CONVERSION
    z = intercept + slope * math.log(p / (1 - p))
    return 1 / (1 + math.exp(-z)), True


def _num(value: Any) -> float | None:
    try:
        return float(str(value).replace('+', ''))
    except (TypeError, ValueError):
        return None


def espn_season(season: int, sched: pd.DataFrame, get: Callable[[str], bytes] = fetch,
                pause: float = 0.05) -> pd.DataFrame:
    """ESPN's moneyline for every regular-season game of a season, matched to
    the league's game id by date and both clubs."""
    regular = sched[(sched['game_type'] == 'regular') & (sched['status'] == 'final')]
    index = {(str(r.slate), r.home, r.away): r for r in regular.itertuples()}
    days = sorted(set(regular['slate']))
    rows, unmatched = [], []
    for day in days:
        events = json.loads(get(ESPN_SCOREBOARD.format(d=day.replace('-', '')))).get('events', [])
        for ev in events:
            if (ev.get('season') or {}).get('type') != 2:
                continue
            comp = ev['competitions'][0]
            if not ((comp.get('status') or {}).get('type') or {}).get('completed'):
                continue  # postponed or never played: the league's own final games decide
            teams = {c['homeAway']: c['team']['abbreviation'] for c in comp['competitors']}
            home, away = (ESPN_ABBR.get(teams['home'], teams['home']), ESPN_ABBR.get(teams['away'], teams['away']))
            game = index.get((day, home, away))
            if game is None:
                unmatched.append(f'{away} at {home} on {day} (ESPN {ev["id"]})')
                continue
            items = json.loads(get(ESPN_ODDS.format(e=ev['id']))).get('items') or []
            if not items:
                continue
            it = items[0]
            hp, ap = _num(it.get('homeTeamOdds', {}).get('moneyLine')), _num(it.get('awayTeamOdds', {}).get('moneyLine'))
            if hp is None or ap is None:
                continue
            prob, converted = two_way(hp, ap, season)
            rows.append({'game_id': str(game.game_id), 'season': season, 'game_date': day, 'home': home, 'away': away,
                         'provider': (it.get('provider') or {}).get('name'), 'home_price': hp, 'away_price': ap,
                         'home_prob': round(prob, 6), 'converted': converted})
            if pause:
                time.sleep(pause)
    if unmatched:
        raise HistoryError(f'{len(unmatched)} ESPN game(s) match no league game: ' + '; '.join(unmatched[:10]))
    return pd.DataFrame(rows, columns=list(MARKET_FIELDS))


def write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    df.to_csv(tmp, index=False, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
    tmp.replace(path)


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('first', type=int)
    ap.add_argument('last', type=int)
    ap.add_argument('--market-from', type=int, default=2020, help='first season ESPN prices')
    args = ap.parse_args(list(argv) if argv is not None else None)
    for season in range(args.first, args.last + 1):
        sched = nhl_schedule.load_schedule(season)
        box_path = HISTORY / f'boxscores_{season}.csv'
        if not box_path.exists():
            box = boxscores(season, schedule=sched)
            team_box = pd.read_parquet(io.BytesIO(fetch(FALLBACK.format(end_year=season + 1))))
            problems = check_against_fallback(box, team_box)
            if problems:
                raise HistoryError(f'{season}: ' + '; '.join(problems[:20]))
            n, bad = fallback_disagreements(box, team_box)
            write(box, box_path)
            print(f'{season}: {len(box)} box scores; shots on goal agree with the fallback on '
                  f'{n - len(bad)} of {n}', flush=True)
            for line in bad:
                print(f'  {line}', flush=True)
        market_path = HISTORY / f'market_{season}.csv'
        if season >= args.market_from and not market_path.exists():
            market = espn_season(season, sched)
            write(market, market_path)
            print(f'{season}: {len(market)} market prices', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
