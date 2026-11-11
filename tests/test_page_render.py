"""One page renderer for the home, NFL, NHL and NBA pages (Stage 87 item 3).

src/core/page_render.py assembles a page from its shell and parts with
template_parts.join, then strips its comments, fills every placeholder in one
pass and hashes its scripts into the content security policy. Its fill
refuses a fill for a placeholder the page does not have and a placeholder left
without a fill.

Run with: pytest tests/test_page_render.py -v
"""
from pathlib import Path

import pytest

from src.core import page_render

ROOT = Path(__file__).resolve().parents[1]
RENDERERS = {
    'home': ROOT / 'src' / 'site' / 'home.py',
    'nfl': ROOT / 'src' / 'sports' / 'nfl' / 'generate_dashboard.py',
    'nhl': ROOT / 'src' / 'sports' / 'nhl' / 'site.py',
    'nba': ROOT / 'src' / 'sports' / 'nba' / 'site.py',
}


def test_every_placeholder_is_filled():
    assert page_render.fill('<p>__A__ and __B_2__</p>', {'__A__': 'x', '__B_2__': 'y'}) == '<p>x and y</p>'


def test_a_placeholder_without_a_fill_is_refused():
    with pytest.raises(ValueError, match=r"unfilled placeholders: \['__B__'\]"):
        page_render.fill('__A__ __B__', {'__A__': 'x'})


def test_a_fill_for_a_missing_placeholder_is_refused():
    """A renamed placeholder would otherwise fill nothing, silently."""
    with pytest.raises(ValueError, match=r"does not have: \['__GONE__'\]"):
        page_render.fill('__A__', {'__A__': 'x', '__GONE__': 'y'})


def test_an_include_left_in_the_page_is_refused():
    with pytest.raises(ValueError, match='unfilled placeholders'):
        page_render.fill('{% include "x.js" %}\n', {})


def test_a_key_that_is_not_a_placeholder_is_refused():
    with pytest.raises(ValueError, match='not placeholders'):
        page_render.fill('__A__', {'__A__': 'x', 'A': 'y'})


def test_the_fill_is_one_pass():
    """Text a fill puts on the page is never searched for a later placeholder: data that happens to read
    __B__ stays as written."""
    assert page_render.fill('__A__|__B__', {'__A__': 'says __B__', '__B__': 'b'}) == 'says __B__|b'


def test_assemble_takes_a_shared_part_before_the_directorys_own(tmp_path):
    (tmp_path / 'page.html').write_text('<x>\n{% include "a.css" %}\n{% include "b.js" %}\n</x>\n', encoding='utf-8')
    (tmp_path / 'a.css').write_text('local a\n', encoding='utf-8')
    (tmp_path / 'b.js').write_text('local b\n', encoding='utf-8')
    shared = tmp_path / 'shared.css'
    shared.write_text('shared a\n', encoding='utf-8')
    assert page_render.assemble(tmp_path, {'a.css': shared}) == '<x>\nshared a\nlocal b\n</x>\n'


def test_finish_strips_comments_before_it_fills():
    """A comment in the template is gone; the same text arriving in a fill is kept, because the data is never
    put through the comment lexer."""
    policy = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'"
    page = (f'<html><head><meta http-equiv="Content-Security-Policy" content="{policy}"></head>'
            '<body><script>/* note */\nconst D = __D__;</script></body></html>')
    out = page_render.finish(page, {'__D__': '"/* data */"'})
    assert '/* note */' not in out and '"/* data */"' in out
    assert "'unsafe-inline'" not in out.split('script-src', 1)[1].split(';', 1)[0], 'the script is hashed in'


@pytest.mark.parametrize('page', sorted(RENDERERS))
def test_every_page_is_rendered_by_the_shared_renderer(page):
    src = RENDERERS[page].read_text(encoding='utf-8')
    assert 'page_render.finish(' in src, f'{page} does not finish through src/core/page_render.py'
    assert ".replace('{% include" not in src, f'{page} expands an include by hand'
    assert "html.replace('__" not in src and "template.replace('__" not in src, f'{page} fills a placeholder by hand'
