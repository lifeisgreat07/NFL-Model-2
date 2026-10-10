"""When each day-sport pick reached the public history (Stage 68 item 20).

The NFL's board shows the commits that saved each week's picks
(src/sports/nfl/lock_proof.py). The NHL and NBA save one file per game,
written once, before its game; this reads, from the repository's own
history, the commit that added each file, when git recorded it, and how
many commits changed the file after, so the card can say "in the public
history at 3:12 PM, before the start" with a link a reader can check on
GitHub, where none of it can be changed after the fact.

A shallow clone has no history to read (the files would all seem to be
added by its one grafted commit), so it gives nothing, and the card shows
no line; so does any git failure. The Pages deploy checks out the whole
history (deploy-pages.yml, fetch-depth: 0).
"""
from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SHA = re.compile(r'[0-9a-f]{40}')
Git = Callable[[list[str], Path], str]


def _git(args: list[str], cwd: Path) -> str:
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, check=True,
                          encoding='utf-8').stdout


def _utc(stamp: str) -> str:
    return datetime.fromisoformat(stamp).astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def proof(folder: Path, root: Path = ROOT, git: Git = _git) -> dict[str, dict[str, Any]]:
    """{game_id: {'sha', 'committed', 'changes'}} for every pick file git has seen added."""
    try:
        if git(['rev-parse', '--is-shallow-repository'], root).strip() != 'false':
            return {}
        rel = folder.resolve().relative_to(root.resolve()).as_posix()
        log = git(['log', '--reverse', '--no-renames', '--format=@%H %cI', '--name-status', '--', rel], root)
    except (OSError, ValueError, subprocess.CalledProcessError):
        return {}
    out: dict[str, dict[str, Any]] = {}
    sha = when = None
    for line in log.splitlines():
        if line.startswith('@'):
            sha, stamp = line[1:].split(' ', 1)
            when = _utc(stamp)
            continue
        parts = line.split('\t')
        if len(parts) != 2 or sha is None or not SHA.fullmatch(sha) or not parts[1].endswith('.json'):
            continue
        status, gid = parts[0], Path(parts[1]).stem
        if status == 'A' and gid not in out:
            out[gid] = {'sha': sha, 'committed': when, 'changes': 0}
        elif gid in out:
            out[gid]['changes'] += 1
    return out
