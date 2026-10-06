"""The NHL's pages (Stage 57): what the builder reads, what it embeds, and
that the template and its script agree about the page's parts."""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.core.sport import SportPaths
from src.sports.nhl import site

NOW = datetime(2026, 10, 6, 21, 5, tzinfo=UTC)


def _game(gid: str, day: str, home: str, away: str, status: str = 'scheduled', game_type: str = 'regular',
          **extra: object) -> dict[str, object]:
    g: dict[str, object] = {'game_id': gid, 'slate': day, 'start_utc': f'{day}T23:00:00Z', 'home': home, 'away': away,
                            'status': status, 'game_type': game_type, 'home_score': None, 'away_score': None,
                            'last_period': None, 'neutral_site': False}
    g.update(extra)
    return g


def _pick(gid: str, home: str, away: str, market: dict[str, object] | None = None) -> dict[str, object]:
    return {'game_id': gid, 'season': 2026, 'home': home, 'away': away, 'model_a': 0.55,
            'model_b': 0.57 if market else None, 'pick': home, 'pick_model': 'model_b' if market else 'model_a',
            'market': market, 'saved_utc': '2026-10-06T21:00:00Z',
            'goalies': {'home': {'player_id': 1, 'name': 'Home Goalie', 'status': 'Confirmed', 'basis': 'projected',
                                 'report': 'https://example.org/r'},
                        'away': {'player_id': 2, 'name': 'Away Goalie', 'status': None, 'basis': 'last_start',
                                 'report': None}}}


@pytest.fixture()
def nhl_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    paths = SportPaths('nhl', root=tmp_path)
    monkeypatch.setattr(site, 'PATHS', paths)
    games = [
        _game('2026010001', '2026-09-25', 'TOR', 'MTL', status='final', game_type='preseason'),
        _game('2026020001', '2026-10-05', 'TBL', 'PHI', status='final', home_score=4, away_score=1,
              last_period='REG'),
        _game('2026020002', '2026-10-06', 'TOR', 'NSH'),
        _game('2026020003', '2026-10-06', 'MTL', 'CAR'),
    ]
    paths.results.mkdir(parents=True)
    (paths.results / 'schedule_2026.json').write_text(json.dumps({'as_of': '2026-10-06', 'games': games}))
    (paths.results / 'graded_2026.json').write_text(json.dumps(
        [{'game_id': '2026020002', 'pick': 'TOR', 'result': 'correct'}]))
    folder = paths.predictions / '2026'
    folder.mkdir(parents=True)
    (folder / '2026020002.json').write_text(json.dumps(_pick('2026020002', 'TOR', 'NSH')))
    market = {'book': 'DraftKings', 'home_price': -218, 'away_price': 180, 'home_prob': 0.66}
    (folder / '2026020003.json').write_text(json.dumps(_pick('2026020003', 'MTL', 'CAR', market)))
    return tmp_path


def test_the_payload_reads_the_nhls_own_files(nhl_root: Path) -> None:
    data = site.payload(2026, NOW)
    assert data['season'] == 2026 and data['built_utc'] == '2026-10-06T21:05:00Z'
    assert data['schedule_as_of'] == '2026-10-06'
    assert sorted(data['picks']) == ['2026020002', '2026020003']
    assert len(data['teams']) == 32
    # nothing the daily run has not written yet is invented
    assert data['standings'] is None and data['ratings'] is None and data['backtest'] is None


def test_the_pages_read_only_the_nhls_folders() -> None:
    """The builder's folders are the NHL's, so the page can show nothing
    another sport wrote (decision record 0006)."""
    for folder in (site.PATHS.data, site.PATHS.predictions, site.PATHS.results, site.PATHS.experiments):
        assert folder.name == 'nhl' and folder.parent.parent == site.ROOT, folder


def test_preseason_games_are_left_off_the_board(nhl_root: Path) -> None:
    ids = [g['id'] for g in site.payload(2026, NOW)['games']]
    assert ids == ['2026020001', '2026020002', '2026020003']


def test_a_pick_carries_its_grade_and_an_ungraded_one_is_pending(nhl_root: Path) -> None:
    picks = site.payload(2026, NOW)['picks']
    assert picks['2026020002']['result'] == 'correct'
    assert picks['2026020003']['result'] == 'pending'


def test_a_pick_carries_the_market_it_was_saved_with_and_none_when_there_was_none(nhl_root: Path) -> None:
    picks = site.payload(2026, NOW)['picks']
    assert picks['2026020003']['market'] == {'book': 'DraftKings', 'hp': -218, 'ap': 180, 'prob': 0.66}
    assert picks['2026020003']['by'] == 'model_b'
    assert 'market' not in picks['2026020002']


