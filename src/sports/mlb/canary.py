"""MLB's nightly canary: read every source the daily run reads, one at a time, and keep none (Stage 98 item 2, made
per-source in Stage 101 item 4).

The NFL's canary exists because an upstream change crashed a locking run with no warning (PR #6); the NHL's and the
NBA's run every night for the same reason. `experiments/mlb/stage101/registry.json` (`canary`) registers MLB's: every
night, each source the daily run reads is read once on its own, judged on the shape the run needs, and named in the
report. As the NBA's does, the workflow raises one issue per failing source ("MLB: ESPN odds failing in the nightly
canary"), so a source that recovers does not hide another that has not.

1. **Stats API schedule**: this season's schedule, through `schedule.load_schedule` (its own checks, the clubs'
   venues included), and today's slate.
2. **Stats API probable pitchers**: today's, through `schedule.probables`. None named on a day with games is noted,
   not failed: clubs name them a day or more ahead.
3. **Stats API box score**: the newest final's, through `history.pitcher_rows`, the read the daily run adds this
   season's games with: each club's pitchers, the first the starter, with outs and runs. The newest few finals are
   tried; none usable is a failure. Before this season's first final, the newest stored finals of last season.
4. **ESPN odds**: the next scheduled games within a week, matched to ESPN's scoreboard (`market.espn_match`) and
   priced by `market.espn_price`. None of them priced is a failure; no game in the next week is not (the winter).
5. **Kalshi**: the game markets, through `market.kalshi_prices`. Kalshi is the fallback, so a night with no quoted
   game is noted, not failed; a feed that cannot be read or has no market list is a failure.

A check that needs the schedule and finds it unreadable says so rather than raising a second error about the same
cause.

    python -m src.sports.mlb.canary [--report mlb-canary-report.md] [--failed mlb-canary-failed.txt]
"""
from __future__ import annotations

import argparse
import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.sport import GameStatus
from src.sports.mlb import history, market
from src.sports.mlb import schedule as mlb_schedule

Check = Callable[[dict[str, Any]], str]
#: How many of the newest finals one night looks through for a usable box score.
LOOKBACK = 5
#: How many upcoming games the odds check reads.
ODDS_SAMPLE = 3
SOURCES = ('Stats API schedule', 'Stats API probable pitchers', 'Stats API box score', 'ESPN odds', 'Kalshi')


class Skipped(Exception):
    """The check depends on a read that already failed tonight."""


def today(state: dict[str, Any]) -> str:
    return str(pd.Timestamp(state['now']).tz_convert('America/New_York').strftime('%Y-%m-%d'))


def _schedule(state: dict[str, Any]) -> pd.DataFrame:
    if state.get('schedule') is None:
        raise Skipped('the schedule could not be read tonight')
    sched: pd.DataFrame = state['schedule']
    return sched


def check_schedule(state: dict[str, Any]) -> str:
    season = mlb_schedule.current_season(state['now'])
    state['schedule'] = mlb_schedule.load_schedule(season, get=state['get'], cache=None, now=state['now'])
    day = mlb_schedule.slate(state['schedule'], today(state))
    counts = day['status'].value_counts().to_dict()
    slate = (', '.join(f'{v} {k}' for k, v in sorted(counts.items())) if counts
             else 'no game (not an error)')
    return f'{len(state["schedule"])} games in {season}; {today(state)}: {slate}'


def check_probables(state: dict[str, Any]) -> str:
    named = mlb_schedule.probables(state['get'](mlb_schedule.DAY.format(day=today(state))))
    both = sum(1 for h, a in named.values() if h and a)
    return f'{both} of {len(named)} games on {today(state)} name both probable pitchers'


def _newest_finals(state: dict[str, Any]) -> list[str]:
    sched = _schedule(state)
    finals = sched[sched['status'] == GameStatus.FINAL.value].sort_values('start_utc', ascending=False)
    if not finals.empty:
        return [str(g) for g in finals['game_id'].head(LOOKBACK)]
    season = mlb_schedule.current_season(state['now'])
    past = pd.read_csv(history.HISTORY / f'games_{season - 1}.csv', dtype={'game_id': str})
    return [str(g) for g in past.sort_values('start_utc', ascending=False)['game_id'].head(LOOKBACK)]


def check_box_score(state: dict[str, Any]) -> str:
    problems: list[str] = []
    for gid in _newest_finals(state):
        try:
            rows = history.pitcher_rows(state['get'](history.BOX.format(gid=gid)), gid)
        except history.HistoryError as exc:
            problems.append(str(exc))
            continue
        return f'game {gid}: {len(rows)} pitcher lines, both starters'
    raise ValueError(f'none of the newest {LOOKBACK} finals has a usable box score: ' + '; '.join(problems))


def check_odds(state: dict[str, Any]) -> str:
    sched = _schedule(state)
    now = pd.Timestamp(state['now']).tz_convert('UTC')
    ahead = sched[(sched['status'] == GameStatus.SCHEDULED.value) & (sched['start_utc'] > now)
                  & (sched['start_utc'] < now + pd.Timedelta(days=7))].head(ODDS_SAMPLE)
    if ahead.empty:
        return 'no game scheduled in the next week (not an error)'
    priced = []
    for day, games in ahead.groupby('slate', sort=True):
        board = state['get'](market.SCOREBOARD.format(day=str(day).replace('-', '')))
        matched, _ = market.espn_match(games, market.espn_events(board))
        for gid, (espn_id, swapped) in matched.items():
            if market.espn_price(state['get'](market.ESPN_ODDS.format(e=espn_id)), swapped) is not None:
                priced.append(gid)
    if not priced:
        raise ValueError(f'ESPN priced none of the next {len(ahead)} games ({", ".join(ahead["game_id"])})')
    return f'{len(priced)} of the next {len(ahead)} games priced'


def check_kalshi(state: dict[str, Any]) -> str:
    feed = state['get'](market.KALSHI)
    if not isinstance(feed.get('markets'), list):
        raise ValueError('no market list')
    return f'{len(market.kalshi_prices(feed))} games quoted on both sides (fallback only)'


CHECKS: list[tuple[str, Check]] = list(zip(SOURCES, (check_schedule, check_probables, check_box_score, check_odds,
                                                     check_kalshi), strict=True))


def run(now: datetime, get: Callable[[str], Any] = mlb_schedule.fetch_json,
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
         get: Callable[[str], Any] = mlb_schedule.fetch_json) -> int:
    ap = argparse.ArgumentParser(description='The MLB nightly canary')
    ap.add_argument('--report', default=None)
    ap.add_argument('--failed', default=None, help='write each failing source on its own line')
    args = ap.parse_args(argv)
    failed, notes = run(now or datetime.now(UTC), get)
    text = '# MLB nightly canary\n\n' + '\n'.join(f'- {n}' for n in notes) + '\n'
    print(text)
    if args.report:
        Path(args.report).write_text(text, encoding='utf-8')
    if args.failed:
        Path(args.failed).write_text(''.join(f'{f}\n' for f in failed), encoding='utf-8')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
