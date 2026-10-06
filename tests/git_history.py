"""When a file first entered the repository, and under what name.

The pre-registration tests (Stages 5, 6 and 33) ask git for the commit that
first added a result file, then read the registry in that commit's parent. A
plain `git log --diff-filter=A -- <path>` answers with the last commit that
added the file *at that path*. Stage 52 moves every NFL experiment under
experiments/nfl/ with `git mv`, so after it the plain query names the move
commit, whose parent has no registry at the new path, and the checks fail; a
weaker check comparing a file with its own moved copy would instead pass by
default. Following renames gives the commit that first added the file and the
path it had then.
"""
from __future__ import annotations

import subprocess
from pathlib import Path, PurePosixPath


def first_added(repo: Path, rel: str) -> tuple[str, str] | None:
    """(commit, path at that commit) for the commit that first added `rel`,
    following renames; None if `rel` has never been committed."""
    out = subprocess.run(
        ['git', '-C', str(repo), 'log', '--follow', '--diff-filter=A', '--name-only', '--format=%x1e%H', '--', rel],
        capture_output=True, text=True, check=True).stdout
    entries = [e.split() for e in out.split('\x1e') if e.strip()]
    if not entries:
        return None
    sha, *paths = entries[-1]
    return sha, (paths[-1] if paths else rel)


def registry_beside(result_path: str) -> str:
    """The registry that sat beside a result when it was written:
    <stage>/results/<id>.json -> <stage>/registry.json."""
    return str(PurePosixPath(result_path).parent.parent / 'registry.json')
