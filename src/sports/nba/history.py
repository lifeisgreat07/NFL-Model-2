"""The NBA's history for its first backtest, read once and kept in the repository.

The registration (`experiments/nba/stage61/registry.json`) asks for each
past game's team box score and every player's minutes, and for the
market's price, read by the backtest's own code and stored so that a re-run
reads the same inputs. This file writes, one season at a time:

- `data/nba/history/games_<season>.csv`: one row per final game from ESPN's
  box score (or the fallback's, below): both teams' points, field-goal and free-throw attempts,
  offensive rebounds and turnovers, and the game's possessions (the mean of
  the two teams' FGA + 0.44 FTA - OREB + TOV);
- `data/nba/history/minutes_<season>.csv`: one row per player per game:
  his team, his ESPN id and his minutes (0 for a player listed who did not
  play);
- `data/nba/history/market_<season>.csv`: one row per game ESPN priced: the
  provider, both moneyline prices (the closing price where ESPN gives one)
  and the home team's two-way probability with the margin out. A provider
  marked live is never used.

Where ESPN's box score is empty (it lists about 500 finished games of
2015-16 to 2017-18, and six of 2020-21's play-in, with no team figures and
every player's minutes as '--'), the game is read from the fallback instead
(hoopR's `team_box` and `player_box`), and `box_source` says so. A game
neither has is left out and named in `data/nba/history/skipped_<season>.csv`.

Before a season's games are written they are checked against the fallback
(SportsDataverse's hoopR `team_box`): points and field-goal attempts must
agree on at least 99% of the games both have, as the registration says,
and every disagreement is listed. hoopR mirrors ESPN, so this guards
against a dropped or garbled game, not against ESPN itself.

ESPN refuses GitHub's runners (docs/stage-history.md, #131), so this is run
on the local machine, as the NHL's history was. `NBA_CACHE` keeps each raw
box score, so an interrupted season resumes.

Run by hand: python -m src.sports.nba.history 2015 2025
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import time
import urllib.request
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.sport import sport_paths
from src.sports.nba import schedule as nba_schedule

HISTORY = sport_paths('nba').data / 'history'
SUMMARY = nba_schedule.SITE + '/summary?event={gid}'
ODDS = ('https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/'
        'events/{e}/competitions/{e}/odds')
FALLBACK = ('https://raw.githubusercontent.com/sportsdataverse/hoopR-nba-data/main/'
            'nba/team_box/parquet/team_box_{end_year}.parquet')
PLAYER_FALLBACK = ('https://raw.githubusercontent.com/sportsdataverse/hoopR-nba-data/main/'
                   'nba/player_box/parquet/player_box_{end_year}.parquet')
#: The registration's agreement floor against the fallback.
AGREEMENT = 0.99
#: A game's possessions: FGA + FTA_WEIGHT * FTA - OREB + TOV, averaged over
#: the two teams.
FTA_WEIGHT = 0.44

GAME_FIELDS = ('game_id', 'season', 'slate', 'game_type', 'neutral_site', 'home', 'away',
               'home_score', 'away_score',
               'home_fga', 'home_fta', 'home_oreb', 'home_tov',
               'away_fga', 'away_fta', 'away_oreb', 'away_tov', 'possessions', 'box_source')
MINUTE_FIELDS = ('game_id', 'team', 'player_id', 'minutes')
MARKET_FIELDS = ('game_id', 'season', 'home', 'away', 'provider', 'home_price', 'away_price',
                 'closing', 'home_prob')

Json = Any


class HistoryError(ValueError):
    """A season that cannot be written without guessing."""


def fetch(url: str, timeout: int = 30, tries: int = 4) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': 'NFL-Model-2 NBA history'})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body: bytes = r.read()
                return body
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(2 + 3 * attempt)
    raise AssertionError('unreachable')


def _pair(value: str, gid: Any, what: str) -> tuple[int, int]:
    try:
        made, att = str(value).split('-')
        return int(made), int(att)
    except ValueError as exc:
        raise HistoryError(f'game {gid}: {what} reads {value!r}, not made-attempted') from exc


def _team_stats(team: Json, gid: Any) -> dict[str, int]:
    stats = {s.get('name'): s.get('displayValue') for s in team.get('statistics') or []}
    abbr = (team.get('team') or {}).get('abbreviation')
    need = ('fieldGoalsMade-fieldGoalsAttempted', 'freeThrowsMade-freeThrowsAttempted',
            'offensiveRebounds', 'totalTurnovers')
    missing = [n for n in need if stats.get(n) in (None, '')]
    if missing:
        raise HistoryError(f'game {gid} {abbr}: no {", ".join(missing)}')
    try:
        oreb, tov = int(stats['offensiveRebounds']), int(stats['totalTurnovers'])
    except ValueError as exc:
        raise HistoryError(f'game {gid} {abbr}: a count that is not a number') from exc
    return {'fga': _pair(stats['fieldGoalsMade-fieldGoalsAttempted'], gid, 'FG')[1],
            'fta': _pair(stats['freeThrowsMade-freeThrowsAttempted'], gid, 'FT')[1],
            'oreb': oreb, 'tov': tov}


def possessions(home: dict[str, int], away: dict[str, int]) -> float:
    """The registration's possessions for one game."""
    def one(t: dict[str, int]) -> float:
        return t['fga'] + FTA_WEIGHT * t['fta'] - t['oreb'] + t['tov']
    return (one(home) + one(away)) / 2


