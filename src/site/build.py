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
    # Stage 76 item 11 (the 2026-10-13 audit's C1, V6): each sport its own
    # icon, home-screen icon and link preview, and the home page a preview
    # with the three marks. The NFL keeps the files above.
    'og-nhl.png': 'assets/og/og-nhl.png',
    'og-nba.png': 'assets/og/og-nba.png',
    'og-home.png': 'assets/og/og-home.png',
    'assets/favicon-nhl.svg': 'assets/favicon-nhl.svg',
    'assets/favicon-nba.svg': 'assets/favicon-nba.svg',
    'assets/apple-touch-icon-nhl.png': 'assets/apple-touch-icon-nhl.png',
    'assets/apple-touch-icon-nba.png': 'assets/apple-touch-icon-nba.png',
    'assets/site.webmanifest': 'assets/site.webmanifest',
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
        # Every commit that changed each locked week's picks, for the
        # board's lock line (Stage 46 item 5); it never fails the build.
        return [py + ['src.sports.nfl.lock_proof', '--out', 'data/nfl/lock_proof.json'],
                py + ['src.sports.nfl.generate_dashboard'],
                py + ['src.sports.nfl.check_build', 'index.html'],
                # Every locked pick and its grade, beside the board (Stage 46 item 7).
                py + ['src.sports.nfl.picks_csv', '--out', 'picks.csv']]
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
<title>Sportalytics</title>
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


#: The "Next games" strip's script (Stage 80 item 52), and how the build
#: marks what it puts on a page, so a page kept from the live site has its
#: old strip taken out before today's goes in.
STRIP_JS = ROOT / 'src' / 'core' / 'strip.js'
STRIP_MARK = 'data-site-strip'
_STRIP_OLD = re.compile(r'<script[^>]*\bdata-site-strip\b[^>]*>.*?</script>\n?', re.S)


def strip_block(rows: list[dict[str, object]]) -> str:
    """The slate as data and the script that draws it, comments taken out
    as every page's are."""
    from src.core.page_comments import strip_page_comments
    from src.core.page_fill import safe_json
    script = strip_page_comments('<script>\n' + STRIP_JS.read_text(encoding='utf-8') + '</script>')
    return (f'<script type="application/json" id="site-strip-data" {STRIP_MARK}>{safe_json(rows)}</script>\n'
            + script.replace('<script>', f'<script {STRIP_MARK}>', 1) + '\n')


def inject_strip(page: Path, block: str) -> bool:
    """Put the strip on one built page: only a page that has the empty
    #site-strip its template carries, before its </body>."""
    if not page.exists():
        return False
    html = _STRIP_OLD.sub('', page.read_text(encoding='utf-8'))
    if 'id="site-strip"' not in html or '</body>' not in html:
        return False
    at = html.rindex('</body>')
    page.write_text(html[:at] + block + html[at:], encoding='utf-8')
    return True


def add_strip(out: Path, results: list[SportResult],
              slate: Callable[[], list[dict[str, object]]] | None = None) -> list[str]:
    """The strip on the home and every sport's page, each published sport's
    games only, so no card links to a page this build has not got. The
    strip is an extra: a failure here is printed and publishes the pages
    without it."""
    from src.site import home
    published = {r.sport for r in results if r.published and r.sport in SPORTS}
    try:
        block = strip_block([g for g in (slate or home.slate)() if g['s'] in published])
    except Exception as exc:  # the strip's failure leaves every page as built
        print(f'the Next games strip was left off: {exc}')
        return []
    pages = ['index.html'] + [f'{s}/index.html' for s in SPORTS]
    return [p for p in pages if inject_strip(out / p, block)]


#: The search box's script and how the build marks what it puts on a page
#: (Stage 80 item 56), as the strip's.
PALETTE_JS = ROOT / 'src' / 'core' / 'palette.js'
SEARCH_MARK = 'data-site-search'
_SEARCH_OLD = re.compile(r'<script[^>]*\bdata-site-search\b[^>]*>.*?</script>\n?', re.S)


def search_block(found: dict[str, object]) -> str:
    """The search index as data and the script that searches it."""
    from src.core.page_comments import strip_page_comments
    from src.core.page_fill import safe_json
    script = strip_page_comments('<script>\n' + PALETTE_JS.read_text(encoding='utf-8') + '</script>')
    return (f'<script type="application/json" id="site-search-data" {SEARCH_MARK}>{safe_json(found)}</script>\n'
            + script.replace('<script>', f'<script {SEARCH_MARK}>', 1) + '\n')


def inject_search(page: Path, block: str) -> bool:
    """Put the search box on one built page: only a page whose template has
    a Search button for it, before its </body>, after the strip's slate."""
    if not page.exists():
        return False
    html = _SEARCH_OLD.sub('', page.read_text(encoding='utf-8'))
    if 'data-palette-open' not in html or '</body>' not in html:
        return False
    at = html.rindex('</body>')
    page.write_text(html[:at] + block + html[at:], encoding='utf-8')
    return True


def add_search(out: Path, results: list[SportResult],
               finder: Callable[[Path, set[str]], dict[str, object]] | None = None) -> list[str]:
    """The search box on the home and every sport's page, finding the
    published sports' teams, pages and experiments (src/site/search.py) and
    the slate's games. Like the strip, an extra: a failure is printed and
    publishes the pages without it."""
    from src.site import search
    published = {r.sport for r in results if r.published and r.sport in SPORTS}
    try:
        block = search_block((finder or search.index)(out, published))
    except Exception as exc:  # the search box's failure leaves every page as built
        print(f'the search box was left off: {exc}')
        return []
    pages = ['index.html'] + [f'{s}/index.html' for s in SPORTS]
    return [p for p in pages if inject_search(out / p, block)]


#: The Settings sheet and the keyboard shortcuts (Stage 80 item 57), put on
#: a page as the search box is.
SHEET_JS = ROOT / 'src' / 'core' / 'sheet.js'
SHEET_MARK = 'data-site-sheet'
_SHEET_OLD = re.compile(r'<script[^>]*\bdata-site-sheet\b[^>]*>.*?</script>\n?', re.S)


def sheet_block() -> str:
    from src.core.page_comments import strip_page_comments
    script = strip_page_comments('<script>\n' + SHEET_JS.read_text(encoding='utf-8') + '</script>')
    return script.replace('<script>', f'<script {SHEET_MARK}>', 1) + '\n'


def inject_sheet(page: Path, block: str) -> bool:
    """Put the sheet on one built page: only a page whose template has a
    Settings button for it, before its </body>."""
    if not page.exists():
        return False
    html = _SHEET_OLD.sub('', page.read_text(encoding='utf-8'))
    if 'data-settings-open' not in html or '</body>' not in html:
        return False
    at = html.rindex('</body>')
    page.write_text(html[:at] + block + html[at:], encoding='utf-8')
    return True


def add_sheet(out: Path) -> list[str]:
    pages = ['index.html'] + [f'{s}/index.html' for s in SPORTS]
    block = sheet_block()
    return [p for p in pages if inject_sheet(out / p, block)]


def build_site(out: Path, live_url: str | None, sports: tuple[str, ...] = SPORTS,
               runner: Runner = run, fetcher: Fetcher = fetch) -> list[SportResult]:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    results = [build_sport(s, out, live_url, runner, fetcher) for s in sports]
    assemble_shared(out)
    results.append(build_home(out, runner, tuple(r.sport for r in results if not r.published)))
    add_strip(out, results)
    add_search(out, results)
    add_sheet(out)
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
