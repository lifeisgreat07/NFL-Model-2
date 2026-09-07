"""Playoff Odds as a column on Power Ratings, not a page of its own.

The odds used to live on their own tab with their own bar chart. That bar was
a 0-100% magnitude anchored at the left edge sharing a class with two signed
bars, and the tab itself was one more thing to click for one number per team.
The number moved onto the Power Ratings table; the page and the bar went away.

Moving it created one non-obvious requirement, which most of this file exists
to hold in place: the value has to be JOINED ONTO THE TEAM OBJECT in Python.
The table sorts by reading `a[sortKey]` off a team, so odds living in a
separate browser-side lookup would render in the cell and silently refuse to
sort -- a column that looks finished and is half broken.
"""

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import generate_dashboard as gd  # noqa: E402

TEMPLATE = Path(__file__).resolve().parents[1] / 'src' / 'dashboard_template.html'


def _ratings(*teams):
    return [{'team': t, 'name': f'{t} Team', 'off': 0.1, 'def': -0.1, 'net': 0.2,
             'sos': None, 'games_played': 0} for t in teams]


# ---------------------------------------------------------------------------
# The join
# ---------------------------------------------------------------------------

def test_the_odds_land_on_the_team_object_where_the_sort_can_reach_them():
    rows = gd.build_teams_js(
        _ratings('BUF', 'KC'),
        {'teams': [{'team': 'BUF', 'playoff_pct': 67.5},
                   {'team': 'KC', 'playoff_pct': 52.9}]})
    assert {r['team']: r['playoff'] for r in rows} == {'BUF': 67.5, 'KC': 52.9}


def test_a_team_missing_from_the_simulation_gets_none_and_not_zero():
    """Zero is a real playoff chance -- a team mathematically eliminated has
    one. Defaulting an absent team to 0 would rank it last on merit and print
    '0.0%' as though the model had said so. None means the simulation never
    covered it, and the cell renders a dash."""
    rows = gd.build_teams_js(
        _ratings('BUF', 'CAR'), {'teams': [{'team': 'BUF', 'playoff_pct': 67.5}]})
    by_team = {r['team']: r['playoff'] for r in rows}
    assert by_team['CAR'] is None, "an unsimulated team was given a number"
    assert by_team['BUF'] == 67.5


def test_an_eliminated_team_keeps_its_real_zero():
    """The other side of the rule above: a genuine 0.0 must survive the join
    as 0.0, not be flattened into the same 'unknown' bucket as a missing team."""
    rows = gd.build_teams_js(_ratings('CAR'), {'teams': [{'team': 'CAR', 'playoff_pct': 0.0}]})
    assert rows[0]['playoff'] == 0.0
    assert rows[0]['playoff'] is not None


def test_no_odds_file_at_all_still_builds_every_team():
    """The odds are a weekly artefact; a fresh clone or a failed simulation
    leaves the file absent. The ratings table is not allowed to disappear
    with it."""
    for missing in (None, {}, {'teams': None}, {'teams': []}):
        rows = gd.build_teams_js(_ratings('BUF', 'KC'), missing)
        assert len(rows) == 2, f"lost teams when odds were {missing!r}"
        assert all(r['playoff'] is None for r in rows)


def test_the_join_does_not_invent_rows_for_teams_that_are_not_rated():
    """The odds file can name a team the ratings do not (a relocation, a
    stale artefact). The ratings are the spine; extra odds rows are dropped
    rather than appended as teams with no rating."""
    rows = gd.build_teams_js(
        _ratings('BUF'),
        {'teams': [{'team': 'BUF', 'playoff_pct': 67.5},
                   {'team': 'ZZZ', 'playoff_pct': 1.0}]})
    assert [r['team'] for r in rows] == ['BUF']


def test_a_nameless_row_in_the_odds_file_does_not_become_a_none_key():
    """A malformed row without a team would otherwise key the lookup under
    None, which is also what `odds.get()` returns for a miss -- so every
    unmatched team would inherit that row's percentage."""
    rows = gd.build_teams_js(
        _ratings('BUF'), {'teams': [{'playoff_pct': 99.9}, {'team': 'BUF', 'playoff_pct': 67.5}]})
    assert rows[0]['playoff'] == 67.5


# ---------------------------------------------------------------------------
# The '#' column, which the new sort made dishonest
# ---------------------------------------------------------------------------
#
# Adding a column people want to sort by exposed a rule that had been true only
# by accident. The rank was the row's position in the current sort, so sorting
# by anything other than net rating renumbered the league -- and the first
# click on Playoff Odds printed "#1 Cincinnati" beside a NEGATIVE net rating on
# a page called Power Ratings. The comment above that line already claimed the
# number was the team's "real league position", which it was only while the
# default sort was the only sort anyone used.


