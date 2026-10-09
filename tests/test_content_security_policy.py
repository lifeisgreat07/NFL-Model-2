"""Every page says what it may load (Stage 45 item 2).

The pages are single files: their code and styles are inline, their fonts and
icons are data: URLs, and the only things fetched from elsewhere are team logos:
ESPN's on the NFL board, the NHL's own on the NHL's pages (found by running
the browser checks with the policy in place: the first draft listed ESPN
alone). A Content-Security-Policy meta tag says exactly that,
so anything else (a script or image from another host, a fetch, a form, a
<base> that re-points relative links) is refused by the browser.

'unsafe-inline' stays for scripts and styles: everything the pages run is
inline, the NFL board has inline event handlers and style attributes, and a
hash per script would have to be rebuilt on every page build. What the policy
buys is that nothing outside the page can run in it or be reached from it.

The browser checks (tests/browser/check_page.py) report any violation the
browser logs, with the network both blocked and allowed.

Run with: pytest tests/test_content_security_policy.py -v
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CSP = ("default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
       "img-src 'self' data: https://a.espncdn.com https://assets.nhle.com; font-src data:; connect-src 'none'; "
       "manifest-src 'self'; base-uri 'none'; form-action 'none'")
META = f'<meta http-equiv="Content-Security-Policy" content="{CSP}">'
PAGES = ['src/dashboard/page.html', 'src/sports/nhl/pages/page.html', 'src/sports/nba/pages/page.html',
         'src/site/home/page.html']
LOADS = re.compile(r'<(?:script|style|link)\b', re.I)


@pytest.mark.parametrize('rel', PAGES)
def test_each_page_carries_the_policy_once(rel):
    text = (ROOT / rel).read_text(encoding='utf-8')
    assert text.count(META) == 1, f'{rel}: the policy is missing or not as written'
    assert text.count('Content-Security-Policy') == 1, f'{rel}: a second policy would combine with the first'


@pytest.mark.parametrize('rel', PAGES)
def test_the_policy_comes_before_anything_it_governs(rel):
    """A meta policy applies only to what follows it in the document."""
    text = (ROOT / rel).read_text(encoding='utf-8')
    first = LOADS.search(text)
    assert first and text.index(META) < first.start(), f'{rel}: a script, style or link comes before the policy'


def test_every_page_template_is_covered():
    found = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'src').rglob('page.html'))
    assert found == sorted(PAGES), f'a page template the policy test does not read: {found}'


def test_the_only_outside_hosts_any_page_loads_from_are_the_logo_hosts():
    """An image or script from a host the policy does not list would be
    refused; this finds one before the browser does. The page builders are
    read too: the NHL's logo addresses are written by its Python."""
    hosts = set()
    for p in (ROOT / 'src').rglob('*'):
        if p.suffix in ('.html', '.js', '.css', '.py') and p.is_file():
            # A <meta> names the share image for other sites; the page does not load it.
            t = re.sub(r'<meta\b[^>]*>', '', p.read_text(encoding='utf-8'))
            hosts |= set(re.findall(r'(?:src=["\']|url\(["\']?|[\'"`])https://([A-Za-z0-9.-]+)/[^"\'`\s]*\.(?:png|svg|jpe?g|gif|webp|js)', t))
    assert hosts == {'a.espncdn.com', 'assets.nhle.com'}, hosts


def test_the_browser_check_reports_a_violation():
    text = (ROOT / 'tests' / 'browser' / 'check_page.py').read_text(encoding='utf-8')
    assert "'Content Security Policy' in m.text" in text
    assert "'csp':" in text, 'the rule needs a fixture that it must catch'
