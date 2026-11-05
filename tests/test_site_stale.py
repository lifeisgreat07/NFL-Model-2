"""Stage 91 item 4 (audit 7, R2 and R14): the site never publishes an empty
board, and a page kept from the live site says it is old.

Run with: pytest tests/test_site_stale.py -v
"""
import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from src.site import build

LIVE = (b'<!DOCTYPE html><html><head></head><body class="page">\n<nav>menu</nav>'
        b'<main id="main-content" tabindex="-1"><h1>Board</h1>yesterday</main></body></html>')
BARE = b'<!DOCTYPE html><html><head></head><body class="page"><p>no main</p></body></html>'
NOW = datetime(2026, 11, 5, 14, 2, tzinfo=UTC)


def test_a_kept_page_says_since_when():
    out = build.mark_stale(LIVE, '2026-11-05 14:02').decode('utf-8')
    # Inside <main>, before its first child: under <body> it became a grid column of its own.
    assert out.index('<nav>') < out.index('<main id="main-content"') < out.index(build.STALE_MARK) < out.index('<h1>')
    bare = build.mark_stale(BARE, '2026-11-05 14:02').decode('utf-8')
    assert bare.index('<body class="page">') < bare.index(build.STALE_MARK) < bare.index('<p>no main')
    assert 'not been rebuilt since 2026-11-05 14:02 UTC' in out and 'role="status"' in out


def test_a_page_already_marked_keeps_its_first_date():
    once = build.mark_stale(LIVE, '2026-11-05 14:02')
    assert build.mark_stale(once, '2026-11-06 14:02') == once


def test_a_failed_build_keeps_the_live_page_with_the_line(tmp_path):
    res = build.build_sport('nhl', tmp_path, 'https://example.org/site', runner=lambda cmd: 1,
                            fetcher=lambda url: LIVE, now=NOW)
    assert res.kept_live and not res.built
    page = (tmp_path / 'nhl' / 'index.html').read_text(encoding='utf-8')
    assert 'not been rebuilt since 2026-11-05 14:02 UTC' in page and 'yesterday</main>' in page


def empty_schedule(tmp_path, sport):
    (tmp_path / 'results').mkdir()
    (tmp_path / 'results' / 'schedule_2026.json').write_text(json.dumps({'as_of': '2026-11-05', 'games': []}),
                                                             encoding='utf-8')
    return SimpleNamespace(results=tmp_path / 'results', predictions=tmp_path / 'predictions',
                           data=tmp_path / 'data', experiments=tmp_path / 'experiments')


def test_the_nhl_page_refuses_an_empty_schedule(tmp_path, monkeypatch):
    from src.sports.nhl import site
    monkeypatch.setattr(site, 'PATHS', empty_schedule(tmp_path, 'nhl'))
    with pytest.raises(ValueError, match='has no games'):
        site.payload(2026, NOW)


def test_the_nba_page_refuses_an_empty_schedule(tmp_path, monkeypatch):
    from src.sports.nba import site
    monkeypatch.setattr(site, 'PATHS', empty_schedule(tmp_path, 'nba'))
    with pytest.raises(ValueError, match='has no games'):
        site.board(2026)
