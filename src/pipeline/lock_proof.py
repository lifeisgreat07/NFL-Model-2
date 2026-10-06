"""When each week's picks were saved, and every commit that changed them
(Stage 46 item 5).

The page says picks are saved before kickoff. This lets a reader check that
without trusting the page. For each locked week (predictions/<season>_week<N>.json)
the page gets every commit that ever changed the file, oldest first, with
the time git recorded and a link to the commit on GitHub, where none of it
can be changed after the fact. The page then says which commit last changed
the picks before the week's first kickoff, and names any commit after it.
Week 1's dates were backfilled after kickoff, under a stated exception: a
commit like that is shown, not hidden.

Read from the repository's own history with `git log --follow`, so a later
move of the file (Stage 52 moves the NFL's folders) still reaches back past
the move. The deploy checks out the whole history for this. The site build
runs it before the board and writes data/lock_proof.json (gitignored).

    python -m src.pipeline.lock_proof --out data/lock_proof.json

A week git cannot place (a shallow clone, a file not yet committed) is left
out, and the page shows no line for it. Any other failure prints why, writes
nothing and exits 0: the board is not held back by its proof line.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.pipeline.paths import PRED_DIR

ROOT = Path(__file__).resolve().parents[2]
#: Where the links point.
REPO = 'lifeisgreat07/NFL-Model-2'
WEEK_FILE = re.compile(r'(\d{4})_week(\d+)')
Git = Any


def locked_weeks(pred_dir: Path = PRED_DIR) -> list[tuple[str, Path]]:
    """('<season>_week<N>', file) for every locked week, oldest first.
    Previews live in predictions/preview/ and are not locked."""
    keys = []
    for p in pred_dir.glob('*_week*.json'):
        m = WEEK_FILE.fullmatch(p.stem)
        if m:
            keys.append((int(m.group(1)), int(m.group(2)), p.stem, p))
    return [(k, p) for _, _, k, p in sorted(keys)]


def _git(args: list[str], cwd: Path) -> str:
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, check=True,
                          encoding='utf-8').stdout


def history(path: Path, root: Path = ROOT, repo: str = REPO, git: Git = _git) -> list[dict[str, str]]:
    """Every commit that changed `path`, following renames, oldest first."""
    rel = path.resolve().relative_to(root.resolve()).as_posix()
    out = git(['log', '--follow', '--format=%H%x09%cI%x09%s', '--', rel], root)
    commits = []
    for line in out.splitlines():
        if not line.strip():
            continue
        sha, when, subject = (line.split('\t', 2) + [''])[:3]
        stamp = datetime.fromisoformat(when).astimezone(UTC)
        commits.append({'sha': sha, 'short': sha[:7], 'committed_utc': stamp.strftime('%Y-%m-%dT%H:%M:%SZ'),
                        'subject': subject, 'url': f'https://github.com/{repo}/commit/{sha}'})
    return commits[::-1]


class ShallowClone(RuntimeError):
    """A shallow clone's oldest commit looks as if it added every file, so
    its history would name the wrong commit as the save."""


def proof(pred_dir: Path = PRED_DIR, root: Path = ROOT, repo: str = REPO,
          git: Git = _git) -> dict[str, list[dict[str, str]]]:
    if git(['rev-parse', '--is-shallow-repository'], root).strip() == 'true':
        raise ShallowClone('the checkout is shallow; fetch the whole history (fetch-depth: 0)')
    out = {}
    for key, path in locked_weeks(pred_dir):
        commits = history(path, root, repo, git)
        if commits:
            out[key] = commits
    return out


def main(argv: list[str] | None = None, now: datetime | None = None, git: Git = _git) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='data/lock_proof.json')
    args = ap.parse_args(argv)
    try:
        weeks = proof(git=git)
    except Exception as exc:  # any failure: the board is built without the line
        print(f'lock commits not read ({type(exc).__name__}: {exc}); the page will show no lock line')
        return 0
    now = now or datetime.now(UTC)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'read_utc': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'weeks': weeks},
                              indent=2) + '\n', encoding='utf-8')
    print(f'{len(weeks)} weeks of lock commits written to {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
