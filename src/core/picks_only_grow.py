"""A day sport's saved picks only ever gain files (Stage 93 item 21, audit 7 R16).

A pick is written once, before its game, and never again: that is what the
forward test and the proof-of-lock links rest on. `save_once` refuses to
overwrite one, but nothing checked what a run actually commits, so a bug
elsewhere -- a rename, a cleanup, a rewrite through another path -- would have
reached main with the run green.

The daily runs call this after staging and before committing. It reads the
staged changes under the given folders and fails, naming each, on anything
but an added file.

    python -m src.core.picks_only_grow predictions/nhl
"""
from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable, Sequence
from typing import Any

Run = Callable[..., Any]


def staged(paths: Sequence[str], run: Run = subprocess.run) -> list[tuple[str, str]]:
    """(status, path) for every staged change under `paths`: A added, M modified, D deleted, R renamed..."""
    r = run(['git', 'diff', '--cached', '--name-status', '--no-renames', '--', *paths],
            capture_output=True, text=True, check=True)
    out = []
    for line in r.stdout.splitlines():
        status, _, path = line.partition('\t')
        if path:
            out.append((status, path))
    return out


def main(argv: Sequence[str] | None = None, run: Run = subprocess.run) -> int:
    paths = list(sys.argv[1:] if argv is None else argv)
    if not paths:
        print('usage: python -m src.core.picks_only_grow FOLDER...', file=sys.stderr)
        return 2
    changes = staged(paths, run)
    bad = [(s, p) for s, p in changes if s != 'A']
    if bad:
        print('PICKS CHANGED: a saved pick is never rewritten or removed, and this commit would:')
        for s, p in bad:
            print(f'  {s} {p}')
        return 1
    print(f'picks only grow: {len(changes)} added under {", ".join(paths)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
