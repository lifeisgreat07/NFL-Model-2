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
for a week should produce one issue with seven comments, not seven issues --
the second is how alert fatigue starts. Matching is on the exact title among
OPEN issues, so closing an issue is how you say "handled": the next failure
opens a fresh one.

Uses the `gh` CLI, which GitHub's runners carry, authenticated by GH_TOKEN.
The workflow step supplies that token and the `issues: write` permission; no
job that runs a model is given either.

    python -m src.core.alerts --title "NHL: nightly canary failing" --body-file report.md
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

Run = Callable[..., Any]


def _gh(args: list[str], run: Run, stdin: str | None = None) -> str:
    r = run(['gh'] + args, input=stdin, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"gh {' '.join(args[:2])} failed: {(r.stderr or r.stdout).strip()}")
    out: str = r.stdout
    return out


def find_open_issue(title: str, run: Run = subprocess.run) -> int | None:
    """The number of the open issue with exactly this title, or None."""
    out = _gh(['issue', 'list', '--state', 'open', '--limit', '200',
               '--json', 'number,title'], run)
    for issue in json.loads(out or '[]'):
        if issue.get('title') == title:
            return int(issue['number'])
    return None


def open_or_comment(title: str, body: str, run: Run = subprocess.run) -> tuple[str, int | str]:
    """Comment on the open issue with this title, or open one. Returns
    ('commented' | 'opened', issue reference)."""
    number = find_open_issue(title, run)
    if number is not None:
        _gh(['issue', 'comment', str(number), '--body-file', '-'], run, stdin=body)
        return 'commented', number
    out = _gh(['issue', 'create', '--title', title, '--body-file', '-'], run, stdin=body)
    return 'opened', out.strip()


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='Open or update an alert issue.')
    ap.add_argument('--title', required=True)
    ap.add_argument('--body-file', required=True)
    args = ap.parse_args(argv)
    body = Path(args.body_file).read_text(encoding='utf-8').strip()
    if not body:
        # An alert that says nothing is the silent failure this module exists
        # to end, one level up.
        print('refusing to raise an alert with an empty body', file=sys.stderr)
        return 1
    action, ref = open_or_comment(args.title, body)
    print(f'{action}: {ref}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
