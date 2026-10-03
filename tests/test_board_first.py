"""The Week Board is the page a visitor lands on, and first in both navs.

Stage 13 (CLAUDE.md). Until now the page opened on Power Ratings, a table of
32 teams, and the games this week -- what most visitors come for -- were one
tap away. The Week Board now ships as the active section, its button is first
and active in the sidebar and in the phone's bottom nav, and the bottom nav
reads Board, Ratings, Picks, Accuracy, More.

Read from the template, because which section ships active is decided by the
markup alone: nothing at load calls setActivePage() except a share link,
which opens My Picks.

Run with: pytest tests/test_board_first.py -v
"""
import re

import pytest

from src.pipeline.template_parts import JOINED_TEMPLATE  # noqa: E402

TEMPLATE = JOINED_TEMPLATE


@pytest.fixture(scope='module')
def src():
    return TEMPLATE.read_text(encoding='utf-8')


def nav_buttons(src, cls):
    """(page, is_active) for each button of one nav, in document order."""
    return [(page, 'active' in classes.split())
            for classes, page in re.findall(
                rf'<button class="({cls}(?: [a-z-]+)*)" data-page="([a-z0-9_-]+)"', src)]


def test_the_week_board_is_the_only_section_that_ships_active(src):
    sections = re.findall(r'<section class="page( active)?" id="page-([a-z0-9_-]+)"', src)
    assert sections, 'no page sections found -- this matcher has drifted'
    active = [page for flag, page in sections if flag]
    assert active == ['board'], f'the sections that ship active are {active}, not just the Week Board'


def test_the_board_is_first_and_active_in_the_sidebar(src):
    side = nav_buttons(src, 'nav-btn')
    assert side, 'no sidebar buttons found -- this matcher has drifted'
    assert side[0] == ('board', True), f'the sidebar starts with {side[0]}'
    assert [p for p, on in side if on] == ['board'], 'another sidebar button also ships active'
    assert [p for p, _ in side[:3]] == ['board', 'ratings', 'teamdive'], (
        'the "This Week" group should read Week Board, Power Ratings, Team Deep-Dive')


def test_the_bottom_nav_reads_board_ratings_picks_accuracy_more(src):
    bottom = nav_buttons(src, 'bnav-btn')
    assert [p for p, _ in bottom] == ['board', 'ratings', 'picks', 'accuracy'], (
        f'the bottom nav reads {[p for p, _ in bottom]}')
    assert bottom[0][1] and not any(on for _, on in bottom[1:]), 'the Board tab is not the one that ships active'
    tabs = re.search(r'data-page="accuracy">.*?\n(\s*<button class="bnav-btn" id="bnav-more-btn")', src, re.S)
    assert tabs, 'More is no longer the tab straight after Accuracy'


def test_nothing_at_load_switches_away_from_the_board(src):
    """The only call outside the click handler is the share-link one."""
    calls = re.findall(r"setActivePage\('([a-z]+)'\)", src)
    assert calls == ['picks'], f'setActivePage is called with fixed pages {calls}'


def test_the_no_script_comments_name_the_page_that_ships_active(src):
    assert 'page-ratings is active' not in src and '#page-ratings, the one the' not in src, (
        'a comment still says Power Ratings is the page a no-script reader lands on')
    assert '#page-board, the one the' in src