def _ranked(*pairs):
    return gd.build_teams_js(
        [{'team': t, 'name': f'{t} Team', 'off': 0.0, 'def': 0.0, 'net': n,
          'sos': None, 'games_played': 0} for t, n in pairs], None)


def test_rank_follows_the_net_rating_and_not_the_order_of_the_input():
    """The ratings file's own order is not a promise. If it ever arrives
    unsorted -- a different writer, a merge, a hand edit -- the ranks have to
    come out right anyway."""
    rows = _ranked(('CIN', -0.03), ('BUF', 0.14), ('GB', 0.10))
    assert {r['team']: r['rank'] for r in rows} == {'BUF': 1, 'GB': 2, 'CIN': 3}


def test_rank_is_a_number_on_the_team_and_not_a_row_position():
    """The template reads `t.rank`. If it went back to counting rows, sorting
    by Playoff Odds would relabel the ninth-rated team '#1' -- a claim the
    model never made, in the one cell a casual reader actually remembers."""
    page = _page()
    assert '_rank: t.rank' in page, (
        "the # is being computed from the row's position in the current sort "
        "again, so sorting by any other column renumbers the league")
    assert re.search(r'const ranked = sorted\.map\(\(t,\s*i\)', page) is None, (
        "the rank map takes an index again, which is the position-in-sort bug")


def test_tied_ratings_rank_the_same_way_on_every_build():
    """Two teams on an identical net rating must not swap places between runs
    and surface as a diff nobody made."""
    a = _ranked(('AAA', 0.1), ('ZZZ', 0.1), ('MMM', 0.2))
    b = _ranked(('ZZZ', 0.1), ('MMM', 0.2), ('AAA', 0.1))
    assert {r['team']: r['rank'] for r in a} == {r['team']: r['rank'] for r in b}


def test_every_team_gets_a_distinct_rank():
    rows = _ranked(('A', 0.3), ('B', 0.2), ('C', 0.2), ('D', 0.1))
    ranks = sorted(r['rank'] for r in rows)
    assert ranks == [1, 2, 3, 4], f"ranks are not a clean 1..n sequence: {ranks}"


def test_every_clickable_header_sorts_by_a_field_a_team_actually_has():
    """A header whose data-key matches no field sends both sides of the
    comparator to -Infinity, and (-Infinity - -Infinity) is NaN. A comparator
    returning NaN leaves the rows in whatever order the engine was already in,
    so the table looks sorted and is not.

    Nothing is in that state today: '#' carries data-key="rank" but its click
    handler returns early, so it is a label rather than a control -- checked
    below, since the exemption here is only sound while that early return
    exists. This guard is for the next column somebody adds.
    """
    page = _page()
    keys = set(re.findall(r'<th[^>]*data-key="([^"]+)"', page))
    assert "if(key==='rank') return;" in page, (
        "the '#' header is now clickable; either it sorts by a real field or "
        "this test's exemption for it has to go")
    fields = set(gd.build_teams_js(_ratings('BUF'), None)[0]) | {'team'}
    assert keys <= fields, (
        f"these headers sort by a field no team has, so clicking them returns "
        f"NaN from the comparator and scrambles the table: {sorted(keys - fields)}")


def test_main_loads_the_odds_before_it_joins_them():
    """An ordering bug with no symptom anywhere else. The odds argument is
    optional, so calling build_teams_js before load_playoff_odds() has run is
    not an error and raises nothing -- every team just quietly gets None and
    the column ships full of dashes. This was the actual bug in the first
    draft of the move."""
    src = Path(gd.__file__).read_text(encoding='utf-8')
    load = re.search(r'playoff_odds\s*=\s*load_playoff_odds\(\)', src)
    join = re.search(r'teams_js\s*=\s*build_teams_js\(ratings,\s*playoff_odds\)', src)
    assert load, "main() no longer loads the playoff odds"
    assert join, "main() no longer passes the odds into build_teams_js"
    assert load.start() < join.start(), (
        "build_teams_js is called before load_playoff_odds() has run, so it "
        "joins against an unbound or empty value and every team gets None")


# ---------------------------------------------------------------------------
# The page
# ---------------------------------------------------------------------------

def _page():
    return TEMPLATE.read_text(encoding='utf-8')


def test_the_column_header_carries_the_sort_key():
    """Without data-key the header is a label, not a control, and the join
    above buys nothing."""
    assert re.search(r'<th[^>]*data-key="playoff"[^>]*>', _page()), (
        "the Playoff Odds header lost its data-key, so clicking it sorts nothing")


def test_the_sort_survives_a_team_with_no_odds():
    """`(null - 5)` is NaN, and a comparator returning NaN leaves the rows in
    whatever order the engine happened to be in -- the table would look
    sorted and not be. The guard has to be on both sides of the subtraction."""
    page = _page()
    for side in ('a', 'b'):
        assert re.search(
            r'const %sv\s*=\s*\(%s\[sortKey\]===null\|\|%s\[sortKey\]===undefined\)\s*\?\s*-Infinity'
            % (side, side, side), page), (
            f"the '{side}' side of the sort comparator no longer defends against a "
            f"missing value, so one unsimulated team scrambles the whole table")