def test_a_pick_carries_each_goalie_with_his_status_and_basis(nhl_root: Path) -> None:
    goalies = site.payload(2026, NOW)['picks']['2026020002']['goalies']
    assert goalies['home'] == {'name': 'Home Goalie', 'status': 'Confirmed', 'basis': 'projected'}
    assert goalies['away'] == {'name': 'Away Goalie', 'status': None, 'basis': 'last_start'}


def test_a_missing_schedule_stops_the_build(nhl_root: Path) -> None:
    (nhl_root / 'results' / 'nhl' / 'schedule_2026.json').unlink()
    with pytest.raises(FileNotFoundError, match='schedule'):
        site.payload(2026, NOW)


def test_the_bar_colours_are_pushed_apart_when_close() -> None:
    a, h = site.bar_colours('CAR', 'MTL')
    assert re.fullmatch(r'#[0-9A-F]{6}', a) and re.fullmatch(r'#[0-9A-F]{6}', h)
    assert a != h


def test_the_embedded_data_cannot_close_its_script_tag() -> None:
    out = site.safe_json({'name': '</script><script>alert(1)</script> & co'})
    assert '<' not in out and '>' not in out and '&' not in out
    assert json.loads(out) == {'name': '</script><script>alert(1)</script> & co'}


def test_a_font_that_does_not_match_its_manifest_stops_the_build(tmp_path: Path) -> None:
    (tmp_path / 'f.woff2').write_bytes(b'not the font')
    (tmp_path / 'manifest.json').write_text(json.dumps({'files': [
        {'file': 'f.woff2', 'sha256': '0' * 64, 'style': 'normal', 'unicode_range': 'U+0000-00FF'}]}))
    with pytest.raises(ValueError, match='sha256'):
        site.font_faces_css(tmp_path)


def test_the_built_page_fills_every_placeholder_and_embeds_the_data(nhl_root: Path) -> None:
    html = site.render(site.payload(2026, NOW))
    assert '{% include' not in html and '__NHL_JSON__' not in html and '__FONT_FACES__' not in html
    block = re.search(r'<script id="nhl-data" type="application/json">(.*?)</script>', html, re.S)
    assert block is not None
    assert json.loads(block.group(1))['picks']['2026020003']['market']['book'] == 'DraftKings'
    assert '<html lang="en" data-sport="nhl">' in html


def test_main_writes_the_page(nhl_root: Path, tmp_path: Path) -> None:
    out = tmp_path / 'out' / 'index.html'
    assert site.main(['--out', str(out), '--season', '2026'], now=NOW) == 0
    assert out.read_text(encoding='utf-8').startswith('<!DOCTYPE html>')


def test_every_element_the_script_looks_up_is_in_the_template() -> None:
    """The script fills the page by id; an id it asks for that the template
    lacks is a page that throws on load and shows nothing."""
    js = (site.TEMPLATE / 'nhl.js').read_text(encoding='utf-8')
    markup = (site.TEMPLATE / 'body.html').read_text(encoding='utf-8') + (site.TEMPLATE / 'page.html').read_text(
        encoding='utf-8')
    wanted = set(re.findall(r"getElementById\('([\w-]+)'\)", js))
    present = set(re.findall(r'\bid="([\w-]+)"', markup))
    assert wanted, 'the script looks nothing up: the pattern no longer reads it'
    assert wanted <= present, sorted(wanted - present)


def test_every_page_the_menu_opens_exists() -> None:
    body = (site.TEMPLATE / 'body.html').read_text(encoding='utf-8')
    targets = set(re.findall(r'data-page="([\w-]+)"', body))
    pages = set(re.findall(r'id="page-([\w-]+)"', body))
    assert targets and targets == pages


def test_the_script_reads_only_fields_the_builder_writes() -> None:
    """Each top-level `DATA.<field>` the script reads is a key `payload`
    returns, so a renamed field cannot leave a page silently empty."""
    js = (site.TEMPLATE / 'nhl.js').read_text(encoding='utf-8')
    src = Path(site.__file__).read_text(encoding='utf-8')
    body = src[src.index('def payload'):src.index('def font_faces_css')]
    written = set(re.findall(r"^\s+'(\w+)':", body, re.M))
    read = set(re.findall(r'\bDATA\.(\w+)', js))
    assert read and read <= written, sorted(read - written)
