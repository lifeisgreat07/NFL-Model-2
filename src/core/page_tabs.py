"""Every sport page's tabs: one order, one name each, one address each (audit 9 D14).

The audit found the three sports naming and ordering the same pages differently: "Power Ratings" on the NFL
and the NBA, "Ratings" on the NHL; "Team Deep-Dive" on the NFL, "Teams" on the others; "Standings Odds" on the
NHL, "Standings" on the NBA; What's Changed before Checking the AI's work on the NFL, after it on the others;
and the NFL's addresses #changelog and #teamdive where the others have #changes and #teams. This is the one
list the three templates are held to (tests/test_page_tabs.py): a sport shows the tabs it has, in this order,
under these names, at these addresses.

The NFL's pages keep their older ids inside the page (page-teamdive, page-changelog), which its scripts and
tests use throughout; their addresses are the shared ones, and the old addresses still open them and are
replaced by the new (src/dashboard/app_pages.js ROUTE_ADDRESS, src/core/routes.js ROUTE_OLD).
"""
from __future__ import annotations

#: (address, the sidebar's name, the phone bar's or its More sheet's name), in the order every sport shows them.
#: The board's sidebar name is each sport's own (BOARD): the NFL's is a week, the others' a day.
TABS: tuple[tuple[str, str, str], ...] = (
    ('board', '', 'Board'),
    ('standings', 'Standings', 'Standings'),
    ('ratings', 'Power Ratings', 'Ratings'),
    ('teams', 'Teams', 'Teams'),
    ('picks', 'My Picks Log', 'Picks'),
    ('accuracy', 'Season Accuracy', 'Accuracy'),
    ('modellab', 'Model Lab', 'Model Lab'),
    ('method', 'Methodology', 'Methodology'),
    ('reliability', "Checking the AI's work", "Checking the AI's work"),
    ('changes', "What's Changed", "What's Changed"),
)
BOARD = {'nfl': 'Week Board', 'nhl': 'Day Board', 'nba': 'Day Board'}
#: The tabs a phone keeps behind More; the rest are on its bar.
MORE = ('teams', 'modellab', 'method', 'reliability', 'changes')
#: An address that used to open a page, and the address it now has (the NFL's own, before D14).
OLD_ADDRESSES = {'teamdive': 'teams', 'changelog': 'changes'}


def address(page_id: str) -> str:
    """A page's address from the id its section has in the page."""
    return OLD_ADDRESSES.get(page_id, page_id)
