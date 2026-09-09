"""The dashboard has to be readable by a twelve-year-old.

That is the governing constraint for Stage 7.5, from the user directly, and
without a guard it reverts the first time anyone writes new copy -- the same
reasoning as every other guard in this repo.

WHAT THIS CHECKS, AND WHAT IT DOES NOT

It checks VOCABULARY: a list of statistics terms that are banned on the pages a
casual reader uses and allowed on the three that exist to be technical. It does
NOT check whether a sentence is short, whether a paragraph earns its length, or
whether an explanation is any good. A page can pass this and still read badly.
Do not treat a green run as "the writing is fine".

WHY IT READS THE JAVASCRIPT TOO

Most reader-facing copy on this dashboard is not in the page markup -- it is in
template literals inside render functions. A markup-only scan called the Week
Board and Season Accuracy "clean" while Season Accuracy was rendering "Brier
decomposition", "reliability - resolution + uncertainty (Murphy, 1973)" and
"95% Wilson interval" into the page. That is the copy this stage exists to fix,
and a guard that could not see it would have been decoration.

So each markup-bearing template literal is attributed to the function that
contains it, and RENDERERS maps those functions to pages. A render function
missing from that map fails the test rather than escaping the guard: the same
enumerate-don't-assert rule the workflow churn guard uses.

THE ALLOWLIST SHRINKS

KNOWN_JARGON records what is on the pages today. Each rewrite deletes entries.
The test also fails on an allowlist entry that is ALREADY clean, so the list
cannot quietly rot into a list of things that were fixed years ago. When it is
empty, the content half of Stage 7.5 is done.
"""

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = REPO_ROOT / 'src' / 'dashboard_template.html'


# Statistics vocabulary. Terms a reader would have to look up, not terms that
# merely sound technical -- "spread" and "net rating" stay, because the page
# explains them and a football fan already uses them.
JARGON = [
    'log loss', 'log-loss', 'brier', 'calibration', 'calibrated',
    'miscalibration', 'opponent-adjusted', 'shrinkage', 'bootstrap',
    'confidence interval', 'wilson interval', 'auc', 'epa',
    'ridge regression', 'fixed-effects', 'logistic', 'coefficient',
    'residual', 'ensemble', 'half-life', 'backtest', 'held-out',
    'resolution + uncertainty', 'reliability diagram',
]

# The three pages that exist to be technical. A reader arrives at these having
# chosen to; the vocabulary is the point.
# 'compare', 'datasources' and 'glossary' were pages of their own until they
# became parts of Methodology; their vocabulary now counts under 'method'.
TECHNICAL_PAGES = {'method', 'modellab', 'changelog', 'reliability'}

# Every render function that emits markup, and the page it emits it onto.
# Deliberately exhaustive: an unmapped function fails the test below rather
# than silently escaping the scan.
RENDERERS = {
    'renderRatings': 'ratings',
    'renderGames': 'board',
    'renderWeekGlance': 'board',
    'pickBadge': 'board',
    'lineFor': 'board',
    'whyRow': 'board',
    'populateWeekSelect': 'board',
    'renderPicksGrid': 'picks',
    'renderPicksStreak': 'picks',
    'trackRecordHtml': 'picks',
    'showUndoToast': 'picks',
    'renderAccuracy': 'accuracy',
    'buildCalibrationChart': 'accuracy',
    # Added when the trend chart gained a not-enough-data message. It used to
    # return '' in that case and so rendered no prose at all; the moment it
    # started explaining itself in words, its copy became reader-facing and
    # this guard caught that on the same change that introduced it.
    'buildCumulativeTrendChart': 'accuracy',
    'renderTeamDive': 'teamdive',
    'renderTeamGames': 'teamdive',
    # Model Lab: its reliability diagram is a technical chart on a technical
    # page. Verified by where the container lives (`#reliability-diagram`
    # sits inside `id="page-modellab"`), not by the function's name.
    'buildReliabilityDiagram': 'modellab',
    'seriesLegend': 'modellab',
    'renderChangelog': 'changelog',
    # "Checking the AI's work". A page ABOUT the verifier, so the vocabulary
    # of verification belongs on it -- but it is written for the same reader
    # as the rest, so it is scoped, not exempt.
    'renderAgentLog': 'reliability',
}


