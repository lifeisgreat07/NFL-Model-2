"""What the search box can find (Stage 80 item 56, the 2026-10-13 UI/UX audit's F6).

The site build hands every page one index, made after all four are built
(src/site/build.py add_search), so a search on the NHL's page finds an NFL
team as readily as an NHL one:

- teams: every club of each published sport, its code and full name, from
  each sport's own list (`data/nfl/team_history.json`, the NHL's and the
  NBA's `teams.NAMES`);
- pages: each published sport's pages, read from its built page's sidebar,
  so a page added there is found without a list here to keep;
- experiments: the NFL Model Lab's rows, read from its built page, each
  with the address its row gets in the page (#modellab/<slug>, made by
  app.js experimentSlug, which experiment_slug copies and the suite holds
  equal).

The games are the slate's (src/site/home.py slate()), already on the page
for the Next games strip.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

_NAV = re.compile(r'<button class="nav-btn[^"]*" data-page="([a-z]+)"[^>]*>(.*?)</button>', re.S)
_LAB = '<div class="table-wrap" data-scroll-label="Experiment log">'
_ROW = re.compile(r'<tr[^>]*>\s*<td[^>]*>(.*?)</td>', re.S)


def _text(fragment: str) -> str:
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', fragment))).strip()


def pages(page: str) -> list[list[str]]:
    """A built sport page's pages, as its sidebar lists them: [name, label]."""
    return [[name, _text(label)] for name, label in _NAV.findall(page)]


def experiment_slug(text: str) -> str:
    """app.js experimentSlug, in Python."""
    slug = re.sub(r'^-+|-+$', '', re.sub(r'[^a-z0-9]+', '-', text.lower()))
    return slug[:48].rstrip('-')


def experiments(page: str) -> list[list[str]]:
    """The NFL Model Lab's rows: [slug, name], a slug made unique as
    app.js routeKnown makes it."""
    if _LAB not in page:
        return []
    table = page[page.index(_LAB):]
    table = table[:table.index('</table>')] if '</table>' in table else table
    out: list[list[str]] = []
    seen: list[str] = []
    for cell in _ROW.findall(table):
        # textContent, as the page reads it: the cell's text, tags dropped.
        raw = html.unescape(re.sub(r'<[^>]+>', '', cell))
        slug, n = experiment_slug(raw), 2
        while slug in seen:
            slug = experiment_slug(raw) + '-' + str(n)
            n += 1
        seen.append(slug)
        out.append([slug, _text(cell)])
    return out


def team_names(root: Path = ROOT) -> dict[str, dict[str, str]]:
    from src.sports.nba import teams as nba_teams
    from src.sports.nhl import teams as nhl_teams
    nfl_file = root / 'data' / 'nfl' / 'team_history.json'
    nfl = json.loads(nfl_file.read_text(encoding='utf-8')).get('names', {}) if nfl_file.exists() else {}
    return {'nfl': dict(nfl), 'nhl': dict(nhl_teams.NAMES), 'nba': dict(nba_teams.NAMES)}


def index(out: Path, published: set[str], root: Path = ROOT) -> dict[str, Any]:
    """The search index for a built site in `out`: published sports only,
    so nothing found leads to a page this build has not got."""
    names = team_names(root)
    found: dict[str, Any] = {'teams': [], 'pages': [], 'experiments': []}
    for sport in ('nfl', 'nhl', 'nba'):
        if sport not in published:
            continue
        found['teams'] += [[sport, abbr, name] for abbr, name in sorted(names.get(sport, {}).items())]
        page = out / sport / 'index.html'
        text = page.read_text(encoding='utf-8') if page.exists() else ''
        found['pages'] += [[sport, name, label] for name, label in pages(text)]
        if sport == 'nfl':
            found['experiments'] += [[sport, slug, name] for slug, name in experiments(text)]
    return found
