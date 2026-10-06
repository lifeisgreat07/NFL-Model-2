"""Each sport's code keeps to its own sport.

The cheap check: no file under one sport's folder names another sport.
"""
from pathlib import Path

ROOT = Path(__file__).parent
SPORTS = ('nfl', 'nhl')


def test_no_sport_names_another():
    for sport in SPORTS:
        others = [s for s in SPORTS if s != sport]
        for path in sorted((ROOT / 'sports' / sport).rglob('*.py')):
            text = path.read_text(encoding='utf-8').lower()
            for other in others:
                assert other not in text, f'{path.relative_to(ROOT)} names {other}'


def test_the_nhl_page_lists_results():
    from sports.nhl.site import build
    assert '<h2>Latest results</h2>' in build()