# Measured, not guessed: produced by running this scan against the pages as
# they stand. Each entry is (page, term). Delete entries as the rewrites land.
# The content half of Stage 7.5 is done when this is empty.
# EMPTY, and that is the point. It held NINE entries when this guard was
# written. Eight were real jargon and were rewritten:
#
#   Power Ratings   one sentence carrying four terms -- "Opponent-adjusted
#                   EPA/play ratings ... fit via ridge regression ... 16-game
#                   recency half-life" -- now says what the number means and
#                   sends the reader to Methodology for how it is computed.
#   Season Accuracy "Live Calibration" and "Calibration" are now "Are these
#                   percentages honest?", which is the question the section
#                   actually answers.
#   My Picks        "backtested games" -> "past games".
#   Team Deep-Dive  "real backtested history" -> "real history, replayed as if
#                   we had been predicting it at the time".
#
# The ninth, ('board', 'epa'), was never real jargon. The Week Board's only
# match was 'epa' inside "s-epa-rately", invented by the old substring
# matcher. It left the list because the matcher was fixed, NOT because any
# copy changed -- and the first writeup of this work counted the remaining
# eight as if that had always been the total, which Booth caught on PR #44.
# Two different causes moved this number in one change; a count that does not
# say which is which misattributes the work.
#
# An entry added here is a debt, not a decision. Anything that goes in should
# come out again in the same stage.
KNOWN_JARGON = set()


# ---------------------------------------------------------------------------

def _source():
    return TEMPLATE.read_text(encoding='utf-8')


def _visible(html):
    html = re.sub(r'<!--.*?-->', ' ', html, flags=re.S)
    html = re.sub(r'<(script|style)\b.*?</\1>', ' ', html, flags=re.S | re.I)
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html))


def _scripts(src):
    js = '\n'.join(re.findall(r'<script\b[^>]*>(.*?)</script>', src, re.S))
    js = re.sub(r'/\*.*?\*/', ' ', js, flags=re.S)
    return re.sub(r'(?m)^\s*//.*$', ' ', js)


_FN = re.compile(r'function\s+([A-Za-z_$][\w$]*)\s*\(')


def _js_copy_by_function(src):
    """{function name: the prose it renders}.

    Only template literals containing markup count. A literal with no tags in
    it is a class name, a selector or a number format -- not something a reader
    reads. `${...}` interpolations are dropped: they are expressions, and the
    identifiers inside them (`calibration.models`) are not copy.
    """
    js = _scripts(src)
    out = {}
    for m in re.finditer(r'`([^`]*)`', js, re.S):
        lit = m.group(1)
        if '<' not in lit or '>' not in lit:
            continue
        fns = _FN.findall(js[:m.start()])
        owner = fns[-1] if fns else '<top-level>'
        lit = re.sub(r'\$\{[^{}]*\}', ' ', lit)
        out.setdefault(owner, []).append(_visible(lit))
    return {k: ' '.join(v) for k, v in out.items()}


def _copy_by_page():
    """{page id: everything a reader sees on it}, markup and rendered alike."""
    src = _source()
    pages = {}
    for m in re.finditer(r'<section class="page[^"]*" id="page-([a-z0-9_-]+)".*?</section>',
                         src, re.S):
        pages[m.group(1)] = _visible(m.group(0))
    for fn, copy in _js_copy_by_function(src).items():
        page = RENDERERS.get(fn)
        if page:
            pages[page] = pages.get(page, '') + ' ' + copy
    return pages


