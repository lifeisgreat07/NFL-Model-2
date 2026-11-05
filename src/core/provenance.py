"""What a day sport's pick was trained on, saved with the pick (Stage 68 item 27).

The NFL's picks carry `data_provenance` (src/sports/nfl/weekly_update.py);
the NHL's and NBA's said nothing about the data behind their models, so a
pick could not show which games it had learned from (the 2026-10-09
audit, E26). The models are refitted each run on every completed game
from the registered first season, so the record is the first season, the
games, how many of them had a price, and the last day among them.

Stage 95 items 39 and 40 (audit 7, M5, M8, M9) make the record exact:
`training_ids_sha256` is a digest of the sorted game ids the models were fitted
on, so two picks trained on the same games can be shown to be, and
`code_identity` names the code that made the pick: `code_sha256`, a digest of
every Python file under src/core and the sport's own folder, beside the
hand-set `code` (CODE_VERSION), and `code_commit`, the commit the run checked
out. CODE_VERSION alone said `nhl-stage56` for every pick since Stage 56.
"""
from __future__ import annotations

import functools
import hashlib
import os
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def ids_digest(ids: Iterable[object]) -> str | None:
    """SHA-256 of the sorted ids, one per line; None for none."""
    keys = sorted(str(i) for i in ids)
    return hashlib.sha256('\n'.join(keys).encode('utf-8')).hexdigest() if keys else None


@functools.cache
def code_identity(sport: str, root: Path = ROOT) -> dict[str, str | None]:
    """`code_sha256` and `code_commit` for a sport's picks, worked out once per run.

    The digest covers every .py file under src/core and src/sports/<sport>, each as its
    repository path and its text with line endings made LF, in path order, so it is the
    same on Windows and on the runner. The commit is GITHUB_SHA on a runner, else git's
    HEAD, else None."""
    h = hashlib.sha256()
    for folder in (root / 'src' / 'core', root / 'src' / 'sports' / sport):
        for path in sorted(folder.rglob('*.py'), key=lambda p: p.relative_to(root).as_posix()):
            h.update(path.relative_to(root).as_posix().encode('utf-8') + b'\0')
            h.update(path.read_text(encoding='utf-8').replace('\r\n', '\n').encode('utf-8') + b'\0')
    commit = os.environ.get('GITHUB_SHA') or None
    if commit is None:
        try:
            out = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True, timeout=10)
            commit = out.stdout.strip() or None if out.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            commit = None
    return {'code_sha256': h.hexdigest(), 'code_commit': commit}


def training(table: pd.DataFrame, first_season: int) -> dict[str, Any]:
    """`training_through` and `data_provenance` for a pick, from the table its models were fitted on."""
    days = pd.to_datetime(table['day'])
    priced = int(table['home_prob'].notna().sum()) if 'home_prob' in table else 0
    return {
        'training_through': str(days.max().date()) if len(days) else None,
        'data_provenance': {
            'training_from_season': int(first_season),
            'training_games': int(len(table)),
            'training_games_priced': priced,
            'training_ids_sha256': ids_digest(table['game_id']) if 'game_id' in table else None,
        },
    }
