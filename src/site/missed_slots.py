"""A second missed-slot detector, run by the page build (Stage 93 item 20, audit 7 R10).

The day sports lock a game at the last run before it starts, so a run that
never happened -- cron-job.org's dispatch lost and GitHub's copy hours late or
dropped -- leaves games started with no pick. The daily run's own MISSED PICKS
line cannot say so when the run is the thing that is missing. The Pages build
runs on every push to main, from any workflow, so it looks too:

- the sport's schedule file was refreshed today or yesterday (US Eastern), and
- every game that started in the last `WINDOW_HOURS` hours, and is not
  postponed or cancelled, has a saved pick.

It raises one alert per sport and never refuses the build (Mark, 2026-11-05):
the page that publishes is still the truest one there is.

    python -m src.site.missed_slots [--alert --run-url URL]
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from src.core import alerts

ROOT = Path(__file__).resolve().parents[2]
SPORTS = ('nhl', 'nba')
WINDOW_HOURS = 36
EASTERN = 'America/New_York'
NOT_PLAYED = {'postponed', 'cancelled', 'suspended'}


def title(sport: str) -> str:
    return f'{sport.upper()}: a daily run slot went missing'


def findings(sport: str, now: datetime, root: Path = ROOT) -> list[str]:
    """What the page build sees that only a missing run explains, for one sport."""
    files = sorted((root / 'results' / sport).glob('schedule_*.json'))
    if not files:
        return []
    season = files[-1].stem.split('_')[1]
    sched = json.loads(files[-1].read_text(encoding='utf-8'))
    out = []
    today = pd.Timestamp(now).tz_convert(EASTERN).date()
    as_of = datetime.strptime(sched.get('as_of') or '1970-01-01', '%Y-%m-%d').date()
    if as_of < today - timedelta(days=1):
        out.append(f'the schedule was last refreshed {as_of}, and today is {today} (US Eastern): '
                   'no daily run has finished since')
    picks = root / 'predictions' / sport / season
    since = now - timedelta(hours=WINDOW_HOURS)
    for g in sched.get('games') or []:
        start = datetime.strptime(g['start_utc'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=UTC)
        if since <= start <= now and g.get('status') not in NOT_PLAYED and not (picks / f"{g['game_id']}.json").exists():
            out.append(f"game {g['game_id']} ({g['away']} at {g['home']}, {g['start_utc']}) started with no pick saved")
    return out


def main(argv: list[str] | None = None, now: datetime | None = None, root: Path = ROOT) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--alert', action='store_true', help='raise or close each sport\'s issue')
    ap.add_argument('--run-url', default='')
    args = ap.parse_args(argv)
    now = now or datetime.now(UTC)
    for sport in SPORTS:
        found = findings(sport, now, root)
        for line in found:
            print(f'MISSED SLOT: {sport.upper()}: {line}')
        if not args.alert:
            continue
        if found:
            body = (f'The page build ({args.run_url}) found what only a missing {sport.upper()} daily run '
                    'explains:\n\n' + '\n'.join(f'- {line}' for line in found) +
                    '\n\nThe page still published. A game with no pick cannot be picked now; '
                    'check the daily run\'s schedule and cron-job.org.')
            alerts.open_or_comment(title(sport), body)
        else:
            alerts.close_open_issue(title(sport), f'Recovered: the page build at {args.run_url} found nothing missing.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