def game_row(raw: Json, game: Any) -> dict[str, Any]:
    """One stored row from ESPN's summary for a final game of the schedule."""
    gid = game.game_id
    teams = {t.get('homeAway'): t for t in (raw.get('boxscore') or {}).get('teams') or []}
    if set(teams) != {'home', 'away'}:
        raise HistoryError(f'game {gid}: the box score has sides {sorted(teams)}')
    for side, abbr in (('home', game.home), ('away', game.away)):
        got = (teams[side].get('team') or {}).get('abbreviation')
        if got != abbr:
            raise HistoryError(f'game {gid}: box score {side} is {got}, schedule says {abbr}')
    h, a = _team_stats(teams['home'], gid), _team_stats(teams['away'], gid)
    return {'game_id': str(gid), 'season': int(game.season), 'slate': game.slate,
            'game_type': game.game_type, 'neutral_site': bool(game.neutral_site),
            'home': game.home, 'away': game.away,
            'home_score': int(game.home_score), 'away_score': int(game.away_score),
            **{f'home_{k}': v for k, v in h.items()}, **{f'away_{k}': v for k, v in a.items()},
            'possessions': round(possessions(h, a), 2), 'box_source': 'espn'}


def espn_box_empty(raw: Json) -> bool:
    """ESPN lists some finished games with no team figures and every
    player's minutes as '--' (about 500 games of 2015-16 to 2017-18, and six
    of 2020-21's play-in). Those games are read from the fallback instead."""
    teams = (raw.get('boxscore') or {}).get('teams') or []
    return len(teams) != 2 or any(not t.get('statistics') for t in teams)


def fallback_rows(game: Any, team_box: pd.DataFrame,
                  player_box: pd.DataFrame) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    """(game row, minute rows) from hoopR's team_box and player_box for a
    game ESPN's box score leaves empty, or None when hoopR lacks it too.
    Turnovers are hoopR's team total where it gives one, else its players'
    turnovers (2017-18 has no team total; the difference is the few
    turnovers charged to a team rather than a player)."""
    gid = str(game.game_id)
    tb = team_box[team_box['game_id'].astype(str) == gid]
    pb = player_box[player_box['game_id'].astype(str) == gid]
    sides = {str(r['team_home_away']): r for _, r in tb.iterrows()}
    if set(sides) != {'home', 'away'} or pb.empty:
        return None
    stats = {}
    for side, abbr in (('home', game.home), ('away', game.away)):
        r = sides[side]
        if r['team_abbreviation'] != abbr:
            raise HistoryError(f'game {gid}: fallback {side} is {r["team_abbreviation"]}, schedule says {abbr}')
        tov = r.get('total_turnovers')
        stats[side] = {'fga': int(r['field_goals_attempted']), 'fta': int(r['free_throws_attempted']),
                       'oreb': int(r['offensive_rebounds']),
                       'tov': int(tov) if pd.notna(tov) else int(r['turnovers'])}
    h, a = stats['home'], stats['away']
    row = {'game_id': gid, 'season': int(game.season), 'slate': game.slate,
           'game_type': game.game_type, 'neutral_site': bool(game.neutral_site),
           'home': game.home, 'away': game.away,
           'home_score': int(game.home_score), 'away_score': int(game.away_score),
           **{f'home_{k}': v for k, v in h.items()}, **{f'away_{k}': v for k, v in a.items()},
           'possessions': round(possessions(h, a), 2), 'box_source': 'hoopr'}
    minutes = [{'game_id': gid, 'team': r['team_abbreviation'], 'player_id': str(r['athlete_id']),
                'minutes': 0 if (bool(r.get('did_not_play')) or pd.isna(r['minutes'])) else int(r['minutes'])}
               for _, r in pb.iterrows()]
    return row, minutes


