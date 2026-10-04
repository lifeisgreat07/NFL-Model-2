"""What the page gives away when it reaches off-site (Stage 30 item 9).

Two small leaks the 2026-09-29 re-audit found, enumerated so the next one is
caught rather than remembered:

- every link opening a new tab carries rel="noopener", so the opened page
  gets no handle on this one (one of six did not);
- every team-logo image, hot-linked from ESPN, carries
  referrerpolicy="no-referrer", so ESPN is not told which page asked.

Both are read from the template with comments blanked, and each enumeration
asserts it found what it must, so a matcher that goes blind fails.

Run with: pytest tests/test_outbound_hygiene.py -v
"""
import re

from src.pipeline.template_parts import JOINED_TEMPLATE

TEMPLATE = JOINED_TEMPLATE


def _page():
    text = TEMPLATE.read_text(encoding='utf-8')
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    return re.sub(r'/\*.*?\*/', '', text, flags=re.S)


def new_tab_links(page):
    return [a for a in re.findall(r'<a\b[^>]*>', page) if 'target="_blank"' in a]


def logo_images(page):
    return [i for i in re.findall(r'<img\b[^>]*>', page) if 'teamLogo(' in i]


def test_every_new_tab_link_is_noopener():
    links = new_tab_links(_page())
    assert len(links) >= 6, f'found only {len(links)} new-tab links; the matcher has gone blind'
    bare = [a for a in links if not re.search(r'rel="[^"]*\bnoopener\b', a)]
    assert not bare, f'new-tab links without rel="noopener": {bare}'


def test_every_logo_image_sends_no_referrer():
    imgs = logo_images(_page())
    assert len(imgs) >= 4, f'found only {len(imgs)} logo images; the matcher has gone blind'
    leaky = [i for i in imgs if 'referrerpolicy="no-referrer"' not in i]
    assert not leaky, f'logo images that tell ESPN which page asked: {leaky}'
