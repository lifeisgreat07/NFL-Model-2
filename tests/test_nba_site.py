"""The NBA's pages (src/sports/nba/site.py): the day board (Stage 65) and
the backtest said plainly (Stage 61), every figure read from the committed
files when the page is built, nothing of another sport read, and the NBA's
own names for storage and styles. The board itself is tests/test_nba_board.py.

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


def test_the_board_leads_and_the_no_picks_page_is_gone(built: tuple[dict, str]) -> None:
    """Stage 65: live picks from opening night, so the page that said there
    were none would now be false."""
    _, html = built
    assert re.search(r'<section class="page active" id="page-board">', html)
    assert 'id="game-grid"' in html and 'id="nba-day-strip"' in html
    assert 'No live NBA picks' not in html and 'Why No Picks' not in html and 'no live picks' not in html


def test_every_page_is_on_both_menus_and_the_checker_can_open_it(built: tuple[dict, str]) -> None:
    _, html = built
    pages = re.findall(r'<section class="page[^"]*" id="page-([a-z]+)"', html)
    assert pages == ['board', 'accuracy', 'modellab', 'method', 'reliability', 'changes']
    side = re.findall(r'class="nav-btn[^"]*" data-page="([a-z]+)"', html)
    bottom = re.findall(r'class="bnav-btn[^"]*" data-page="([a-z]+)"', html)
    # Since Stage 77 item 22 the phone nav keeps Methodology and Checking the
    # AI's work under More, as the NHL's and the NFL's do.
    more = re.findall(r'class="bnav-more-item[^"]*" data-page="([a-z]+)"', html)
    assert side == pages and bottom + more == pages and 'id="bnav-more-btn"' in html
    assert 'window.setActivePage = ' in html



def test_whats_changed_is_dated_newest_first_and_reaches_the_page(built) -> None:
    """Stage 104 item 2, as tests/test_nhl_site.py holds the NHL's."""
    from src.sports.nba import site as nba_site
    changes = json.loads((nba_site.TEMPLATE / 'changes.json').read_text(encoding='utf-8'))
    dates = [c['date'] for c in changes]
    assert dates and dates == sorted(dates, reverse=True)
    assert all(re.fullmatch(r'\d{4}-\d{2}-\d{2}', d) for d in dates)
    data, html = built
    assert data['changes'] == changes and 'id="changes-body"' in html
    js = (nba_site.TEMPLATE / 'nba.js').read_text(encoding='utf-8')
    assert 'renderReliability();\nrenderChanges();\n' in js.replace('\r\n', '\n'), 'the page is built at load, as every other page is'


def test_every_registration_whats_changed_names_exists_and_says_what_its_results_say() -> None:
    from src.sports.nba import site as nba_site
    root = Path(nba_site.__file__).resolve().parents[3]
    changes = json.loads((nba_site.TEMPLATE / 'changes.json').read_text(encoding='utf-8'))
    for c in changes:
        for path in re.findall(r'experiments/nba/\S+?\.json', c['text']):
            assert (root / path).exists(), path
    backtest = next(c for c in changes if 'stage61' in c['text'])
    answers = json.loads((root / 'experiments/nba/stage61/results/confirmation.json').read_text(encoding='utf-8'))
    labels = {k: q.get('label') for k, q in answers['questions'].items()}
    assert 'Model A beats the base rate' in backtest['text'] and labels['H1'] == 'ACCEPT'
    assert 'Model B beats Model A' in backtest['text'] and labels['H2'] == 'ACCEPT'
    assert 'does worse than the market alone' in backtest['text'] and labels['H3'] == 'REJECT'


def test_the_page_uses_the_nbas_own_names(built: tuple[dict, str]) -> None:
    _, html = built
    assert '<html lang="en" data-sport="nba">' in html
    keys = set(re.findall(r'''localStorage\.(?:get|set)Item\('([^']+)''', html))
    # site:cards: compact cards, chosen in the Settings sheet (Stage 80 item 57).
    # site:density: Compact spacing, the same sheet (Stage 80 item 64).
    assert keys == {'site:theme', 'nba:theme', 'site:cards', 'site:density'}
    css = (PAGES / 'nba.css').read_text(encoding='utf-8')
    green = [ln.strip() for ln in css.splitlines() if 'var(--good)' in ln]
    assert green == ['.nba-row-result.right{color:var(--good);}'], 'green means only a pick scored right'


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
