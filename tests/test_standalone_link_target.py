"""A link that stands alone on its line has a 24px target (WCAG 2.5.8).

Stage 12 (CLAUDE.md). The five "Read the case study" / "Read the lessons"
links on "Checking the AI's work" each sit alone in a paragraph, so each is a
target of its own, and each measured under 24px: 16px in the fallback face,
18px in Plus Jakarta Sans (Booth on #112, 2026-09-26). A link INSIDE a
sentence, like the one to VERIFICATION.md, is exempt under 2.5.8's inline
exception and is deliberately left at the text's line height.

The rule is enumerated rather than listed: every <a> that is the only thing
in its <p> must wear .link-standalone, so the next standalone link is covered
without anyone remembering this file.

Run with: pytest tests/test_standalone_link_target.py -v
"""
import re

import pytest

from src.pipeline.template_parts import JOINED_TEMPLATE  # noqa: E402

TEMPLATE = JOINED_TEMPLATE
STANDALONE = re.compile(r'<p\b[^>]*>\s*(<a\b[^>]*>)[^<]*</a>\s*</p>')


@pytest.fixture(scope='module')
def source():
    src = TEMPLATE.read_text(encoding='utf-8')
    return re.sub(r'<!--.*?-->', '', src, flags=re.S)


def test_the_scan_finds_the_standalone_links(source):
    """Vacuity: the five that prompted this must be found, or the rule
    below is checking nothing."""
    assert len(STANDALONE.findall(source)) >= 5


def test_every_standalone_link_wears_the_target_class(source):
    bare = [a for a in STANDALONE.findall(source)
            if 'link-standalone' not in (re.search(r'class="([^"]*)"', a) or [None, ''])[1].split()]
    assert not bare, f'standalone links without the 24px target: {bare}'


def test_the_class_gives_a_24px_target(source):
    styles = ''.join(re.findall(r'<style[^>]*>(.*?)</style>', source, re.S))
    rule = re.search(r'\.link-standalone\{([^}]*)\}', styles)
    assert rule, '.link-standalone has no rule'
    m = re.search(r'min-height\s*:\s*(\d+)px', rule.group(1))
    assert m and int(m.group(1)) >= 24, f'.link-standalone is {rule.group(1)!r}'
    # min-height does nothing on an inline box; the class must change that.
    assert re.search(r'display\s*:\s*inline-(flex|block)', rule.group(1))


def test_a_link_inside_a_sentence_is_left_alone(source):
    """The inline exception, kept on purpose: the VERIFICATION.md link sits
    mid-sentence, and a 24px box there would push its lines apart."""
    m = re.search(r'<a\b[^>]*>VERIFICATION\.md</a>', source)
    assert m, 'the in-sentence VERIFICATION.md link is gone -- re-anchor this guard'
    assert 'link-standalone' not in m.group(0)
