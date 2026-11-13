"""Stored history files only ever gain rows (audit 8, finding S5).

A collector appends each new game to a season's file and never rewrites a stored row, so a commit of its folder may
add files and add lines, and nothing else. The collector workflow calls this after staging and before committing:
it reads the staged changes under the given folders and fails, naming each file, on a deleted or renamed file or on
any removed line.

    python -m src.core.rows_only_grow data/ncaam/history
"""
from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable, Sequence
from typing import Any

Run = Callable[..., Any]


def changes(paths: Sequence[str], run: Run = subprocess.run) -> list[tuple[str, str, str]]:
    """(status, lines removed, path) for every staged change under `paths`."""
    status = run(['git', 'diff', '--cached', '--name-status', '--no-renames', '--', *paths],
                 capture_output=True, text=True, check=True).stdout
    numstat = run(['git', 'diff', '--cached', '--numstat', '--no-renames', '--', *paths],
                  capture_output=True, text=True, check=True).stdout
    removed = {}
    for line in numstat.splitlines():
        parts = line.split('\t')
        if len(parts) == 3:
            removed[parts[2]] = parts[1]
    out = []
    for line in status.splitlines():
        s, _, path = line.partition('\t')
        if path:
            out.append((s, removed.get(path, '0'), path))
    return out


def main(argv: Sequence[str] | None = None, run: Run = subprocess.run) -> int:
    paths = list(sys.argv[1:] if argv is None else argv)
    if not paths:
        print('usage: python -m src.core.rows_only_grow FOLDER...', file=sys.stderr)
        return 2
    found = changes(paths, run)
    bad = [(s, r, p) for s, r, p in found if s not in ('A', 'M') or r != '0']
    if bad:
        print('ROWS CHANGED: a stored row is never rewritten or removed, and this commit would:')
        for s, r, p in bad:
            print(f'  {s} {p} ({r} lines removed)')
        return 1
    print(f'rows only grow: {len(found)} files added or appended under {", ".join(paths)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
