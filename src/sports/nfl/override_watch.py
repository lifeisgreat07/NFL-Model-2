"""
Tell a person when a QB override pull request is waiting to merge (Stage 81 item 1).

The Weekly update locks a week's picks on Thursday at 11:00 UTC and reads only the
override files already on `main` (`load_qb_overrides`). Mark's QB routine opens its
pull request on Wednesday at 22:00 UTC, so the window to merge it is about thirteen
hours, most of them overnight. In 2026 weeks 7 and 8 it closed with #530 and #542
still open, and the picks locked with Jalen Hurts, out for the season, as PHI's
starter. Nothing had said the pull request was waiting.

This runs on the pull request's own events rather than on a schedule: GitHub's
cron starts hours late (see `docs/traps.md`), and an issue opened the moment the
pull request appears gives the most time before the lock. When the pull request
is merged or closed, the issue is closed with a comment saying which.

One issue per week, titled by season and week, so a second pull request for the
same week comments on it rather than opening a twin (`src/core/alerts.py`).

    python -m src.sports.nfl.override_watch --event opened --pr 549 \
        --url https://github.com/o/r/pull/549 --merged false --files-file files.txt
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

from src.core import alerts

OVERRIDE_PATH = re.compile(r'^data/nfl/qb_overrides/(\d{4})_week(\d{1,2})\.json$')
OPENING = frozenset({'opened', 'reopened'})


def override_weeks(paths: Iterable[str]) -> list[tuple[int, int]]:
    """(season, week) for every override file the pull request touches, sorted."""
    weeks = set()
    for p in paths:
        m = OVERRIDE_PATH.match(p.strip())
        if m:
            weeks.add((int(m.group(1)), int(m.group(2))))
    return sorted(weeks)


def title(season: int, week: int) -> str:
    return f'NFL: {season} week {week} QB override waiting to merge'


def opened_body(season: int, week: int, pr: int, url: str) -> str:
    return (
        f'Pull request #{pr} ({url}) adds QB overrides for {season} week {week}.\n\n'
        'The Weekly update locks the week at **Thursday 11:00 UTC** and reads only override files '
        'already merged into `main`. If this pull request is still open then, every override in it '
        "is ignored and the picks lock with the schedule's listed starter. That is what happened in "
        'weeks 7 and 8 (#530, #542).\n\n'
        'To act on it: open the pull request, read Booth\'s audit comment, and merge it if the '
        'overrides are right. This issue closes itself when the pull request is merged or closed.'
    )


def closed_body(pr: int, merged: bool) -> str:
    if merged:
        return f'#{pr} was merged, so its overrides are on `main` for the next lock. Closing.'
    return (f'#{pr} was closed without merging, so its overrides will not be used. Closing; '
            'a new override pull request for the week opens a fresh issue.')


def handle(event: str, pr: int, url: str, merged: bool, paths: Iterable[str],
           run: alerts.Run = subprocess.run) -> list[str]:
    """Act on one pull request event. Returns one line per week acted on."""
    done = []
    for season, week in override_weeks(paths):
        t = title(season, week)
        if event in OPENING:
            action, ref = alerts.open_or_comment(t, opened_body(season, week, pr, url), run)
            done.append(f'{action}: {ref} ({t})')
        elif event == 'closed':
            number = alerts.close_open_issue(t, closed_body(pr, merged), run)
            done.append(f'closed: {number} ({t})' if number is not None else f'no open issue ({t})')
    return done


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='Alert while a QB override pull request is open.')
    ap.add_argument('--event', required=True)
    ap.add_argument('--pr', required=True, type=int)
    ap.add_argument('--url', required=True)
    ap.add_argument('--merged', required=True, choices=('true', 'false'))
    ap.add_argument('--files-file', required=True)
    args = ap.parse_args(argv)
    paths = Path(args.files_file).read_text(encoding='utf-8').splitlines()
    lines = handle(args.event, args.pr, args.url, args.merged == 'true', paths)
    if not lines:
        print(f'#{args.pr} touches no override file this watch reads', file=sys.stderr)
    for line in lines:
        print(line)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
