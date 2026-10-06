"""The NHL's nightly canary: run the daily run's reads every night and keep none.

The NFL's canary exists because an upstream change crashed a locking run
with no warning (PR #6). The NHL's runs lock every day, so a source that
breaks matters the same day. Each step below is one read the daily run
makes, judged on the shape the run needs; a step that raises is recorded
and the rest still run, so one report names everything wrong tonight.

1. this season's schedule, through `schedule.load_schedule` (its own checks);
2. yesterday's and today's slates, through the lock rule;
3. a final game's box score, through `history.box_row`;
4. the league's odds feed, through `market.parse`;
5. Daily Faceoff's page for today, through `goalies.parse_faceoff`;
6. a club's roster, through `roster.goalies_of`.

Exit 1 on any error. The workflow that schedules this, and turns a failure
into an issue titled "NHL: ...", waits for Stage 52, which moves the alert
code into the core.

    python -m src.sports.nhl.canary [--report nhl-canary-report.md]
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
from src.sports.nhl import goalies, history, market, roster
from src.sports.nhl import schedule as nhl_schedule
from src.sports.nhl.lock import GameLock

Step = Callable[[dict[str, Any]], str]


def step_schedule(state: dict[str, Any]) -> str:
    season = nhl_schedule.current_season(state['now'])
    state['schedule'] = nhl_schedule.load_schedule(season, get=lambda u: json.loads(state['get'](u)))
    return f'{len(state["schedule"])} games in {season}'


def step_lock(state: dict[str, Any]) -> str:
    sched = state['schedule']
    today = pd.Timestamp(state['now']).tz_convert('America/New_York').strftime('%Y-%m-%d')
    d = GameLock().decide(sched[sched['slate'] == today], state['now'])
    return f'today: lock {len(d.lock)}, hold {len(d.hold)}, started {len(d.started)}'


def step_box_score(state: dict[str, Any]) -> str:
    finals = state['schedule'][state['schedule']['status'] == GameStatus.FINAL.value]
    if finals.empty:
        return 'no final game yet this season (not an error)'
    g = finals.iloc[-1]
    row = history.box_row(json.loads(state['get'](history.BOX.format(gid=g['game_id']))), str(g['game_type']))
    return f'game {row["game_id"]}: shots {row["home_sog"]}-{row["away_sog"]}, both starters flagged'


def step_market(state: dict[str, Any]) -> str:
    rows, missing = market.parse(json.loads(state['get'](market.SOURCE)), state['now'])
    if missing:
        raise ValueError('; '.join(missing))
    return f'{len(rows)} games priced'


def step_goalies(state: dict[str, Any]) -> str:
    day = pd.Timestamp(state['now']).tz_convert('America/New_York').strftime('%Y-%m-%d')
    rows = goalies.parse_faceoff(state['get'](f'{goalies.SOURCE}/{day}').decode('utf-8', 'replace'), state['now'])
    attached = goalies.attach_games(rows, state['schedule'][state['schedule']['slate'] == day].to_dict('records'))
    return f'{len(attached)} games with projected goalies'


def step_roster(state: dict[str, Any]) -> str:
    gs = roster.goalies_of(json.loads(state['get'](roster.ROSTER.format(club='TOR'))))
    if not gs:
        raise ValueError('a roster with no goalies')
    return f'{len(gs)} goalies on a roster'


STEPS: list[tuple[str, Step]] = [
    ('schedule', step_schedule), ('lock', step_lock), ('box score', step_box_score),
    ('market', step_market), ('goalies', step_goalies), ('roster', step_roster),
]


def run(now: datetime, get: Callable[[str], bytes] = history.fetch,
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
         get: Callable[[str], bytes] = history.fetch) -> int:
    ap = argparse.ArgumentParser(description='The NHL nightly canary')
    ap.add_argument('--report', default=None)
    args = ap.parse_args(argv)
    errors, notes = run(now or datetime.now(UTC), get)
    text = '# NHL nightly canary\n\n' + '\n'.join(f'- {n}' for n in notes) + '\n'
    if errors:
        text += '\n## Errors\n\n' + '\n'.join(f'- {e}' for e in errors) + '\n'
    print(text)
    if args.report:
        Path(args.report).write_text(text, encoding='utf-8')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
