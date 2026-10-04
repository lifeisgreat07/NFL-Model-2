"""A team row and a week row link to their own pages (Stage 26 item 5, from
the 2026-09-28 audit).

Hash routes (Stage 21 of the UX plan) gave every team and every saved week an
address, and nothing on the page linked to one: Power Ratings listed 32 teams
and Season Accuracy listed the graded weeks, and to see one you went to the
nav and picked it again from a select. Each team's name in Power Ratings now
links to #team/<abbr>, and each graded week in Season Accuracy to
#board/<week key> when the page has that week's board. The links go through
routeHash(), the one function that writes addresses, and the existing
popstate handler opens them, so Back returns to the table. Checked in a
browser for the PR; held here by source, as the suite has no browser.

Run with: pytest tests/test_row_links.py -v
"""
import re
from pathlib import Path

from src.pipeline.template_parts import read_template

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = read_template()


def test_each_team_name_links_to_its_deep_dive():
    row = re.search(r"body\.innerHTML = visible\.map\(\(t\)=>\{.*?\n  \}\)\.join\(''\);", TEMPLATE, re.S)
    assert row, 'the Power Ratings row template is not findable -- re-anchor this test'
    assert ('<a class="row-link" href="${routeHash({page:\'teamdive\', team:t.team})}">'
            '<img class="team-logo"') in row.group(0)
    assert '<span class="team-full">${t.name}</span></a>' in row.group(0), (
        'the link does not cover the name, or wraps the rank-move arrow too')


def test_each_graded_week_links_to_its_board_only_when_the_board_exists():
    body = re.search(r'function renderAccuracy\(\)\{.*?\n\}', TEMPLATE, re.S).group(0)
    assert "const key = `${w.season}_week${w.week}`" in body
    assert 'return weekKeysSorted.includes(key)' in body, 'a week with no board would link to one anyway'
    assert "href=\"${routeHash({page:'board', week:key})}\"" in body
    assert '<td>${weekCell(w)}</td>' in body


def test_the_week_key_is_the_one_the_saved_weeks_use():
    from src.pipeline import generate_dashboard as gd
    assert gd.parse_week_stem('2026_week3') == (2026, 3), (
        'the saved-week key format changed, so the week links point at nothing')


def test_the_links_keep_the_tables_look_and_the_target_size():
    rule = re.search(r'\.row-link\{([^}]*)\}', TEMPLATE)
    assert rule, 'no .row-link rule'
    css = rule.group(1)
    assert 'color:inherit' in css and 'text-decoration:none' in css
    assert 'min-height:24px' in css
