"""One product name: Pick'em Model (Stage 29; Mark, 2026-09-29).

The 2026-09-28 audit counted six names for one site: the repository
"NFL-Model-2", the README "NFL Pick'em Model", the tab "Pick'em Model --
Command Board", the sidebar "COMMAND BOARD", the link preview "The Pick'em
Model" and the iPhone home screen "Pick'em Board". The repository keeps its
name (renaming it moves the live address); everything a reader sees now says
Pick'em Model. "The Pick'em Model" in the link preview and the share image
is the same name with an article, and stays.

Run with: pytest tests/test_product_name.py -v
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NAME = "Pick'em Model"
RETIRED = ('Command Board', "Pick'em Board", "NFL Pick'em Model", 'COMMAND<br>BOARD')


def read(rel):
    return (REPO / rel).read_text(encoding='utf-8')


def test_the_tab_the_sidebar_and_the_phone_bar_say_the_name():
    t = read('src/dashboard_template.html')
    assert f'<title>Week Board \u2014 {NAME}</title>' in t
    assert "`${heading.textContent.trim()} \u2014 Pick'em Model`" in t, (
        'the other pages no longer end their tab title with the name')
    assert "<h1>PICK'EM<br>MODEL</h1>" in t, 'the sidebar heading is not the name'
    assert f'<h1>{NAME} <span class="topbar-sub">' in t, 'the phone bar is not the name'
    assert f'<meta name="apple-mobile-web-app-title" content="{NAME}">' in t


def test_the_readme_and_the_printed_sheet_say_the_name():
    assert read('README.md').splitlines()[0] == f'# {NAME}'
    pdf = read('src/generate_picks_pdf.py')
    assert f'title=f"{NAME} {{season}} Week {{week}}"' in pdf
    assert f'Paragraph(f"{NAME} &mdash; {{season}} Week {{week}}"' in pdf


def test_no_retired_name_is_left_where_a_reader_sees_it():
    for rel in ('src/dashboard_template.html', 'README.md', 'src/generate_picks_pdf.py'):
        text = read(rel)
        left = [n for n in RETIRED if re.search(re.escape(n), text)]
        assert not left, f'{rel} still says {left}'
