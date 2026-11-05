"""Auto-merge for a pull request that only adds or changes QB override files (Stage 90 item 4).

Mark's decision, recorded in the 2026-11-02 review: the human bottleneck on
override pull requests cost two locked weeks (2026 weeks 7 and 8 locked with
an out-for-season starter while the routine's pull request waited). Once QB
overrides are checked against the roster and a source allowlist (Stage 88
item 4, `override_check.py`), a pull request that does nothing else can merge
itself.

It is OFF until the repository variable `AUTO_MERGE_OVERRIDES` is set to
`true` (Settings, Secrets and variables, Actions, Variables). Mark set it to
build behind that switch on 2026-11-05 and turn it on himself.

`decide` is the whole rule, so a test can hold it:

- every changed file is `data/nfl/qb_overrides/<season>_week<N>.json`, added
  or modified (a deletion, a rename or any other path is not data-only);
- the pull request comes from this repository, not a fork;
- `override_check` passed on those files (its exit code, from the workflow).

Anything else leaves the pull request for a person, and says why.

    python -m src.sports.nfl.override_automerge --files files.ndjson --check-exit 0 --same-repo true
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

OVERRIDE = re.compile(r'^data/nfl/qb_overrides/\d{4}_week\d+\.json$')
DATA_ONLY_STATUSES = ('added', 'modified')


def decide(files: list[dict[str, Any]], check_exit: int, same_repo: bool) -> tuple[bool, list[str]]:
    """(merge?, why not) for a pull request's changed files, as the API lists them."""
    why = []
    if not same_repo:
        why.append('the pull request comes from a fork')
    if not files:
        why.append('the pull request changes no file')
    for f in files:
        name, status = f.get('filename', ''), f.get('status', '')
        if not OVERRIDE.match(name):
            why.append(f'{name} is not a QB override file')
        elif status not in DATA_ONLY_STATUSES:
            why.append(f'{name} is {status}, not added or modified')
    if check_exit != 0:
        why.append('the override check did not pass')
    return not why, why


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--files', required=True, type=Path, help='the changed files, one JSON object a line')
    ap.add_argument('--check-exit', required=True, type=int)
    ap.add_argument('--same-repo', required=True, choices=('true', 'false'))
    args = ap.parse_args(argv)
    files = [json.loads(line) for line in args.files.read_text(encoding='utf-8').splitlines() if line.strip()]
    merge, why = decide(files, args.check_exit, args.same_repo == 'true')
    if merge:
        print('MERGE: only QB override files, and each passed the roster and source check.')
        return 0
    print('LEAVE FOR A PERSON: ' + '; '.join(why))
    return 1


if __name__ == '__main__':
    sys.exit(main())
