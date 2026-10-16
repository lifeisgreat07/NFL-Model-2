"""The NHL's side column prints a club's name once (Stage 78 item 41, the 2026-10-13 UI/UX audit's L1).

The column beside the day board read "Tampa Bay LightningTBL 93% to make
the playoffs" at 1440 px (measured 2026-10-14): clubCell() writes the name
and the code side by side, and only .nhl-table hides one of them. The
column now prints the name alone, and clubCell() is called only where the
markup it lands in is an .nhl-table.

Run with: pytest tests/test_nhl_side_names.py -v
"""
import re
from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js').read_text(encoding='utf-8')


def functions():
    """{name: body} for each top-level function."""
    return {m.group(1): m.group(2) for m in re.finditer(r'^function (\w+)\(.*?\)\{(.*?)\n\}\n', JS, re.S | re.M)}


def test_the_side_column_prints_the_name_alone():
    side = functions()['sideHtml']
    assert 'clubCell(' not in side
    assert '<span>${escapeHtml(teamName(t.team))} <b>${odds(t.playoff_pct)}</b> to make the playoffs</span>' in side


def test_club_cells_land_only_in_a_table_that_hides_one_half():
    callers = [n for n, body in functions().items() if 'clubCell(' in body and n != 'clubCell']
    assert callers, 'clubCell is not called at all -- re-anchor this guard'
    for name in callers:
        assert 'nhl-table' in functions()[name], f'{name} writes club cells outside an .nhl-table'
