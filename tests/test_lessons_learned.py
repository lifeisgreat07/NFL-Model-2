"""docs/lessons-learned.md and docs/architecture.md: every pointer still points.

Each lesson ends with where it came from: a case study, a repository path,
or an entry in `docs/traps.md` or `CLAUDE.md` named by a phrase from its
title. Those are the lesson's evidence, and a pointer that has gone dead turns
a sourced lesson into an assertion. A renamed trap or a moved file is exactly
the kind of change nothing else would notice here.

Each phrase is looked up in the document its citation names, not in either:
since the Stage 29 split the traps and the rules live in different files, and
a phrase that moved between them without its citation moving is a pointer to
the wrong place.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOC = REPO / 'docs' / 'lessons-learned.md'
ARCH = REPO / 'docs' / 'architecture.md'
CITED = {'CLAUDE.md': REPO / 'CLAUDE.md', 'docs/traps.md': REPO / 'docs' / 'traps.md'}
TEMPLATE = REPO / 'src' / 'pipeline' / 'dashboard_template.html'
LINK = 'https://github.com/lifeisgreat07/NFL-Model-2/blob/main/docs/lessons-learned.md'


def links(text):
    """Relative markdown link targets, resolved against docs/."""
    return [t for t in re.findall(r'\]\(([^)#]+)\)', text) if not t.startswith('http')]


def paths(text):
    """Backticked strings shaped like repository paths."""
    return [p for p in re.findall(r'`([\w./-]+)`', text) if '/' in p or p.endswith('.md')]


def cited_phrases(text):
    """(document, phrase) for each quoted phrase after a cited document.

    A citation runs from the backticked document name to the next backtick or
    the closing `*`, so `CLAUDE.md`, "a"; `docs/traps.md`, "b" is two
    citations in one line, each checked against its own file.
    """
    found = []
    names = '|'.join(re.escape(n) for n in CITED)
    for doc, tail in re.findall(r'`(' + names + r')`,([^*`]*)', text, flags=re.S):
        found += [(doc, p) for p in re.findall(r'"([^"]+)"', tail)]
    return found


def trap_phrases(text):
    """The phrases alone, for the vacuity guard."""
    return [p for _, p in cited_phrases(text)]


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


def test_every_trap_it_cites_is_still_where_it_says():
    text = DOC.read_text(encoding='utf-8')
    missing = []
    for doc, path in CITED.items():
        phrases = [p for d, p in cited_phrases(text) if d == doc]
        missing += [f"{doc}: {p}" for p in
                    missing_phrases(phrases, path.read_text(encoding='utf-8'))]
    assert not missing, f"these cited entries are not in the document they cite: {missing}"


def test_both_cited_documents_are_actually_cited():
    """Vacuity guard for the split: if every citation pointed at one file, the
    lookup in the other would run over nothing and pass."""
    docs = {d for d, _ in cited_phrases(DOC.read_text(encoding='utf-8'))}
    assert docs == set(CITED), f"lessons-learned.md cites only {sorted(docs)}"


def test_the_trap_check_notices_a_renamed_entry():
    """Synthetic, so the failing branch is reachable while every real phrase matches."""
    assert missing_phrases(['a guard that lies'], 'A GUARD THAT\n  LIES about itself') == []
    assert missing_phrases(['a guard that lies'], 'a guard that tells the truth') == ['a guard that lies']


def test_the_page_links_to_it():
    page = re.sub(r'<!--.*?-->', '', TEMPLATE.read_text(encoding='utf-8'), flags=re.S)
    assert f'href="{LINK}"' in page, "Checking the AI's work no longer links to lessons-learned.md"


# --- docs/architecture.md: the table names the file behind every box -------

def test_every_path_in_the_architecture_table_exists():
    text = ARCH.read_text(encoding='utf-8')
    found = paths(text)
    assert len(found) >= 10, "the path matcher found almost nothing in architecture.md"
    dead = [p for p in found if not (REPO / p).exists()]
    assert not dead, f"architecture.md names paths that do not exist: {dead}"


def test_every_workflow_is_on_the_architecture_page_or_deliberately_not():
    """A new workflow is a new box. The regression and backtest workflows are
    manual and described under the boxes they serve, so they are listed here
    as known omissions rather than silently skipped."""
    text = ARCH.read_text(encoding='utf-8')
    omitted = {'booth-regression.yml', 'run-backtest.yml'}
    for wf in sorted((REPO / '.github' / 'workflows').glob('*.yml')):
        if wf.name in omitted:
            continue
        assert f'.github/workflows/{wf.name}' in text, f"{wf.name} is not on the architecture page"
