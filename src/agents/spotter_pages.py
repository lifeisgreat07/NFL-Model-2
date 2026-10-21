"""Which pages of the built site a change can alter (Stage 43 item 2).

Spotter renders the pages a pull request touches, not every page every time:
a change to the NHL's stylesheet does not need the NBA's page photographed.
The built site (src/site/build.py) has four pages, `home`, `nfl`, `nhl` and
`nba`, and each is built from its own files. `RULES` says which files feed
which pages, first match wins.

The map is held to the repository by tests/test_spotter_pages.py, so it
cannot drift quietly:

* every file in the repository that `scout_preflight.page_files` calls part
  of a page has a rule here (a new template part with no rule fails the
  suite, not a Spotter run nobody reads);
* every rule matches a file that exists, so a renamed folder cannot leave a
  rule pointing at nothing.

A changed page file with no rule is still rendered: it falls back to every
page, and the result says so (`unmapped`), because rendering too much is a
cost and rendering too little is a miss.

    python -m src.agents.spotter_pages --base <sha> --head <sha>

prints the pages as one line, `nfl,nhl`, which is empty when the change
touches no page.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from src.agents.scout_preflight import page_files

ROOT = Path(__file__).resolve().parents[2]

#: The built site's pages, in the order they are rendered, and where each is
#: served under the site's root.
PAGES = ('home', 'nfl', 'nhl', 'nba')
SITE_PATH = {'home': '', 'nfl': 'nfl/', 'nhl': 'nhl/', 'nba': 'nba/'}

#: (repository path or folder prefix, the pages it feeds). First match wins.
#: An empty tuple says the file is a page file that no page is built from.
RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ('src/dashboard/', ('nfl',)),
    ('src/sports/nhl/pages/', ('nhl',)),
    ('src/sports/nhl/site.py', ('nhl',)),
    ('src/sports/nhl/page_inputs.py', ('nhl',)),
    ('src/sports/nba/pages/', ('nba',)),
    ('src/sports/nba/site.py', ('nba',)),
    ('src/sports/nba/page_inputs.py', ('nba',)),
    ('src/site/home/', ('home',)),
    ('src/site/home.py', ('home',)),
    ('assets/favicon-nhl.svg', ('nhl',)),
    ('assets/favicon-nba.svg', ('nba',)),
    ('assets/favicon.svg', ('home', 'nfl')),
    # The link-preview card sources are drawn to og-*.png by hand; no page
    # renders them.
    ('assets/og/', ()),
    # What every page is published with, and what takes the pictures: a
    # change to the renderer or its workflow can change every picture, so it
    # renders every page (and is how the renderer's own pull request is
    # shown to work).
    ('src/agents/spotter_pages.py', PAGES),
    ('tests/browser/spotter_render.py', PAGES),
    ('.github/workflows/spotter.yml', PAGES),
    ('src/site/build.py', PAGES),
    ('src/site/sw.js', PAGES),
    ('src/site/search.py', PAGES),
)


@dataclass(frozen=True)
class Plan:
    pages: tuple[str, ...]
    unmapped: tuple[str, ...]


def rule_for(path: str) -> tuple[str, tuple[str, ...]] | None:
    for prefix, pages in RULES:
        if path == prefix or (prefix.endswith('/') and path.startswith(prefix)):
            return prefix, pages
    return None


def plan(changed: list[str]) -> Plan:
    """The pages to render for these changed files, and the page files no
    rule knew (which pull in every page)."""
    flagged = set(page_files(changed))
    pages: set[str] = set()
    unmapped: list[str] = []
    for path in changed:
        hit = rule_for(path)
        if hit is not None:
            pages.update(hit[1])
        elif path in flagged:
            unmapped.append(path)
    if unmapped:
        pages.update(PAGES)
    return Plan(tuple(p for p in PAGES if p in pages), tuple(sorted(unmapped)))


def changed_files(base: str, head: str, cwd: Path = ROOT) -> list[str]:
    out = subprocess.run(['git', 'diff', '--name-only', f'{base}...{head}'], cwd=cwd,
                         capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else '')
    ap.add_argument('--base', required=True)
    ap.add_argument('--head', required=True)
    args = ap.parse_args(argv)
    result = plan(changed_files(args.base, args.head))
    print(','.join(result.pages))
    if result.unmapped:
        print(f'unmapped page files, every page rendered: {", ".join(result.unmapped)}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
