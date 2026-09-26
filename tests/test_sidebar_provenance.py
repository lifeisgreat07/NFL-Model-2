"""The sidebar footer is one plain provenance line, generated from config.

Stage 11 (CLAUDE.md, "Stage 11 - Integrity and access"). The footer read
"Trained on: current nflfastR history / 3 week(s) saved / Latest: 2026_week3
/ Data as of ...": a file-name week key, a "(s)" plural and a data project's
name -- the build talking to itself. It now reads, for example, "Model 2.5,
built from NFL play-by-play since 2020. Updated Sep 26, 2026, 19:11 UTC."

Every part comes from config or the clock, so the line cannot drift from
what built the page; these tests hold it to both.

Run with: pytest tests/test_sidebar_provenance.py -v
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import config  # noqa: E402
import generate_dashboard as gd  # noqa: E402

WHEN = datetime(2026, 9, 26, 19, 11, tzinfo=timezone.utc)


def _text(html):
    return re.sub(r'<[^>]+>', '', html)


def test_the_line_reads_as_a_sentence():
    # Unordered, and not starting at today's 2020, so a first season typed
    # into the generator -- or read off the list's first entry -- is caught.
    line = gd.provenance_line(WHEN, model_version='9.1', train_seasons=[2021, 2018, 2025])
    assert _text(line) == ('Model 9.1, built from NFL play-by-play since 2018. '
                           'Updated Sep 26, 2026, 19:11 UTC.')


def test_it_is_one_line():
    assert '<br' not in gd.provenance_line(WHEN).lower()


def test_the_version_and_first_season_come_from_config():
    """The defaults are config's, not copies typed into the generator."""
    text = _text(gd.provenance_line(WHEN))
    assert f'Model {config.MODEL_VERSION},' in text
    assert f'since {min(config.TRAIN_SEASONS)}.' in text


def test_a_morning_build_keeps_its_leading_zero():
    early = datetime(2026, 1, 4, 6, 5, tzinfo=timezone.utc)
    assert 'Updated Jan 4, 2026, 06:05 UTC.' in _text(gd.provenance_line(early))


def test_the_page_footer_is_the_provenance_line_and_nothing_else():
    src = (ROOT / 'src' / 'generate_dashboard.py').read_text(encoding='utf-8')
    code = re.sub(r'(?s)""".*?"""', '', src)
    code = re.sub(r'(?m)#.*$', '', code)
    assigned = re.findall(r'foot_html\s*=\s*(.+)', code)
    assert assigned == ['provenance_line(datetime.now(timezone.utc))'], (
        f'the sidebar footer is no longer just the provenance line: {assigned}')
    for internal in ('Trained on', 'week(s)', 'Latest:', 'nflfastR history'):
        assert internal not in code, f'build internals are back in the generator: {internal!r}'
