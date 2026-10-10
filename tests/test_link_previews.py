"""Each board has its own link preview (Stage 68 item 22).

The NHL's and NBA's pages had no Open Graph or Twitter tags and no
home-screen icon, so a shared link previewed as a bare address; the NFL
board's og:title was the site's name, the same as the home page's.

Run with: pytest tests/test_link_previews.py -v
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://lifeisgreat07.github.io/NFL-Model-2/'
PAGES = {'nfl': ('src/dashboard/page.html', 'NFL Week Board — Sportalytics'),
         'nhl': ('src/sports/nhl/pages/page.html', 'NHL Day Board — Sportalytics'),
         'nba': ('src/sports/nba/pages/page.html', 'NBA Day Board — Sportalytics')}


def meta(html, prop):
    m = re.search(r'<meta (?:property|name)="' + re.escape(prop) + r'" content="([^"]*)">', html)
    return m.group(1) if m else None


@pytest.mark.parametrize('sport', PAGES)
def test_each_board_previews_as_itself(sport):
    rel, title = PAGES[sport]
    html = (ROOT / rel).read_text(encoding='utf-8')
    assert meta(html, 'og:title') == title
    assert meta(html, 'og:url') == f'{BASE}{sport}/'
    assert meta(html, 'og:description') == meta(html, 'description') and meta(html, 'description')
    assert meta(html, 'og:image') == f'{BASE}og-card.png' and meta(html, 'twitter:card') == 'summary_large_image'
    assert '<link rel="apple-touch-icon" href="../assets/apple-touch-icon.png">' in html
