"""What a search result, a link preview and a phone's browser bar say (Stage 68 item 17).

The 2026-10-09 audit found the home page's description, og:description and
ld+json still saying "the NFL and the NHL ... with the NBA's backtest" and
the web app manifest "NFL and NHL", with the NBA live from opening night.
It also found the manifest's theme_color differing from the pages'; the
manifest was the one that matched the background (--n0, #0B0D10), so the
four pages' theme-color meta moved, not the manifest.

Run with: pytest tests/test_site_meta.py -v
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ['src/site/home/page.html', 'src/dashboard/page.html',
         'src/sports/nhl/pages/page.html', 'src/sports/nba/pages/page.html']
MANIFEST = json.loads((ROOT / 'assets' / 'site.webmanifest').read_text(encoding='utf-8'))


def bg():
    css = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
    n0 = re.search(r'--n0:(#[0-9A-Fa-f]{6})', css).group(1)
    assert re.search(r'--bg:var\(--n0\)', css)
    return n0.upper()


def test_every_page_and_the_manifest_share_the_backgrounds_colour():
    want = bg()
    assert MANIFEST['theme_color'].upper() == want
    for rel in PAGES:
        m = re.search(r'<meta name="theme-color" content="(#[0-9A-Fa-f]{6})">', (ROOT / rel).read_text(encoding='utf-8'))
        assert m and m.group(1).upper() == want, rel


def test_the_sites_descriptions_name_all_three_sports():
    home = (ROOT / 'src/site/home/page.html').read_text(encoding='utf-8')
    found = re.findall(r'(?:name="description"|property="og:description") content="([^"]+)"', home)
    found += re.findall(r'"description": "([^"]+)"', home) + [MANIFEST['description']]
    assert len(found) == 4
    for d in found:
        assert all(s in d for s in ('NFL', 'NHL', 'NBA')), d
        assert 'backtest' not in d, d
