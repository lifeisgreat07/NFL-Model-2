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

Stage 81 item 2: after the Weekly update locks, `--after-lock --season S` looks
for an override pull request that is still open for a week whose picks are now
saved, and raises "NFL: <season> week <N> locked while its QB override was
unmerged". The lock is final, so this cannot change a pick; it makes the cost
visible the same morning instead of when someone reads the week's QB notes.

    python -m src.sports.nfl.override_watch --after-lock --season 2026
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

from src.core import alerts
from src.sports.nfl.paths import PRED_DIR

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


def locked_title(season: int, week: int) -> str:
    return f'NFL: {season} week {week} locked while its QB override was unmerged'


def locked_while_open(season: int, open_prs: Iterable[dict], pred_dir: Path = PRED_DIR) -> list[tuple[int, int, str]]:
    """(week, pr number, url) for every open pull request carrying an override
    for a week of `season` whose locked picks file already exists."""
    found = []
    for pr in open_prs:
        paths = [f.get('path', '') for f in pr.get('files') or []]
        for s, week in override_weeks(paths):
            if s == season and (pred_dir / f'{season}_week{week}.json').exists():
                found.append((week, int(pr['number']), str(pr.get('url', ''))))
    return sorted(found)


def after_lock(season: int, run: alerts.Run = subprocess.run, pred_dir: Path = PRED_DIR) -> list[str]:
    out = run(['gh', 'pr', 'list', '--state', 'open', '--limit', '100', '--json', 'number,url,files'],
              capture_output=True, text=True)
    if out.returncode:
        raise RuntimeError(f'gh pr list failed: {(out.stderr or out.stdout).strip()}')
    lines = []
    for week, number, url in locked_while_open(season, json.loads(out.stdout or '[]'), pred_dir):
        body = (f'Week {week} of {season} is locked, and pull request #{number} ({url}) with its QB '
                'overrides was still open, so the picks were made without them. A lock is never '
                'rewritten. Merge or close the pull request; the week\'s QB notes on the page say '
                'which starter each pick used.')
        action, ref = alerts.open_or_comment(locked_title(season, week), body, run)
        lines.append(f'{action}: {ref} ({locked_title(season, week)})')
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='Alert while a QB override pull request is open.')
    ap.add_argument('--after-lock', action='store_true', help='check for overrides left open at the lock')
    ap.add_argument('--season', type=int)
    ap.add_argument('--event')
    ap.add_argument('--pr', type=int)
    ap.add_argument('--url')
    ap.add_argument('--merged', choices=('true', 'false'))
    ap.add_argument('--files-file')
    args = ap.parse_args(argv)
    if args.after_lock:
        if args.season is None:
            ap.error('--after-lock needs --season')
        lines = after_lock(args.season)
        print('\n'.join(lines) if lines else f'No QB override pull request was open for a locked {args.season} week.')
        return 0
    if None in (args.event, args.pr, args.url, args.merged, args.files_file):
        ap.error('--event, --pr, --url, --merged and --files-file are required without --after-lock')
    paths = Path(args.files_file).read_text(encoding='utf-8').splitlines()
    lines = handle(args.event, args.pr, args.url, args.merged == 'true', paths)
    if not lines:
        print(f'#{args.pr} touches no override file this watch reads', file=sys.stderr)
    for line in lines:
        print(line)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
