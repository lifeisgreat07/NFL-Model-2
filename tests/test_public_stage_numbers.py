"""Stage 89 item 8: internal stage numbers stay off the public pages and the README.

A "Stage 9" means something to whoever planned the work and nothing to a
reader. Mark's call (2026-11-05): they leave the pages and the README, and
the Model Lab's registration ids ("Stage 33 R1", "Stage 5 H5"), which name a
registered experiment a reader can look up, stay. Comments and scripts are
not shown, so only the text a visitor reads is checked.

Run with: pytest tests/test_public_stage_numbers.py -v
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGES = ['src/dashboard/body.html', 'src/site/home/page.html', 'README.md'] + sorted(
    p.relative_to(ROOT).as_posix() for s in ('nhl', 'nba') for p in (ROOT / 'src' / 'sports' / s / 'pages').glob('*.html'))
#: "Stage 33 R1", "Stage 6 N4", "Stage 5 H10": a registration id, which stays.
REGISTRATION = re.compile(r'Stage \d+ [A-Z]+\d+\b')


def visible(text):
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    text = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '', text, flags=re.S)
    return REGISTRATION.sub('', text)


@pytest.mark.parametrize('rel', PAGES)
def test_no_internal_stage_number_is_shown(rel):
    shown = re.findall(r'.{0,40}\bStage \d+.{0,30}', visible((ROOT / rel).read_text(encoding='utf-8')))
    assert not shown, f'{rel} shows internal stage numbers: {shown}'


def test_a_registration_id_is_not_counted_and_a_stage_is():
    assert visible('<p>Pre-registered, Stage 33 R1 &middot;</p>') == '<p>Pre-registered,  &middot;</p>'
    assert 'Stage 9' in visible('<p>validated (Stage 9)</p><!-- Stage 4 -->')
    assert 'Stage 4' not in visible('<p>x</p><!-- Stage 4 -->')
