"""What's Changed -- the Roadmap page folded into the Changelog page.

WHY THESE GUARDS EXIST, AND WHY ONE OF THEM IS UNUSUAL

The written plan for this merge said the Roadmap's "Done" list duplicated the
Changelog and could simply be deleted. It did not. The Changelog is seven
*model* versions generated from `config.VERSION_HISTORY`; the Done list was
sixteen mostly-*product* milestones -- the picks log, the calibration table,
the deep-dive page, the nflreadpy migration -- and only about three genuinely
overlapped. Deleting it would have destroyed the only record of most of the
work, quietly, with every test still green, because nothing tested that the
content existed.

So the unusual guard is `test_the_build_record_survived_the_merge`: it asserts
a floor on how much of that record is on the page. A test that only checked
"the merged page renders" would have passed just as happily over an empty one.
"""

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / 'src'))

import config  # noqa: E402

TEMPLATE = REPO_ROOT / 'src' / 'dashboard_template.html'


def _page():
    return TEMPLATE.read_text(encoding='utf-8')


def _visible_text():
    """What a reader actually sees.

    Comments have to come out FIRST, and by their own delimiters. Stripping
    tags with `<[^>]+>` does not remove an HTML comment -- the character class
    stops at the first '>' inside it and leaves the rest as text. The first
    version of the reference check below failed on the code comment that
    explains this very merge, which reads like the page pointing at a deleted
    tab when it is a note to the next developer. Scripts and styles go too:
    a CSS rule name is not prose.
    """
    text = re.sub(r'<!--.*?-->', ' ', _page(), flags=re.S)
    text = re.sub(r'<(script|style)\b.*?</\1>', ' ', text, flags=re.S | re.I)
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', text))


def _live_markup():
    """The markup a browser will actually build the page from.

    Comments stripped, because a scan of the raw file counts commented-out
    content as present. Mutation testing found this: wrapping the entire
    "what got built" grid in `<!--` left every guard below green while the
    page rendered an empty section. A test that reads the file rather than
    the document is checking that the text exists, not that the page does.
    """
    return re.sub(r'<!--.*?-->', ' ', _page(), flags=re.S)


def _cards():
    """(pill class, status, title) for every milestone card on the page."""
    return re.findall(
        r'<div class="roadmap-card"><div class="roadmap-status ([a-z-]+)">(.*?)</div><h4>(.*?)</h4>',
        _live_markup(), re.S)


def _card_titles():
    return {title.strip() for _, _, title in _cards()}


# ---------------------------------------------------------------------------
# The page that went away
# ---------------------------------------------------------------------------

def test_the_roadmap_page_is_gone():
    page = _page()
    assert 'id="page-roadmap"' not in page, "the Roadmap section is still in the markup"
    assert 'data-page="roadmap"' not in page, "a nav button still points at the deleted page"


def test_every_nav_on_the_page_agrees_on_which_pages_exist():
    """This dashboard has TWO navigations -- the desktop sidebar and the mobile
    bottom-nav "more" sheet -- and deleting the Roadmap from the sidebar left
    the mobile one pointing at nothing. On a phone the tab was still there and
    opened a blank screen. Nothing else would have caught it: the desktop
    render looks perfect.

    Stated as an equality rather than as "no roadmap button", so the next page
    deleted from one nav and not the other fails here too.
    """
    page = _page()
    targets = set(re.findall(r'data-page="([a-z0-9_-]+)"', page))
    # `class="page active"` on the default section, so match the class list
    # loosely. Pinning it to `class="page"` silently drops Power Ratings from
    # the known-pages set and reports the site's own home tab as broken.
    sections = set(re.findall(r'<section class="page[^"]*" id="page-([a-z0-9_-]+)"', page))

    assert targets, "no navigation controls found at all; this matcher has drifted"
    assert sections, "no pages found at all; this matcher has drifted"
    assert targets <= sections, (
        f"navigation controls point at pages that do not exist: "
        f"{sorted(targets - sections)}. On the desktop sidebar that is a dead "
        f"button; in the mobile bottom-nav sheet it is a tab that opens a "
        f"blank screen, which is where this was actually found")


def test_nothing_sends_the_reader_to_a_page_that_no_longer_exists():
    """The Methodology page carried 'see Roadmap and Model Lab'. A deletion
    that leaves a sentence pointing at a vanished tab is worse than the
    duplication it was meant to fix -- the reader goes looking and finds
    nothing, and concludes the site is broken rather than that a page moved.
    """
    visible = _visible_text()
    for phrase in ('see Roadmap', 'the Roadmap page', 'on the Roadmap', 'Roadmap tab'):
        assert phrase not in visible, (
            f"visible text still refers the reader to {phrase!r}, but that page "
            f"was deleted when it was folded into What's Changed")


# ---------------------------------------------------------------------------
# The record the merge existed to preserve
# ---------------------------------------------------------------------------

def test_the_build_record_survived_the_merge():
    """The floor. Sixteen milestones were folded in; if that count collapses,
    somebody has deleted the history rather than moved it -- which is exactly
    what the original plan would have done, and exactly what no existing test
    would have noticed."""
    cards = _cards()
    assert len(cards) >= 23, (
        f"only {len(cards)} milestone cards on the page; 23 were folded in "
        f"(16 built, 7 tried-and-not-kept). Work has been deleted, not moved")