def test_the_cell_prints_a_dash_rather_than_a_number_it_does_not_have():
    page = _page()
    assert 't.playoff===null||t.playoff===undefined' in page, (
        "the Playoff Odds cell no longer distinguishes 'not simulated' from a value")


def test_the_page_explains_the_number_in_words_a_reader_can_check():
    """This dashboard is meant to be readable by a twelve-year-old. A bare
    '67.5%' invites the reading 'the model is 67.5% sure', which is not what a
    simulation count means, so the sentence saying what was actually done has
    to stay on the page beside the column."""
    page = _page()
    assert 'playoff-note' in page, "the plain-English note above the table is gone"
    note = re.search(r'id="playoff-note".*?</div>', page, re.S)
    assert note, "the note element lost its shape"
    text = re.sub(r'<[^>]+>', ' ', note.group(0)).lower()
    assert 'playoffs' in text or 'playoff' in text
    for jargon in ('monte carlo', 'stochastic', 'posterior', 'quantile'):
        assert jargon not in text, f"'{jargon}' is not twelve-year-old English"


def test_the_empty_state_still_spans_the_whole_table():
    """A colspan that lags the column count leaves the 'no teams' row short,
    and the table draws a ragged edge exactly when something has gone wrong
    and the reader most needs it to look deliberate."""
    page = _page()
    headers = re.findall(r'<th[^>]*data-key="[^"]+"', page)
    colspans = [int(n) for n in re.findall(r'colspan="(\d+)"', page)]
    assert colspans, "no colspan found; the empty-state row has changed shape"
    assert max(colspans) >= len(headers), (
        f"{len(headers)} sortable columns but the widest colspan is "
        f"{max(colspans)} -- the empty state no longer spans the table")


# ---------------------------------------------------------------------------
# The page that went away
# ---------------------------------------------------------------------------

def test_nothing_still_points_at_the_deleted_playoffs_page():
    """A nav button or a render call left behind after the section is gone is
    a click that lands on nothing."""
    page = _page()
    assert 'renderPlayoffs' not in page, "the deleted page's render function is still referenced"
    assert "showPage('playoffs')" not in page, "a control still navigates to the deleted page"
    assert 'id="page-playoffs"' not in page, "the deleted section is still in the markup"


def test_the_old_whole_file_placeholder_is_gone_from_both_sides():
    """Template and generator have to agree on the placeholder name. If the
    template kept __PLAYOFF_ODDS_JSON__ the generator would never replace it
    and the literal string would ship in the page."""
    page = _page()
    src = Path(gd.__file__).read_text(encoding='utf-8')
    assert '__PLAYOFF_ODDS_JSON__' not in page
    assert '__PLAYOFF_ODDS_JSON__' not in src
    assert '__PLAYOFF_META_JSON__' in page
    assert '__PLAYOFF_META_JSON__' in src


def test_the_meta_block_carries_the_run_details_and_not_the_teams():
    """The point of the split: per-team odds ride on the team objects, and
    only the description of the simulation run is injected separately. If
    'teams' crept back in, every team's odds would ship twice and the two
    copies could disagree."""
    src = Path(gd.__file__).read_text(encoding='utf-8')
    block = re.search(r'__PLAYOFF_META_JSON__.*?indent=2\)', src, re.S)
    assert block, "the meta injection has changed shape"
    keys = set(re.findall(r"'(\w+)'", block.group(0)))
    assert 'n_simulations' in keys and 'games_played' in keys
    assert 'teams' not in keys, "the per-team odds are being injected a second time"


def test_the_built_page_has_no_unreplaced_placeholders():
    built = Path(__file__).resolve().parents[1] / 'index.html'
    if not built.exists():
        pytest.skip('index.html has not been generated in this checkout')
    leftovers = set(re.findall(r'__[A-Z][A-Z0-9_]*__', built.read_text(encoding='utf-8')))
    assert not leftovers, f"placeholders shipped to the reader: {sorted(leftovers)}"


def test_the_built_page_actually_carries_a_playoff_value_per_team():
    """End of the chain: the join happened, the generator ran, and the number
    reached the file the reader opens."""
    built = Path(__file__).resolve().parents[1] / 'index.html'
    if not built.exists():
        pytest.skip('index.html has not been generated in this checkout')
    blob = re.search(r'const teams = (\[.*?\n\]);', built.read_text(encoding='utf-8'), re.S)
    assert blob, "could not find the injected teams array in the built page"
    teams = json.loads(blob.group(1))
    assert teams, "the built page has no teams"
    assert all('playoff' in t for t in teams), (
        "some teams reached the page without a playoff key, so their cells "
        "render a dash regardless of what the simulation said")


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