def minute_rows(raw: Json, gid: str) -> list[dict[str, Any]]:
    """Every listed player's minutes. ESPN lists a player who did not play
    with no stats; he gets 0."""
    out = []
    for team in (raw.get('boxscore') or {}).get('players') or []:
        abbr = (team.get('team') or {}).get('abbreviation')
        for block in team.get('statistics') or []:
            keys = block.get('names') or block.get('keys') or []
            at = keys.index('MIN') if 'MIN' in keys else (keys.index('minutes') if 'minutes' in keys else None)
            if at is None:
                raise HistoryError(f'game {gid} {abbr}: no minutes column')
            for a in block.get('athletes') or []:
                stats = a.get('stats') or []
                try:
                    minutes = int(stats[at]) if stats and not a.get('didNotPlay') else 0
                except (ValueError, IndexError):
                    minutes = 0
                out.append({'game_id': gid, 'team': abbr, 'player_id': str((a.get('athlete') or {}).get('id')),
                            'minutes': minutes})
    if not out:
        raise HistoryError(f'game {gid}: no players listed')
    return out


def boxscores(season: int, get: Callable[[str], bytes] = fetch,
              schedule: pd.DataFrame | None = None, pause: float = 0.05,
              fallback: tuple[pd.DataFrame, pd.DataFrame] | None = None,
              ) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """(games, minutes, skipped) for every final game of a season. A game
    whose ESPN box score is empty is read from `fallback` (hoopR's team_box
    and player_box); one neither has is skipped, and `skipped` says which."""
    sched = schedule if schedule is not None else nba_schedule.load_schedule(season)
    finals = sched[sched['status'] == 'final']
    cache = nba_schedule.cache_dir()
    games, minutes, skipped = [], [], []
    for g in finals.itertuples():
        raw_path = cache / 'box' / str(season) / f'{g.game_id}.json' if cache is not None else None
        if raw_path is not None and raw_path.exists():
            raw = json.loads(raw_path.read_bytes())
        else:
            raw = json.loads(get(SUMMARY.format(gid=g.game_id)))
            raw = {k: raw.get(k) for k in ('boxscore', 'header')}
            if raw_path is not None:
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_path.write_text(json.dumps(raw), encoding='utf-8')
            if pause:
                time.sleep(pause)
        if espn_box_empty(raw):
            found = fallback_rows(g, *fallback) if fallback is not None else None
            if found is None:
                skipped.append(f'game {g.game_id} ({g.slate}, {g.away} at {g.home}): '
                               'ESPN\'s box score is empty and the fallback has none')
                continue
            games.append(found[0])
            minutes.extend(found[1])
            continue
        games.append(game_row(raw, g))
        minutes.extend(minute_rows(raw, str(g.game_id)))
    return (pd.DataFrame(games, columns=list(GAME_FIELDS)),
            pd.DataFrame(minutes, columns=list(MINUTE_FIELDS)), skipped)


def fallback_disagreements(games: pd.DataFrame, team_box: pd.DataFrame) -> tuple[int, list[str]]:
    """(games compared, a sentence for each game whose points or field-goal
    attempts differ) against hoopR's team_box for the same season."""
    tb = team_box.assign(game_id=team_box['game_id'].astype(str))
    side = tb.pivot_table(index='game_id', columns='team_home_away',
                          values=['team_score', 'field_goals_attempted'], aggfunc='first')
    side.columns = [f'fb_{stat}_{ha}' for stat, ha in side.columns]
    own = games[games['box_source'] == 'espn'] if 'box_source' in games else games
    both = own.set_index('game_id').join(side, how='inner')
    out = []
    for gid, r in both.iterrows():
        ours = (r.home_score, r.away_score, r.home_fga, r.away_fga)
        theirs = (r.fb_team_score_home, r.fb_team_score_away,
                  r.fb_field_goals_attempted_home, r.fb_field_goals_attempted_away)
        if tuple(float(x) for x in ours) != tuple(float(x) for x in theirs):
            out.append(f'game {gid}: ESPN {ours}, fallback {tuple(int(x) for x in theirs)}')
    return len(both), out


