"""Release notes for each model version (Stage 41 item 3, Mark's yes on
2026-10-04 to the fourth audit's item 24).

The tags v2.2 to v2.5 were pushed on 2026-09-29 (Stage 34 item 27); each
model version also deserves a GitHub Release a visitor can read. The text
comes from config.VERSION_HISTORY -- the same entries What's Changed shows
-- so a release can never say something the page does not. v2.0 and v2.1
have no tag: they predate the repository, as the v2.2 tag message says.

    python -m src.agents.release_notes --list          # versions with a tag to release
    python -m src.agents.release_notes --version 2.5   # one release's notes, markdown

The Releases workflow (.github/workflows/releases.yml) creates a release
for every listed version that does not have one yet, so running it twice
changes nothing. It runs by hand, and since Stage 49 item 25 when a `v*`
tag is pushed; a pushed tag that `--list` does not print fails the run.
"""
import argparse
import subprocess
import sys

from src.pipeline.config import VERSION_HISTORY

#: The first version with a tag in this repository (Stage 34 item 27).
FIRST_TAGGED = (2, 2)
REPO_URL = 'https://github.com/lifeisgreat07/NFL-Model-2'
PAGE_URL = 'https://lifeisgreat07.github.io/NFL-Model-2/'


def _key(version: str) -> tuple[int, ...]:
    return tuple(int(p) for p in version.split('.'))


def released_versions(history=VERSION_HISTORY) -> list[str]:
    """Every VERSION_HISTORY version from the first tagged one on, oldest first."""
    return sorted((h['version'] for h in history if _key(h['version']) >= FIRST_TAGGED), key=_key)


def entry(version: str, history=VERSION_HISTORY) -> dict:
    found = [h for h in history if h['version'] == version]
    if len(found) != 1:
        raise ValueError(f'VERSION_HISTORY has {len(found)} entries for {version!r}, not one')
    return found[0]


def title(version: str, history=VERSION_HISTORY) -> str:
    return f"v{version}: {entry(version, history)['headline']}"


def notes(version: str, history=VERSION_HISTORY) -> str:
    e = entry(version, history)
    return (f"**{e['date']}.** {e['detail']}\n\n"
            f"Every version and its reason is on the dashboard's What's Changed page "
            f"({PAGE_URL}#changelog); every model question asked, and its answer, is on "
            f"Model Lab ({PAGE_URL}#modellab).\n")


def tag_exists(version: str, run=subprocess.run) -> bool:
    r = run(['git', 'rev-parse', '-q', '--verify', f'refs/tags/v{version}'], capture_output=True, text=True)
    return r.returncode == 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    which = ap.add_mutually_exclusive_group(required=True)
    which.add_argument('--list', action='store_true')
    which.add_argument('--version')
    ap.add_argument('--title', action='store_true', help='print the title instead of the notes')
    args = ap.parse_args(argv)
    if args.list:
        missing = [v for v in released_versions() if not tag_exists(v)]
        if missing:
            print(f'no tag for {missing}; tag them first', file=sys.stderr)
            return 1
        print('\n'.join(released_versions()))
        return 0
    print(title(args.version) if args.title else notes(args.version), end='\n' if args.title else '')
    return 0


if __name__ == '__main__':
    sys.exit(main())