def _headings_by_page():
    """{page id: [h3 text, ...]} from the markup AND from the render functions.

    Both halves matter, and the JS half is the one that caught the real bug:
    the two duplicate headings on Season Accuracy were both produced by render
    functions, so a scan of the page's `<section>` markup found neither. The
    first version of the guard below did exactly that and would have passed
    over the defect it is named for.
    """
    src = _source()
    out = {}
    for m in re.finditer(r'<section class="page[^"]*" id="page-([a-z0-9_-]+)".*?</section>',
                         src, re.S):
        out[m.group(1)] = re.findall(r'<h3[^>]*>(.*?)</h3>', m.group(0), re.S)
    js = _scripts(src)
    for fn_m in re.finditer(r'`([^`]*)`', js, re.S):
        lit = fn_m.group(1)
        if '<h3' not in lit:
            continue
        fns = _FN.findall(js[:fn_m.start()])
        page = RENDERERS.get(fns[-1] if fns else '')
        if page:
            out.setdefault(page, []).extend(re.findall(r'<h3[^>]*>(.*?)</h3>', lit, re.S))
    return {p: [re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', h)).strip() for h in hs]
            for p, hs in out.items()}


def _mentions(copy, term):
    """Anchored at a word START, with any suffix allowed.

    Two failures, one on each side, both found by running it:

    Plain substring matching flagged 'epa' inside 's-epa-rately' and sent a
    rewrite at a sentence that was already fine. A guard whose false positives
    cost edits to correct copy spends the very thing it exists to protect.

    Closing both ends with \\b then hid 'backtested', because the term is
    'backtest' and the word carries a suffix. That is worse: the guard went
    quiet on jargon that was actually on the page, and the allowlist would
    have recorded the work as done.

    So: a word may not START inside another word, and may end however English
    ends it. 'epa' does not match 'separately'; 'backtest' matches
    'backtested', 'backtests' and 'backtesting'.
    """
    return re.search(r'\b%s\w*' % re.escape(term), copy, re.I) is not None


def _violations():
    found = set()
    for page, copy in _copy_by_page().items():
        if page in TECHNICAL_PAGES:
            continue
        for term in JARGON:
            if _mentions(copy, term):
                found.add((page, term))
    return found


# ---------------------------------------------------------------------------

def test_every_render_function_is_attributed_to_a_page():
    """A render function missing from RENDERERS is copy this guard cannot see.
    Enumerate rather than assume: the alternative is a new function quietly
    rendering 'Brier decomposition' onto the Week Board with the suite green."""
    rendered = set(_js_copy_by_function(_source()))
    unmapped = sorted(rendered - set(RENDERERS) - {'<top-level>'})
    assert not unmapped, (
        f"these functions render markup but are not in RENDERERS, so their copy "
        f"is unchecked: {unmapped}. Add each one with the page it renders onto")


def test_the_scan_actually_sees_the_javascript_copy():
    """The whole reason this file is more than a markup grep. If the literal
    matcher drifts, every check below passes over an empty string."""
    copy = _js_copy_by_function(_source())
    assert len(copy) >= 10, f"only {len(copy)} render functions found; the matcher has drifted"
    total = sum(len(v) for v in copy.values())
    assert total > 3000, (
        f"only {total} characters of rendered copy found; most of this "
        f"dashboard's prose is in template literals and it is not being read")


def test_no_new_jargon_on_the_pages_a_casual_reader_uses():
    """The guard itself. New entries are failures; the known ones live in
    KNOWN_JARGON and shrink as the rewrites land."""
    new = _violations() - KNOWN_JARGON
    assert not new, (
        "statistics vocabulary added to a page meant for a casual reader:\n  "
        + "\n  ".join(f"{page}: {term!r}" for page, term in sorted(new))
        + "\n\nThese pages are for someone who wants to know who to pick. Say it "
          "in football terms, or move the explanation to Methodology or Model Lab.")


def test_the_allowlist_does_not_keep_entries_that_are_already_clean():
    """Makes the list SHRINK rather than rot. An entry for text somebody has
    already rewritten turns the allowlist into a list of solved problems, and
    the next reader cannot tell what is left to do."""
    stale = KNOWN_JARGON - _violations()
    assert not stale, (
        "KNOWN_JARGON lists jargon that is no longer on the page:\n  "
        + "\n  ".join(f"{page}: {term!r}" for page, term in sorted(stale))
        + "\n\nDelete these entries -- the work is done.")


def test_no_page_repeats_a_heading():
    """Rewriting two sections with the same question left Season Accuracy with
    two identical `<h3>Are these percentages honest?</h3>` headings. To a
    reader that says the page repeats itself; to anyone scanning for a section
    it means the heading no longer identifies one.

    Cheap to check and easy to reintroduce, because plain-English rewriting
    naturally converges on the same short question for related sections.
    """
    for page, heads in _headings_by_page().items():
        dupes = {h for h in heads if heads.count(h) > 1}
        assert not dupes, f"page-{page} uses the same h3 more than once: {sorted(dupes)}"


def test_the_technical_pages_are_still_allowed_to_be_technical():
    """The other side of the rule. If this ever fails, the ban has been applied
    everywhere and Methodology has been flattened into baby talk, which is not
    the goal -- the goal is that a reader chooses when to meet the vocabulary."""
    pages = _copy_by_page()
    technical_copy = ' '.join(pages.get(p, '') for p in TECHNICAL_PAGES).lower()
    assert any(t in technical_copy for t in JARGON), (
        "no statistics vocabulary anywhere on Methodology, Model Lab or the "
        "glossary -- the technical explanations have gone missing")


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
