"""The NBA's nightly canary: read every source the daily run reads, one at a
time, and keep none (Stage 65).

The NHL's canary (`src/sports/nhl/canary.py`) runs its steps in a chain and
raises one alert for the night. The NBA's live run rests on five outside
reads, and Stage 65's registration names each, so this canary judges each
source on its own and the workflow raises one issue per failing source
("NBA: ESPN odds failing in the nightly canary"). A source that breaks is
then named in the issue's title, and one that recovers does not hide
another that has not.

Each check reads what the daily run reads and judges it on the shape the
run needs:

1. **ESPN scoreboard**: this season's schedule, through `schedule.load_schedule`.
2. **ESPN box score**: the latest final game's, through `history.game_row`
   and `history.minute_rows` (this season's, else last season's last game).
3. **ESPN odds**: the next scheduled games within a week, through
   `market.espn_price`; none of them priced is a failure, no game scheduled
   is not.
4. **ESPN injuries**: the report, through `injuries.parse`.
5. **Kalshi**: the game markets, through `market.kalshi_prices`. Kalshi is
   the fallback, so a night with no quoted game is noted, not failed; a
   feed that cannot be read or has no market list is a failure.

A check that needs the schedule and finds it unreadable says so rather
than raising a second error about the same cause.

    python -m src.sports.nba.canary [--report nba-canary-report.md] [--failed nba-canary-failed.txt]
"""
from __future__ import annotations

import argparse
import json
import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.sport import GameStatus
from src.sports.nba import history, injuries, market
from src.sports.nba import schedule as nba_schedule

Check = Callable[[dict[str, Any]], str]
#: How many upcoming games the odds check reads.
ODDS_SAMPLE = 3


class Skipped(Exception):
    """The check depends on a read that already failed tonight."""


def _schedule(state: dict[str, Any]) -> pd.DataFrame:
    if state.get('schedule') is None:
        raise Skipped('the schedule could not be read tonight')
    sched: pd.DataFrame = state['schedule']
    return sched


def check_scoreboard(state: dict[str, Any]) -> str:
    season = nba_schedule.current_season(state['now'])
    state['schedule'] = nba_schedule.load_schedule(season, get=lambda u: json.loads(state['get'](u)))
    return f'{len(state["schedule"])} games in {season}'


def _last_final(state: dict[str, Any]) -> Any:
    sched = _schedule(state)
    finals = sched[sched['status'] == GameStatus.FINAL.value]
    if not finals.empty:
        return finals.iloc[-1]
    season = int(sched['season'].iloc[0]) if len(sched) else nba_schedule.current_season(state['now'])
    past = pd.read_csv(history.HISTORY / f'games_{season - 1}.csv', dtype={'game_id': str})
    row = past.iloc[-1]
    return pd.Series({'game_id': row['game_id'], 'season': season - 1, 'slate': row['slate'],
                      'game_type': row['game_type'], 'neutral_site': row['neutral_site'],
                      'home': row['home'], 'away': row['away'],
                      'home_score': row['home_score'], 'away_score': row['away_score']})


def check_box_score(state: dict[str, Any]) -> str:
    g = _last_final(state)
    raw = json.loads(state['get'](history.SUMMARY.format(gid=g['game_id'])))
    row = history.game_row(raw, g)
    players = history.minute_rows(raw, str(g['game_id']))
    return f'game {row["game_id"]} ({g["slate"]}): {row["possessions"]} possessions, {len(players)} players'


def check_odds(state: dict[str, Any]) -> str:
    sched = _schedule(state)
    now = pd.Timestamp(state['now']).tz_convert('UTC')
    ahead = sched[(sched['status'] == GameStatus.SCHEDULED.value) & (sched['start_utc'] > now)
                  & (sched['start_utc'] < now + pd.Timedelta(days=7))].head(ODDS_SAMPLE)
    if ahead.empty:
        return 'no game scheduled in the next week (not an error)'
    priced = [gid for gid in ahead['game_id']
              if market.espn_price(json.loads(state['get'](market.ESPN_ODDS.format(e=gid)))) is not None]
    if not priced:
        raise ValueError(f'ESPN priced none of the next {len(ahead)} games ({", ".join(ahead["game_id"])})')
    return f'{len(priced)} of the next {len(ahead)} games priced'


def check_injuries(state: dict[str, Any]) -> str:
    sched = _schedule(state)
    rows = injuries.parse(json.loads(state['get'](injuries.SOURCE)), set(sched['home']) | set(sched['away']))
    out = sum(r['status'] == injuries.OUT for r in rows)
    return f'{len(rows)} players listed, {out} Out'


def check_kalshi(state: dict[str, Any]) -> str:
    feed = json.loads(state['get'](market.KALSHI))
    if not isinstance(feed.get('markets'), list):
        raise ValueError('no market list')
    games = market.kalshi_prices(feed)
    tight = 0
    for by_team in games.values():
        widest = max(s['ask'] - s['bid'] for s in by_team.values())
        tight += widest <= market.KALSHI_MAX_SPREAD + 1e-9
    return f'{len(games)} games quoted on both sides, {tight} within the registered spread (fallback only)'


CHECKS: list[tuple[str, Check]] = [
    ('ESPN scoreboard', check_scoreboard), ('ESPN box score', check_box_score),
    ('ESPN odds', check_odds), ('ESPN injuries', check_injuries), ('Kalshi', check_kalshi),
]


def run(now: datetime, get: Callable[[str], bytes] = history.fetch,
        checks: list[tuple[str, Check]] | None = None) -> tuple[list[str], list[str]]:
    """(the failing sources, a report line per source) for one night."""
    state: dict[str, Any] = {'now': now, 'get': get}
    failed, notes = [], []
    for name, check in checks or CHECKS:
        try:
            notes.append(f'{name}: {check(state)}')
        except Skipped as why:
            notes.append(f'{name}: not checked, {why}')
        except Exception as exc:  # the crash is the finding
            failed.append(name)
            notes.append(f'{name}: FAILED, {type(exc).__name__}: {exc}\n\n```\n{traceback.format_exc(limit=3)}```')
    return failed, notes


def main(argv: list[str] | None = None, now: datetime | None = None,
         get: Callable[[str], bytes] = history.fetch) -> int:
    ap = argparse.ArgumentParser(description='The NBA nightly canary')
    ap.add_argument('--report', default=None)
    ap.add_argument('--failed', default=None, help='write each failing source on its own line')
    args = ap.parse_args(argv)
    failed, notes = run(now or datetime.now(UTC), get)
    text = '# NBA nightly canary\n\n' + '\n'.join(f'- {n}' for n in notes) + '\n'
    print(text)
    if args.report:
        Path(args.report).write_text(text, encoding='utf-8')
    if args.failed:
        Path(args.failed).write_text(''.join(f'{f}\n' for f in failed), encoding='utf-8')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
