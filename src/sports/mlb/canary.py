"""MLB's nightly canary: run the reads the daily run will make, every night, and keep none (Stage 98 item 2).

The NFL's canary exists because an upstream change crashed a locking run with no warning (PR #6); the NHL's and
the NBA's run every night for the same reason. MLB's daily run is Stage 101's, but its reads are fixed now, so the
canary can watch them through the winter and spring training before a pick depends on them. Each step is one read,
judged on the shape the run needs; a step that raises is recorded and the rest still run, so one report names
everything wrong tonight.

1. this season's schedule, through `schedule.load_schedule` (its own checks, the clubs' venues included);
2. today's slate and the status of each game;
3. the newest final's box score: both clubs' runs and a first pitcher, the starter;
4. today's probable pitchers, through `schedule.probables` (none named on a day with games is reported, not
   failed: the clubs name them a day or more ahead, and when is measured in spring training).

Exit 1 on any error. The workflow that schedules it waits for MLB's daily run (Stage 101).

    python -m src.sports.mlb.canary [--report mlb-canary-report.md]
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
from src.sports.mlb import schedule as mlb_schedule

Step = Callable[[dict[str, Any]], str]
BOX = mlb_schedule.STATS + '/game/{gid}/boxscore'
#: How many of the newest finals one night looks through for a box score with both clubs' pitchers.
LOOKBACK = 5


def today(state: dict[str, Any]) -> str:
    return str(pd.Timestamp(state['now']).tz_convert('America/New_York').strftime('%Y-%m-%d'))


def step_schedule(state: dict[str, Any]) -> str:
    season = mlb_schedule.current_season(state['now'])
    state['schedule'] = mlb_schedule.load_schedule(season, get=state['get'], cache=None, now=state['now'])
    return f'{len(state["schedule"])} games in {season}'


def step_slate(state: dict[str, Any]) -> str:
    day = mlb_schedule.slate(state['schedule'], today(state))
    if day.empty:
        return f'no game on {today(state)} (not an error)'
    counts = day['status'].value_counts().to_dict()
    return f'{today(state)}: ' + ', '.join(f'{v} {k}' for k, v in sorted(counts.items()))


def box_problems(data: Any) -> list[str]:
    teams = (data or {}).get('teams') or {}
    out = []
    for side in ('home', 'away'):
        t = teams.get(side) or {}
        runs = ((t.get('teamStats') or {}).get('batting') or {}).get('runs')
        if not isinstance(runs, int):
            out.append(f'{side}: no runs')
        if not t.get('pitchers'):
            out.append(f'{side}: no pitchers, so no starter')
    return out


def step_box_score(state: dict[str, Any]) -> str:
    sched = state['schedule']
    finals = sched[sched['status'] == GameStatus.FINAL.value].sort_values('start_utc', ascending=False)
    if finals.empty:
        return 'no final game yet this season (not an error)'
    problems: list[str] = []
    for gid in finals['game_id'].head(LOOKBACK):
        bad = box_problems(state['get'](BOX.format(gid=gid)))
        if not bad:
            return f'game {gid}: both clubs\' runs and starters'
        problems.append(f'game {gid}: ' + ', '.join(bad))
    raise ValueError(f'none of the newest {LOOKBACK} finals has a usable box score: ' + '; '.join(problems))


def step_probables(state: dict[str, Any]) -> str:
    named = mlb_schedule.probables(state['get'](mlb_schedule.DAY.format(day=today(state))))
    both = sum(1 for h, a in named.values() if h and a)
    return f'{both} of {len(named)} games on {today(state)} name both probable pitchers'


STEPS: list[tuple[str, Step]] = [
    ('schedule', step_schedule), ('slate', step_slate), ('box score', step_box_score),
    ('probables', step_probables),
]


def run(now: datetime, get: Callable[[str], Any] = mlb_schedule.fetch_json,
        steps: list[tuple[str, Step]] | None = None) -> tuple[list[str], list[str]]:
    """(errors, notes) for one night."""
    state: dict[str, Any] = {'now': now, 'get': get}
    errors, notes = [], []
    for name, step in steps or STEPS:
        try:
            notes.append(f'{name}: {step(state)}')
        except Exception as exc:  # the crash is the finding
            errors.append(f'{name} raised {type(exc).__name__}: {exc}')
            notes.append(f'{name}: FAILED\n\n```\n{traceback.format_exc(limit=3)}```')
    return errors, notes


def main(argv: list[str] | None = None, now: datetime | None = None,
         get: Callable[[str], Any] = mlb_schedule.fetch_json) -> int:
    ap = argparse.ArgumentParser(description='The MLB nightly canary')
    ap.add_argument('--report', default=None)
    args = ap.parse_args(argv)
    errors, notes = run(now or datetime.now(UTC), get)
    text = '# MLB nightly canary\n\n' + '\n'.join(f'- {n}' for n in notes) + '\n'
    if errors:
        text += '\n## Errors\n\n' + '\n'.join(f'- {e}' for e in errors) + '\n'
    print(text)
    if args.report:
        Path(args.report).write_text(text, encoding='utf-8')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
