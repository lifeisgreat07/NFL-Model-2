"""Build the whole published site, one sport at a time (Stage 53).

The site the deploy publishes:

    index.html            the home page (Stage 59, src/site/home.py): a card
                          per sport; a #picks= share link is sent on to nfl/
    nfl/index.html        the NFL's board, and nfl/dist/ its printable picks
    nhl/index.html        the NHL's pages
    nba/index.html        the NBA's pages
    og-card.png, assets/  shared by every page; .nojekyll

**Each sport builds on its own.** A builder runs in a process of its own, so
an exception, a `sys.exit` or a crash in one sport's code cannot stop another
sport from publishing. A sport whose build fails keeps its last good page: the
page currently live at `<live-url>/<sport>/` is fetched and published again
unchanged. Either way the failure is written to the report, and the deploy
opens an issue titled for that sport ("NHL: page build failed").

The run fails, and nothing is published, only when the NFL has no page at
all: neither a fresh build nor a live copy. Any other sport with no page is
left out and reported.

Run by hand:  python -m src.site.build --out _site
The deploy:   python -m src.site.build --out _site --live-url https://lifeisgreat07.github.io/NFL-Model-2
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: Every sport the site publishes, in the order they are built.
SPORTS = ('nfl', 'nhl', 'nba')

#: The sport the root sends a visitor to until the home page exists.
DEFAULT_SPORT = 'nfl'

#: The files every page shares: published path -> repository path.
SHARED_FILES = {
    '.nojekyll': '.nojekyll',
    'og-card.png': 'assets/og/og-card.png',
    'assets/favicon.svg': 'assets/favicon.svg',
    'assets/apple-touch-icon.png': 'assets/apple-touch-icon.png',
}

#: What the root redirect and the home page say about themselves, so a live
#: copy of the root is never mistaken for the NFL's board.
REDIRECT_MARK = 'data-site-redirect'
HOME_MARK = 'data-site-home'

Runner = Callable[[list[str]], int]
Fetcher = Callable[[str], 'bytes | None']


@dataclass
class SportResult:
    sport: str
    built: bool = False
    kept_live: bool = False
    error: str = ''
    log: list[str] = field(default_factory=list)

    @property
    def published(self) -> bool:
        return self.built or self.kept_live


def run(cmd: list[str]) -> int:
    """Run one build command from the repository root. Its output goes to
    this process's own, so the deploy log shows every sport's build."""
    return subprocess.run(cmd, cwd=ROOT).returncode


def fetch(url: str) -> bytes | None:
    """The live copy of a page, or None if there is none to keep."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'site-build'})
        with urllib.request.urlopen(req, timeout=30) as r:
            body: bytes = r.read()
            return body if r.status == 200 and body else None
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def unfilled(html: str) -> list[str]:
    """Template placeholders still in a page (`__NAME__`)."""
    return sorted(set(re.findall(r'__[A-Z0-9_]+__', html)))


def build_commands(sport: str, out: Path) -> list[list[str]]:
    """The commands that build one sport's page into `out/<sport>/`."""
    py = [sys.executable, '-B', '-m']
    if sport == 'nfl':
        # The NFL's builder writes index.html and dist/ at the repository
        # root, where a local checkout looks at them, and check_build refuses
        # a page with missing data; collect() copies both into place.
        return [py + ['src.pipeline.generate_dashboard'],
                py + ['src.pipeline.check_build', 'index.html'],
                # Every locked pick and its grade, beside the board (Stage 46 item 7).
                py + ['src.pipeline.picks_csv', '--out', 'picks.csv']]
    return [py + [f'src.sports.{sport}.site', '--out', str(out / sport / 'index.html')]]


def collect(sport: str, out: Path) -> None:
    """Copy what a successful NFL build left at the root into nfl/."""
    if sport != 'nfl':
        return
    dest = out / 'nfl'
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / 'index.html', dest / 'index.html')
    if (ROOT / 'picks.csv').exists():
        shutil.copyfile(ROOT / 'picks.csv', dest / 'picks.csv')
    if (ROOT / 'dist').is_dir():
        shutil.copytree(ROOT / 'dist', dest / 'dist', dirs_exist_ok=True)


def live_copy(sport: str, live_url: str, fetcher: Fetcher) -> bytes | None:
    """The sport's page as published now. The NFL's lived at the root until
    this stage, so its first deploy here falls back to the root's page, as
    long as that page is not the redirect."""
    base = live_url.rstrip('/')
    body = fetcher(f'{base}/{sport}/')
    if body is None and sport == 'nfl':
        root = fetcher(f'{base}/')
        if root is not None and REDIRECT_MARK.encode() not in root and HOME_MARK.encode() not in root:
            body = root
    return body


