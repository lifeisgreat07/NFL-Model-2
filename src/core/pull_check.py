"""
Refuse to commit after a pull that did not apply cleanly.

Stage 91 item 1 (audit 7, 2026-11-04, finding R1). Every writer catches up
with main before committing with `git pull --rebase --autostash`, which
carries the run's uncommitted data across the rebase. When main has changed a
file the run also wrote, the stash does not apply cleanly, and git says so but
EXITS 0: it leaves the stash in place and the file full of conflict markers,
and the commit step then stages and pushes that file to main. The run is
green, no alert fires, and the next run and the Pages build read invalid
JSON. (Reproduced with git 2.55 on 2026-11-05.)

Run straight after the pull, in the same step:

    python -m src.core.pull_check

It exits 1, naming what it found, when a stash is left, when a path is
unmerged, or when a changed file holds a conflict marker. A failed step
fails the job, so the run's failure alert fires and the keep-the-picks
artifact step (if: failure()) keeps what the run made; nothing is pushed.
Standard library only.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

#: The opening or closing line git writes around a hunk it could not merge. (The
#: middle "=======" line is left out: a Markdown heading underline can be one.)
MARKER = re.compile(r'^(<{7}|>{7})( |$)', re.M)


def _git(root: Path, *args: str) -> str:
    r = subprocess.run(('git', *args), cwd=root, capture_output=True, text=True, check=True)
    return r.stdout


def problems(root: Path = Path('.')) -> list[str]:
    """What is wrong with the working tree at `root` after the pull; empty when it is clean to commit."""
    out = []
    stash = _git(root, 'stash', 'list').strip()
    if stash:
        out.append(f'a stash is left ({stash.splitlines()[0]}): the autostash did not apply cleanly')
    unmerged = [p for p in _git(root, 'diff', '--name-only', '--diff-filter=U').split('\n') if p]
    if unmerged:
        out.append('unmerged: ' + ', '.join(unmerged))
    changed = [p for p in _git(root, 'diff', '--name-only', 'HEAD').split('\n') if p]
    marked = [p for p in changed if (root / p).is_file()
              and MARKER.search((root / p).read_text(encoding='utf-8', errors='replace'))]
    if marked:
        out.append('conflict markers in: ' + ', '.join(marked))
    return out


def main(root: Path = Path('.')) -> int:
    found = problems(root)
    if not found:
        print('pull_check: the tree is clean to commit')
        return 0
    print('PULL REFUSED: main changed a file this run also wrote, and the pull did not apply cleanly. '
          "Nothing is committed; this run's files are kept in its artifact.")
    for p in found:
        print('  ' + p)
    return 1


if __name__ == '__main__':
    sys.exit(main())
