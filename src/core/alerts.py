"""
Tell a person when something automated goes wrong: open a GitHub issue, or
comment on the one already open.

The core's copy of `src/core/alerts.py`, for every sport's workflows.
The sports may not import the NFL's legacy package, and the NHL's daily
run, canary and drift check needed alerts before Stage 52 moves the NFL
onto the core. Until then the two files are the same module; Stage 52
points the NFL's workflows here and deletes the other.

Until Stage 4 every failure in this repository was silent in the same way: a
red run in the Actions tab that nobody was looking at. The Booth audits that
posted nothing were found by a session start-up checklist, days later. An
issue sends the owner a notification and stays open until someone closes it,
which is the property a failed run lacks.

One issue per problem, not one per occurrence. A canary that fails every night
for a week should produce one issue, not seven -- the second is how alert
fatigue starts. Within the issue, a report that repeats the latest post (run
links aside) raises a count on that post instead of adding a comment (Stage 83
item 1); a report that says something new is a new comment. Matching is on the exact title among
OPEN issues, so closing an issue is how you say "handled": the next failure
opens a fresh one.

Uses the `gh` CLI, which GitHub's runners carry, authenticated by GH_TOKEN.
The workflow step supplies that token and the `issues: write` permission; no
job that runs a model is given either.

    python -m src.core.alerts --title "NHL: nightly canary failing" --body-file report.md
    python -m src.core.alerts --title "NBA: daily run failed" --body-file failure.md --log nba-daily.log

`--log` appends the last lines of a step's log (Stage 81 item 5): a run's own
log needs a GitHub sign-in to read, so an alert that carried only a link left
the cause unknown until someone opened it (#529).

Every `gh` call is tried three times with a backoff, and an alert GitHub still
refuses is written to the step summary with an error annotation, and the step
exits 1 (Stage 93 item 12, audit 7 R8): before, one refused call lost the alert.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

Run = Callable[..., Any]


#: Seconds to wait before the second and third tries of a `gh` call (Stage 93
#: item 12). GitHub's API answers a burst of calls, or a moment of its own
#: trouble, with a 5xx or a secondary rate limit that clears in seconds; one
#: failed call used to lose the alert, and the run's own failure with it.
BACKOFF = (5.0, 20.0)
SLEEP: Callable[[float], Any] = time.sleep


def _gh(args: list[str], run: Run, stdin: str | None = None) -> str:
    """One `gh` call, tried up to three times. A create that reached GitHub
    but answered with an error could be tried again and open a twin; the
    repeat is caught the next time by the title match, and a twin is a far
    smaller harm than a lost alert."""
    for wait in (*BACKOFF, None):
        r = run(['gh'] + args, input=stdin, capture_output=True, text=True)
        if not r.returncode:
            out: str = r.stdout
            return out
        if wait is not None:
            SLEEP(wait)
    raise RuntimeError(f"gh {' '.join(args[:2])} failed {len(BACKOFF) + 1} times: {(r.stderr or r.stdout).strip()}")


def find_open_issue(title: str, run: Run = subprocess.run) -> int | None:
    """The number of the open issue with exactly this title, or None."""
    out = _gh(['issue', 'list', '--state', 'open', '--limit', '200',
               '--json', 'number,title'], run)
    for issue in json.loads(out or '[]'):
        if issue.get('title') == title:
            return int(issue['number'])
    return None


#: A link to one Actions run. Every run of a failing job writes its own, so a
#: report is "the same" as the last one when it differs only in these.
RUN_LINK = re.compile(r'https://github\.com/[\w.-]+/[\w.-]+/actions/runs/\d+[^\s)]*')
KEY_MARK = re.compile(r'<!-- alert-key: ([0-9a-f]{16}) -->')
REPEAT_LINE = re.compile(r'\n*<!-- alert-repeat n=(\d+) -->[^\n]*')
COMMENT_ID = re.compile(r'#issuecomment-(\d+)$')


def report_key(body: str) -> str:
    """What makes two reports the same: the text with its run links blanked."""
    return hashlib.sha256(RUN_LINK.sub('<run>', body.strip()).encode('utf-8')).hexdigest()[:16]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def latest_post(number: int, run: Run) -> tuple[str, str]:
    """The issue's most recent post, as (where, text): where is the comment's id,
    or 'body' when no one has commented. A comment whose id cannot be read
    is ('', text), which nothing will edit."""
    out = _gh(['issue', 'view', str(number), '--json', 'body,comments'], run)
    issue = json.loads(out or '{}')
    comments = issue.get('comments') or []
    if not comments:
        return 'body', issue.get('body') or ''
    last = comments[-1]
    m = COMMENT_ID.search(last.get('url') or '')
    return (m.group(1) if m else ''), last.get('body') or ''


def counted(post: str, body: str, now: datetime) -> str:
    """The post with its repeat line set one higher, naming the newest run."""
    m = REPEAT_LINE.search(post)
    n = int(m.group(1)) + 1 if m else 1
    rest = REPEAT_LINE.sub('', post).rstrip()
    link = RUN_LINK.search(body)
    where = link.group(0) if link else 'a run that gave no link'
    times = 'once' if n == 1 else f'{n} times'
    line = (f'<!-- alert-repeat n={n} -->Seen again with the same report {times}; '
            f'the latest: {where} ({now:%Y-%m-%d %H:%M} UTC).')
    return f'{rest}\n\n{line}'


def open_or_comment(title: str, body: str, run: Run = subprocess.run, key: str | None = None,
                    now: Callable[[], datetime] = _utc_now) -> tuple[str, int | str]:
    """Comment on the open issue with this title, or open one. Returns
    ('commented' | 'counted' | 'opened', issue reference).

    Stage 83 item 1: a report that repeats the issue's latest post, run links
    aside, raises the count on that post instead of adding a comment, so a
    failure that comes back every night is one post with a number, not a
    page of copies (#540 had 23). `key` is the text that decides "the same";
    it defaults to the body, and the CLI passes the body without its log tail,
    whose timestamps differ every run."""
    marked = f"{body}\n\n<!-- alert-key: {report_key(key if key is not None else body)} -->"
    number = find_open_issue(title, run)
    if number is None:
        out = _gh(['issue', 'create', '--title', title, '--body-file', '-'], run, stdin=marked)
        return 'opened', out.strip()
    where, post = latest_post(number, run)
    seen = KEY_MARK.search(post)
    if where and seen and seen.group(1) == report_key(key if key is not None else body):
        text = counted(post, body, now())
        if where == 'body':
            _gh(['issue', 'edit', str(number), '--body-file', '-'], run, stdin=text)
        else:
            _gh(['api', '--method', 'PATCH', f'repos/{{owner}}/{{repo}}/issues/comments/{where}',
                 '--input', '-'], run, stdin=json.dumps({'body': text}))
        return 'counted', number
    _gh(['issue', 'comment', str(number), '--body-file', '-'], run, stdin=marked)
    return 'commented', number


LOG_LINES = 30


def with_log_tail(body: str, log: str | None) -> str:
    """The body with the last LOG_LINES lines of the log under it, or a line
    saying no log was written -- which is itself the finding when a run died
    before its main step."""
    if log is None:
        return body
    path = Path(log)
    if not path.exists():
        return f'{body}\n\nNo log was written ({path.name}): the run stopped before its main step.'
    tail = path.read_text(encoding='utf-8', errors='replace').splitlines()[-LOG_LINES:]
    return f'{body}\n\nLast {len(tail)} lines of {path.name}:\n```\n' + '\n'.join(tail) + '\n```'


def close_open_issue(title: str, comment: str, run: Run = subprocess.run) -> int | None:
    """Comment on and close the open issue with this title. Returns its number,
    or None when there is no open issue to close (nothing is created).

    For an alert whose cause has an end of its own -- a pull request merged or
    closed -- so the issue does not wait for a person to say it is handled."""
    number = find_open_issue(title, run)
    if number is None:
        return None
    _gh(['issue', 'comment', str(number), '--body-file', '-'], run, stdin=comment)
    _gh(['issue', 'close', str(number)], run)
    return number


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='Open or update an alert issue.')
    ap.add_argument('--title', required=True)
    ap.add_argument('--resolve', action='store_true',
                    help='close the open issue with this title, commenting the body; create nothing')
    ap.add_argument('--body-file', required=True)
    ap.add_argument('--log', help='append the last lines of this log file to the body')
    args = ap.parse_args(argv)
    body = Path(args.body_file).read_text(encoding='utf-8').strip()
    if args.resolve:
        # Stage 83 item 1 (the 2026-11-02 review): a run that succeeds closes the
        # failure issue its own failure would have opened, so an alert ends when
        # its cause does instead of waiting for a person to find it.
        number = close_open_issue(args.title, body or 'Recovered.')
        print(f'closed: {number}' if number is not None else f'no open issue titled {args.title!r}')
        return 0
    if not body:
        # An alert that says nothing is the silent failure this module exists
        # to end, one level up.
        print('refusing to raise an alert with an empty body', file=sys.stderr)
        return 1
    text = with_log_tail(body, args.log)
    try:
        action, ref = open_or_comment(args.title, text, key=body)
    except RuntimeError as exc:
        kept_in_summary(args.title, text, exc)
        return 1
    print(f'{action}: {ref}')
    return 0


def kept_in_summary(title: str, body: str, exc: Exception) -> None:
    """Stage 93 item 12: when GitHub would not take the alert after every try,
    the alert goes where the run's page still shows it -- the step summary --
    with an error annotation naming the title, and the step fails (the
    caller returns 1), so the run is red with the reason on its front page
    instead of green with the alert lost."""
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as f:
            f.write(f'## Alert not raised: {title}\n\nGitHub refused the issue ({exc}). '
                    f'The alert, as it would have been posted:\n\n{body}\n')
    print(f'::error title=Alert not raised::{title}: {exc}')


if __name__ == '__main__':
    raise SystemExit(main())