def check_against_fallback(games: pd.DataFrame, team_box: pd.DataFrame) -> list[str]:
    """Empty when the season meets the registration's floor; otherwise the
    reason and every disagreement."""
    n, bad = fallback_disagreements(games, team_box)
    if n == 0:
        return ['the fallback has none of this season\'s games']
    if (n - len(bad)) / n < AGREEMENT:
        return [f'points and field-goal attempts agree on {n - len(bad)} of {n} games, under {AGREEMENT:.0%}', *bad]
    return []


def implied(price: float) -> float:
    """The probability an American price implies, margin included."""
    return 100 / (price + 100) if price > 0 else -price / (-price + 100)


def _num(value: Any) -> float | None:
    try:
        return float(str(value).replace('+', ''))
    except (TypeError, ValueError):
        return None


def market_row(odds: Json, game: Any) -> dict[str, Any] | None:
    """The home team's two-way probability from ESPN's odds for one game, or
    None when ESPN has no usable price. The closing price is used where ESPN
    gives one; a provider marked live is never used."""
    for it in odds.get('items') or []:
        provider = str((it.get('provider') or {}).get('name') or '')
        if 'live' in provider.lower():
            continue
        h, a = it.get('homeTeamOdds') or {}, it.get('awayTeamOdds') or {}
        close_h = _num(((h.get('close') or {}).get('moneyLine') or {}).get('american'))
        close_a = _num(((a.get('close') or {}).get('moneyLine') or {}).get('american'))
        closing = close_h is not None and close_a is not None
        hp, ap = (close_h, close_a) if closing else (_num(h.get('moneyLine')), _num(a.get('moneyLine')))
        if hp is None or ap is None or abs(hp) < 100 or abs(ap) < 100:
            # No American price lies between -100 and +100: ESPN writes 0
            # for a price it does not have.
            continue
        ih, ia = implied(hp), implied(ap)
        return {'game_id': str(game.game_id), 'season': int(game.season), 'home': game.home, 'away': game.away,
                'provider': provider, 'home_price': hp, 'away_price': ap, 'closing': closing,
                'home_prob': round(ih / (ih + ia), 6)}
    return None


def market(season: int, sched: pd.DataFrame, get: Callable[[str], bytes] = fetch,
           pause: float = 0.05) -> pd.DataFrame:
    rows = []
    for g in sched[sched['status'] == 'final'].itertuples():
        row = market_row(json.loads(get(ODDS.format(e=g.game_id))), g)
        if row is not None:
            rows.append(row)
        if pause:
            time.sleep(pause)
    return pd.DataFrame(rows, columns=list(MARKET_FIELDS))


def write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    df.to_csv(tmp, index=False, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
    tmp.replace(path)


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    ap.add_argument('first', type=int)
    ap.add_argument('last', type=int)
    args = ap.parse_args(list(argv) if argv is not None else None)
    for season in range(args.first, args.last + 1):
        sched = nba_schedule.load_schedule(season)
        games_path = HISTORY / f'games_{season}.csv'
        if not games_path.exists():
            team_box = pd.read_parquet(io.BytesIO(fetch(FALLBACK.format(end_year=season + 1))))
            player_box = pd.read_parquet(io.BytesIO(fetch(PLAYER_FALLBACK.format(end_year=season + 1))))
            games, minutes, skipped = boxscores(season, get=fetch, schedule=sched, fallback=(team_box, player_box))
            problems = check_against_fallback(games, team_box)
            if problems:
                raise HistoryError(f'{season}: ' + '; '.join(problems[:20]))
            write(minutes, HISTORY / f'minutes_{season}.csv')
            write(pd.DataFrame({'note': skipped}), HISTORY / f'skipped_{season}.csv')
            write(games, games_path)
            from_fallback = int((games['box_source'] == 'hoopr').sum())
            print(f'{season}: {len(games)} games ({from_fallback} from the fallback, {len(skipped)} skipped), '
                  f'{len(minutes)} player rows; the fallback agrees', flush=True)
        market_path = HISTORY / f'market_{season}.csv'
        if not market_path.exists():
            m = market(season, sched)
            write(m, market_path)
            print(f'{season}: {len(m)} games priced', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