@pytest.mark.parametrize('title', [
    'My Picks Log',
    'Season Accuracy + Calibration',
    'Confidence Ranking + Why Breakdown',
    'Team Deep-Dive Page',
    'Automated Weekly Routine',
    'Migrated to nflreadpy',
])
def test_the_milestones_the_changelog_never_covered_are_still_named(title):
    """Each of these is a real piece of built work with NO corresponding entry
    in config.VERSION_HISTORY -- the changelog tracks model versions, and these
    are product. They are named individually because they are the specific
    things the 'it's all duplicated anyway' reading got wrong.

    Checked against the CARD TITLES, not against the file. Several of these
    phrases also appear as a nav label or a page heading -- "My Picks Log" is
    a tab of its own -- so `title in page` stayed true with the milestone card
    renamed out of existence. Mutation testing caught that: the substring was
    matching a completely different element.
    """
    assert title in _card_titles(), (
        f"{title!r} is no longer one of the milestone cards, so this piece of "
        f"built work is recorded nowhere on the site")


def test_those_milestones_really_are_absent_from_the_generated_changelog():
    """Guards the REASON for the test above. If VERSION_HISTORY ever grows to
    cover this work properly, the hand-written cards become the duplication
    the original plan wrongly believed they already were -- and this test
    turning red is the signal to go and delete them for real."""
    changelog = ' '.join(e['headline'] + ' ' + e['detail']
                         for e in config.VERSION_HISTORY).lower()
    for phrase in ('picks log', 'calibration', 'deep-dive', 'nflreadpy'):
        assert phrase not in changelog, (
            f"config.VERSION_HISTORY now mentions {phrase!r}. The generated "
            f"changelog has started covering product work, so the hand-written "
            f"'What got built' cards may genuinely be duplication now -- "
            f"re-read them against it rather than keeping both")


# ---------------------------------------------------------------------------
# The pill colour, which was asserting the opposite of the text on it
# ---------------------------------------------------------------------------

def test_a_rejected_idea_does_not_wear_the_success_colour():
    """`.status-done` is the green pill. Every card on the old Roadmap used it
    -- including six that read "Tested — Rejected", "Removed", and "Decided
    Against". A green badge saying REJECTED is the page contradicting itself,
    and the colour is the part most readers actually parse.

    Stated over the markup, so a card added later is covered automatically.
    """
    for cls, status, title in _cards():
        shipped = status.strip() in ('Built', 'Adopted')
        if cls == 'status-done':
            assert shipped, (
                f"{title.strip()!r} is labelled {status.strip()!r} but wears the "
                f"success-green pill, so the page says it shipped and says it "
                f"did not at the same time")
        else:
            assert not shipped, (
                f"{title.strip()!r} shipped but wears the neutral pill, so real "
                f"work reads as an abandoned experiment")


def test_the_neutral_pill_is_actually_a_different_colour():
    """The pairing above is satisfied by two classes that resolve to the same
    paint. Both rules have to exist and name different colour variables."""
    page = _page()
    done = re.search(r'\.status-done\{([^}]*)\}', page)
    planned = re.search(r'\.status-planned\{([^}]*)\}', page)
    assert done and planned, "one of the status pill rules is missing"
    assert done.group(1) != planned.group(1), (
        "the shipped and not-kept pills resolve to identical styling, so "
        "separating the classes changed nothing a reader can see")


def test_both_kinds_of_card_are_actually_on_the_page():
    """The pairing test passes vacuously over a page with only one kind. This
    is the same lesson the Playoff Odds deletion taught: a rule checked by
    only one branch is not being checked."""
    classes = {cls for cls, _, _ in _cards()}
    assert 'status-done' in classes and 'status-planned' in classes, (
        f"only {classes} present -- the pill rule above is testing one side")


# ---------------------------------------------------------------------------
# Shape of the merged page
# ---------------------------------------------------------------------------

def test_the_page_has_its_three_parts_in_order():
    page = _page()
    section = re.search(r'<section class="page" id="page-changelog".*?</section>', page, re.S)
    assert section, "the merged page is gone"
    heads = re.findall(r'<h3 class="section-title">(.*?)</h3>', section.group(0))
    assert heads == ['Model versions', 'What got built', 'What we tried that did not work'], (
        f"the merged page's sections are {heads}; the generated versions come "
        f"first, then what shipped, then what did not")


def test_the_generated_version_list_is_still_generated():
    """The merge must not have turned a generated section into hand-written
    prose. `#changelog-content` is filled from config.VERSION_HISTORY."""
    page = _page()
    assert '<div id="changelog-content"></div>' in page, (
        "the version list is no longer an empty container filled from "
        "config.VERSION_HISTORY -- it may have been inlined by hand")


def test_the_tab_is_named_in_plain_english():
    """'Changelog' is developer vocabulary on a dashboard meant to be readable
    by a twelve-year-old."""
    page = _page()
    assert 'What&#39;s Changed</button>' in page, "the nav button lost its plain-English label"
    assert '<h2>Changelog</h2>' not in page, "the page heading is still the jargon one"


def test_the_built_page_carries_the_merged_content():
    built = REPO_ROOT / 'index.html'
    if not built.exists():
        pytest.skip('index.html has not been generated in this checkout')
    page = built.read_text(encoding='utf-8')
    assert 'id="page-roadmap"' not in page, "the built page still ships the deleted section"
    assert 'What we tried that did not work' in page, (
        "the built page is stale -- regenerate it")


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
