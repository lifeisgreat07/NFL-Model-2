"""docs/lessons-learned.md: every pointer in it still points at something.

Each lesson ends with where it came from: a case study, a repository path,
or a trap entry in CLAUDE.md named by a phrase from its title. Those are the
lesson's evidence, and a pointer that has gone dead turns a sourced lesson
into an assertion. A renamed trap or a moved file is exactly the kind of
change nothing else would notice here.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOC = REPO / 'docs' / 'lessons-learned.md'
CLAUDE = REPO / 'CLAUDE.md'
TEMPLATE = REPO / 'src' / 'dashboard_template.html'
LINK = 'https://github.com/lifeisgreat07/NFL-Model-2/blob/main/docs/lessons-learned.md'


def links(text):
    """Relative markdown link targets, resolved against docs/."""
    return [t for t in re.findall(r'\]\(([^)#]+)\)', text) if not t.startswith('http')]


def paths(text):
    """Backticked strings shaped like repository paths."""
    return [p for p in re.findall(r'`([\w./-]+)`', text) if '/' in p or p.endswith('.md')]


def trap_phrases(text):
    """The quoted phrase after each `CLAUDE.md`, naming a trap entry."""
    found = []
    for line in re.findall(r'`CLAUDE\.md`,([^*]*)', text, flags=re.S):
        found += re.findall(r'"([^"]+)"', line)
    return found


def missing_phrases(phrases, claude_text):
    flat = ' '.join(claude_text.split()).lower()
    return [p for p in phrases if ' '.join(p.split()).lower() not in flat]


def test_the_matchers_find_what_the_document_holds():
    """Vacuity guard: an empty list below would make every test pass."""
    text = DOC.read_text(encoding='utf-8')
    assert len(links(text)) >= 3
    assert len(paths(text)) >= 3
    assert len(trap_phrases(text)) >= 5


def test_every_link_resolves():
    text = DOC.read_text(encoding='utf-8')
    dead = [t for t in links(text) if not (DOC.parent / t).exists()]
    assert not dead, f"lessons-learned.md links to files that do not exist: {dead}"


def test_every_path_exists():
    text = DOC.read_text(encoding='utf-8')
    dead = [p for p in paths(text) if not (REPO / p).exists()]
    assert not dead, f"lessons-learned.md names paths that do not exist: {dead}"


def test_every_trap_it_cites_is_still_in_claude_md():
    text = DOC.read_text(encoding='utf-8')
    missing = missing_phrases(trap_phrases(text), CLAUDE.read_text(encoding='utf-8'))
    assert not missing, f"CLAUDE.md no longer has the trap entries these name: {missing}"


def test_the_trap_check_notices_a_renamed_entry():
    """Synthetic, so the failing branch is reachable while every real phrase matches."""
    assert missing_phrases(['a guard that lies'], 'A GUARD THAT\n  LIES about itself') == []
    assert missing_phrases(['a guard that lies'], 'a guard that tells the truth') == ['a guard that lies']


def test_the_page_links_to_it():
    page = re.sub(r'<!--.*?-->', '', TEMPLATE.read_text(encoding='utf-8'), flags=re.S)
    assert f'href="{LINK}"' in page, "Checking the AI's work no longer links to lessons-learned.md"
