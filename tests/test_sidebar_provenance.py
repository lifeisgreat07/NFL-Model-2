"""The sidebar footer says what made the page; the Week Board says when.

Stage 11 (CLAUDE.md, "Stage 11 - Integrity and access"). The footer read
"Trained on: current nflfastR history / 3 week(s) saved / Latest: 2026_week3
/ Data as of ...": a file-name week key, a "(s)" plural and a data project's
name -- the build talking to itself. It became one line, for example "Model
2.5, built from NFL play-by-play since 2020. Updated Sep 26, 2026, 19:11 UTC."

Stage 13 moved the "Updated" half into the Week Board's header: the sidebar
is hidden below 1080px, so no phone or tablet ever saw when the page was
built. The footer now reads "Model 2.5, built from NFL play-by-play since
2020." and the header "Updated Sep 26, 2026, 19:11 UTC.", in a <time>.

Every part comes from config or the clock, so neither can drift from what
built the page; these tests hold them to both.

Run with: pytest tests/test_sidebar_provenance.py -v
"""
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from src.core.template_parts import JOINED_TEMPLATE
from src.sports.nfl import config
from src.sports.nfl import generate_dashboard as gd

WHEN = datetime(2026, 9, 26, 19, 11, tzinfo=UTC)
TEMPLATE = JOINED_TEMPLATE


def _text(html):
    return re.sub(r'<[^>]+>', '', html)


def _code():
    src = (ROOT / 'src' / 'sports' / 'nfl' / 'generate_dashboard.py').read_text(encoding='utf-8')
    code = re.sub(r'(?s)""".*?"""', '', src)
    return re.sub(r'(?m)#.*$', '', code)


def test_the_line_reads_as_a_sentence():
    # Unordered, and not starting at today's 2020, so a first season typed
    # into the generator -- or read off the list's first entry -- is caught.
    line = gd.provenance_line(model_version='9.1', train_seasons=[2021, 2018, 2025])
    assert _text(line) == 'Model 9.1, built from NFL play-by-play since 2018.'


def test_it_is_one_line():
    assert '<br' not in gd.provenance_line().lower()


def test_the_version_and_first_season_come_from_config():
    """The defaults are config's, not copies typed into the generator."""
    text = _text(gd.provenance_line())
    assert f'Model {config.MODEL_VERSION},' in text
    assert f'since {min(config.TRAIN_SEASONS)}.' in text


def test_the_updated_line_names_its_time_zone():
    line = gd.updated_line(WHEN)
    assert _text(line) == 'Updated Sep 26, 2026, 3:11 PM ET.'  # ET since Stage 68 item 18c (U18)
    assert '<time datetime="2026-09-26T19:11Z">' in line, 'the instant is not machine-readable'


def test_a_morning_build_keeps_its_minutes_and_its_day():
    early = datetime(2026, 1, 4, 6, 5, tzinfo=UTC)
    assert 'Updated Jan 4, 2026, 1:05 AM ET.' in _text(gd.updated_line(early))
    assert 'Updated Jan 3, 2026, 11:30 PM ET.' in _text(gd.updated_line(datetime(2026, 1, 4, 4, 30, tzinfo=UTC)))
    assert 'datetime="2026-01-04T06:05Z"' in gd.updated_line(early)


def test_the_page_footer_is_the_provenance_line_and_nothing_else():
    code = _code()
    assigned = re.findall(r'foot_html\s*=\s*(.+)', code)
    assert assigned == ['provenance_line()'], (
        f'the sidebar footer is no longer just the provenance line: {assigned}')
    for internal in ('Trained on', 'week(s)', 'Latest:', 'nflfastR history'):
        assert internal not in code, f'build internals are back in the generator: {internal!r}'
    assert 'Updated' not in _text(gd.provenance_line()), (
        'the build time is back in the sidebar, which no phone or tablet shows')


def test_the_build_time_is_in_the_week_board_header():
    code = _code()
    assert re.findall(r'updated_html\s*=\s*(.+)', code) == ['updated_line(datetime.now(UTC))']
    assert "html.replace('__BOARD_UPDATED__', updated_html)" in code
    src = TEMPLATE.read_text(encoding='utf-8')
    board = re.search(r'<section class="page[^"]*" id="page-board">(.*?)</section>', src, re.S)
    assert board, 'the Week Board section is no longer findable'
    head = re.search(r'<div class="page-head">(.*?)\n    </div>', board.group(1), re.S)
    assert head and '__BOARD_UPDATED__' in head.group(1), (
        "the build time is not in the Week Board's header")
    assert src.count('__BOARD_UPDATED__') == 1