def build_sport(sport: str, out: Path, live_url: str | None,
                runner: Runner = run, fetcher: Fetcher = fetch) -> SportResult:
    res = SportResult(sport)
    page = out / sport / 'index.html'
    page.parent.mkdir(parents=True, exist_ok=True)
    try:
        for cmd in build_commands(sport, out):
            code = runner(cmd)
            step = ' '.join(cmd[3:])
            res.log.append(f'{step}: exit {code}')
            if code != 0:
                raise RuntimeError(f'{step} exited {code}')
        collect(sport, out)
        html = page.read_text(encoding='utf-8') if page.exists() else ''
        if not html.strip():
            raise RuntimeError(f'{sport}/index.html is missing or empty')
        left = unfilled(html)
        if left:
            raise RuntimeError(f'{sport}/index.html has unfilled placeholders: {left}')
        res.built = True
        return res
    except Exception as exc:  # any failure of this sport's build, and only this sport's
        res.error = str(exc)
    shutil.rmtree(out / sport, ignore_errors=True)
    if live_url:
        body = live_copy(sport, live_url, fetcher)
        if body is not None:
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_bytes(body)
            res.kept_live = True
    return res


REDIRECT = """<!DOCTYPE html>
<html lang="en" data-site-redirect="{sport}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex">
<title>Pick'em Model</title>
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<script>
  // The board moved to {sport}/ (Stage 53). A shared-picks link carries its
  // picks in the hash (#picks=...), so the query and the hash go along.
  location.replace('{sport}/' + location.search + location.hash);
</script>
<meta http-equiv="refresh" content="0; url={sport}/">
</head>
<body>
<p>The board has moved: <a href="{sport}/">open the {label} board</a>.</p>
</body>
</html>
"""


def redirect_page(sport: str = DEFAULT_SPORT) -> str:
    return REDIRECT.replace('{sport}', sport).replace('{label}', sport.upper())


def assemble_shared(out: Path) -> None:
    for dest, src in SHARED_FILES.items():
        target = out / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / src, target)


def build_home(out: Path, runner: Runner = run, unpublished: tuple[str, ...] = ()) -> SportResult:
    """The home page, in a process of its own like every sport's. If it
    fails, the root forwards to the NFL board instead, as it did before the
    home page existed, and the failure is reported like a sport's."""
    res = SportResult('home')
    page = out / 'index.html'
    cmd = [sys.executable, '-B', '-m', 'src.site.home', '--out', str(page), '--unpublished', ','.join(unpublished)]
    try:
        code = runner(cmd)
        res.log.append(f'src.site.home: exit {code}')
        if code != 0:
            raise RuntimeError(f'src.site.home exited {code}')
        html = page.read_text(encoding='utf-8') if page.exists() else ''
        if not html.strip() or unfilled(html):
            raise RuntimeError(f'index.html is empty or unfilled: {unfilled(html)}')
        res.built = True
    except Exception as exc:  # the home page's failure, and only the home page's
        res.error = str(exc)
        page.write_text(redirect_page(), encoding='utf-8')
        res.kept_live = True
    return res


def build_site(out: Path, live_url: str | None, sports: tuple[str, ...] = SPORTS,
               runner: Runner = run, fetcher: Fetcher = fetch) -> list[SportResult]:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    results = [build_sport(s, out, live_url, runner, fetcher) for s in sports]
    assemble_shared(out)
    results.append(build_home(out, runner, tuple(r.sport for r in results if not r.published)))
    return results


def report(results: list[SportResult]) -> dict[str, object]:
    return {'sports': [{'sport': r.sport, 'built': r.built, 'kept_live': r.kept_live,
                        'published': r.published, 'error': r.error, 'log': r.log}
                       for r in results]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='Build the whole site, one sport at a time')
    ap.add_argument('--out', default='_site')
    ap.add_argument('--live-url', default=None,
                    help='where the site is published now; a sport whose build fails keeps its page from there')
    ap.add_argument('--report', default='site-report.json',
                    help='written outside --out, so it is never published')
    args = ap.parse_args(argv)
    results = build_site(Path(args.out), args.live_url)
    Path(args.report).write_text(json.dumps(report(results), indent=1) + '\n', encoding='utf-8')
    for r in results:
        state = 'built' if r.built else 'kept the live page' if r.kept_live else 'NOT PUBLISHED'
        print(f'{r.sport}: {state}' + (f' ({r.error})' if r.error else ''))
    first = next((r for r in results if r.sport == DEFAULT_SPORT), None)
    if first is not None and not first.published:
        print(f'{DEFAULT_SPORT} has no page at all; refusing to publish a site whose root leads nowhere')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
