"""One product name: Sportalytics (Stage 67; Mark, 2026-10-09).

Stage 29 (2026-09-29) settled six names on one, Pick'em Model. Stage 67
renames it Sportalytics, with wordmark W2 from the "Sportalytics Icons and
Wordmark" canvas: "Sporta" in the text colour and "lytics" in the accent
colour, on one line. The repository keeps its name, because renaming it
moves the live address.

The old name must show nowhere a visitor can see. That means the page text,
tab titles, link previews, the home-screen name, the share image's source,
the printed sheet and the README. test_the_old_name_is_nowhere_a_visitor_sees
reads every file the site is built from, and every file it serves as is. A
generic "pick'em", the confidence-pool format, is not the name, and stays.

Run with: pytest tests/test_product_name.py -v
"""
import re
from pathlib import Path

from src.core.template_parts import read_template

REPO = Path(__file__).resolve().parents[1]
NAME = 'Sportalytics'
WORDMARK = 'Sporta<span class="wm-accent">lytics</span>'
RETIRED = ('Command Board', "Pick'em Board", "NFL Pick'em Model", 'COMMAND<br>BOARD')
#: The Stage 29 name, in any case, apostrophe or line break, and its two-line sidebar form.
OLD_NAME = re.compile(r"pick(?:'|&#39;|’|&rsquo;)?em\s+model|PICK'EM<br>", re.I)

#: Everything the site is built from or serves.
VISITOR_FILES = sorted(
    {p for pattern in ('src/dashboard/*.html', 'src/dashboard/*.js', 'src/dashboard/*.css',
                       'src/sports/*/pages/*', 'src/site/home/*', 'src/site/*.py',
                       'assets/*.webmanifest', 'assets/*.svg', 'assets/og/*.html')
     for p in REPO.glob(pattern) if p.is_file()}
    | {REPO / 'README.md', REPO / 'src' / 'sports' / 'nfl' / 'generate_picks_pdf.py'})


def read(rel):
    return (REPO / rel).read_text(encoding='utf-8')


def test_the_tab_the_sidebar_and_the_phone_bar_say_the_name():
    t = read_template()
    assert f'<title>NFL Week Board — {NAME}</title>' in t
    assert "`NFL ${heading.textContent.trim()} — Sportalytics`" in t, (
        'the other pages no longer end their tab title with the name')
    assert f'<h1 class="wordmark"><a class="wordmark-link" href="../">{WORDMARK}</a></h1>' in t, 'the sidebar heading is not wordmark W2'
    assert f'<h1>{WORDMARK} <span class="topbar-sub">' in t, 'the phone bar is not wordmark W2'
    assert f'<meta name="apple-mobile-web-app-title" content="{NAME}">' in t


def test_every_page_carries_the_wordmark():
    for rel in ('src/sports/nhl/pages/body.html', 'src/sports/nba/pages/body.html'):
        body = read(rel)
        assert f'<h1 class="wordmark"><a class="wordmark-link" href="../">{WORDMARK}</a></h1>' in body, f'{rel}: sidebar'
        assert f'<h1>{WORDMARK} <span class="topbar-sub">' in body, f'{rel}: phone bar'
    assert f'<span class="home-wordmark">{WORDMARK}</span>' in read('src/site/home/page.html')


def test_lytics_takes_the_accent_colour():
    css = read('src/dashboard/styles.css')
    assert re.search(r'\.wm-accent\{color:var\(--accent\);\}', css), 'W2 is one colour'


def test_the_phone_bar_does_not_shout_the_wordmark():
    """W2 is mixed case. The phone bar's heading was set in capitals for the
    old name, which turned the wordmark into SPORTALYTICS."""
    css = read('src/dashboard/styles.css')
    rule = re.search(r'\.topbar h1\{([^}]*)\}', css).group(1)
    assert 'uppercase' not in rule


def test_the_readme_the_printed_sheet_and_the_home_screen_say_the_name():
    assert read('README.md').splitlines()[0] == f'# {NAME}'
    pdf = read('src/sports/nfl/generate_picks_pdf.py')
    assert f'title=f"{NAME} {{season}} Week {{week}}"' in pdf
    assert f'Paragraph(f"{NAME} &mdash; {{season}} Week {{week}}"' in pdf
    manifest = read('assets/site.webmanifest')
    assert f'"name": "{NAME}"' in manifest and f'"short_name": "{NAME}"' in manifest


def test_the_old_name_is_nowhere_a_visitor_sees():
    assert len(VISITOR_FILES) > 20, 'the file search is broken'
    left = [f'{p.relative_to(REPO).as_posix()}: {m.group(0)!r}'
            for p in VISITOR_FILES for m in OLD_NAME.finditer(p.read_text(encoding='utf-8', errors='replace'))]
    assert not left, f'the old name is still where a visitor sees it: {left}'


def test_the_old_name_pattern_finds_every_spelling():
    """Synthetic, so the search cannot quietly stop matching."""
    for text in ("Pick'em Model", 'pick&#39;em model', 'Pick’em Model', "PICK'EM<br>MODEL",
                 "Pick'em\n     Model"):
        assert OLD_NAME.search(text), text
    assert not OLD_NAME.search("A pick'em format where you rank games")


def test_no_retired_name_is_left_where_a_reader_sees_it():
    for rel in ('src/dashboard/', 'README.md', 'src/sports/nfl/generate_picks_pdf.py'):
        text = read_template() if rel == 'src/dashboard/' else read(rel)
        left = [n for n in RETIRED if re.search(re.escape(n), text)]
        assert not left, f'{rel} still says {left}'
