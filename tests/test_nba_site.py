"""The NBA's pages (Stage 61, src/sports/nba/site.py): the backtest said
plainly and no board, every figure read from the committed files when the
page is built, nothing of another sport read, and the NBA's own names for
storage and styles.

Run with: pytest tests/test_nba_site.py -v
"""
from __future__ import annotations

import csv
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.core.sport import SportPaths
from src.sports.nba import site

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / 'src' / 'sports' / 'nba' / 'pages'
NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
RESULTS = ROOT / 'experiments' / 'nba' / 'stage61' / 'results'


@pytest.fixture(scope='module')
def built() -> tuple[dict, str]:
    data = site.payload(NOW)
    return data, site.render(data)


def embedded(html: str) -> dict:
    block = re.search(r'<script id="nba-data" type="application/json">(.*?)</script>', html, re.S)
    assert block is not None
    return json.loads(block.group(1))


def test_the_page_carries_the_committed_backtest_and_grid_unchanged(built: tuple[dict, str]) -> None:
    data, html = built
    got = embedded(html)
    assert got['backtest'] == json.loads((RESULTS / 'confirmation.json').read_text(encoding='utf-8'))
    assert got['tuning'] == json.loads((RESULTS / 'tuning.json').read_text(encoding='utf-8'))
    assert got == json.loads(json.dumps(data))


def test_the_coverage_is_each_seasons_games_and_prices(built: tuple[dict, str]) -> None:
    data, _ = built
    seasons = [c['season'] for c in data['coverage']]
    p = data['protocol']
    assert seasons == list(range(p['training_from_season'], p['confirmation_seasons'][-1] + 1))
    for c in data['coverage']:
        folder = ROOT / 'data' / 'nba' / 'history'
        with (folder / f"games_{c['season']}.csv").open(encoding='utf-8', newline='') as f:
            games = {r['game_id'] for r in csv.DictReader(f)}
        with (folder / f"market_{c['season']}.csv").open(encoding='utf-8', newline='') as f:
            market = [r for r in csv.DictReader(f) if r['game_id'] in games]
        assert c == {'season': c['season'], 'games': len(games), 'priced': len({r['game_id'] for r in market}),
                     'closing': sum(r['closing'] == 'True' for r in market)}
        assert 0 <= c['closing'] <= c['priced'] <= c['games'] and c['priced'] > 0


def test_no_answer_or_figure_is_written_into_the_page_by_hand() -> None:
    """The labels and numbers come from the results files, so a re-run that
    changed an answer changes the page with it."""
    js = (PAGES / 'nba.js').read_text(encoding='utf-8')
    assert not re.search(r'\b(ACCEPT|REJECT)\b', js)
    assert not re.search(r'0\.\d{3,}', js), 'a figure is written into the script'
    for text in ((PAGES / 'body.html').read_text(encoding='utf-8'), (PAGES / 'page.html').read_text(encoding='utf-8')):
        assert not re.search(r'\b(ACCEPT|REJECT)\b|0\.\d{3,}', text)


def test_there_is_no_board_and_the_page_says_why(built: tuple[dict, str]) -> None:
    _, html = built
    assert not re.search(r'id="(page-board|game-grid)"', html)
    assert 'No live NBA picks this season.' in html


def test_every_page_is_on_both_menus_and_the_checker_can_open_it(built: tuple[dict, str]) -> None:
    _, html = built
    pages = re.findall(r'<section class="page[^"]*" id="page-([a-z]+)"', html)
    assert pages == ['season', 'modellab', 'method', 'reliability']
    side = re.findall(r'class="nav-btn[^"]*" data-page="([a-z]+)"', html)
    bottom = re.findall(r'class="bnav-btn[^"]*" data-page="([a-z]+)"', html)
    assert side == pages and bottom == pages
    assert 'window.setActivePage = ' in html


def test_the_page_uses_the_nbas_own_names(built: tuple[dict, str]) -> None:
    _, html = built
    assert '<html lang="en" data-sport="nba">' in html
    keys = set(re.findall(r'''localStorage\.(?:get|set)Item\('([^']+)''', html))
    assert keys == {'site:theme', 'nba:theme'}
    css = (PAGES / 'nba.css').read_text(encoding='utf-8')
    assert '--good' not in css, 'green means only a pick scored right'


def test_the_page_reads_the_nbas_own_folders() -> None:
    for folder in (site.PATHS.data, site.PATHS.experiments):
        assert folder.name == 'nba', folder


def test_a_missing_result_stops_the_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(site, 'PATHS', SportPaths('nba', root=tmp_path))
    with pytest.raises(FileNotFoundError, match='registry.json'):
        site.payload(NOW)


def test_nothing_unfilled_is_left_in_the_page(built: tuple[dict, str]) -> None:
    _, html = built
    assert '__NBA_JSON__' not in html and '__FONT_FACES__' not in html and '{% include' not in html
    assert '</script>' not in embedded_text(html)


def embedded_text(html: str) -> str:
    block = re.search(r'<script id="nba-data" type="application/json">(.*?)</script>', html, re.S)
    assert block is not None
    return block.group(1)
