"""
Stage 89 item 4 (the 2026-11-02 review): docs/architecture.md's diagram shows
the system as it is, three sports and four agents, and its QB overrides row
says what the folder holds.

The diagram was drawn when the project was the NFL alone, with Scout and
Booth; the NHL and NBA daily runs, the home page, Spotter and Line Judge were
added to the table under it but never to the picture, and the overrides row
still said no override had ever been filed.

Run with: pytest tests/test_architecture_diagram.py -v
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / 'docs' / 'architecture.md').read_text(encoding='utf-8')


def diagram():
    m = re.search(r'```mermaid\n(.*?)```', TEXT, re.S)
    assert m, 'the diagram is gone'
    return m.group(1)


def test_the_diagram_has_each_sport_and_its_run():
    d = diagram()
    for label in ('NFL weekly update', 'NFL weekend refresh', 'NHL daily run', 'NBA daily run'):
        assert label in d, label
    assert 'NFL, NHL and NBA pages' in d and 'home page' in d


def test_the_diagram_has_the_four_agents():
    d = diagram()
    for agent in ('Scout', 'Booth', 'Spotter', 'Line Judge'):
        assert re.search(rf'\["{agent}:', d), agent
    assert 'subgraph AGENTS["The four agents"]' in d


def test_every_box_in_the_diagram_is_drawn_into_it():
    """Every edge joins boxes or groups the diagram defines, and every box
    has an edge of its own or sits in a group that has one."""
    d = diagram()
    member = {}
    group = None
    for line in d.splitlines():
        if m := re.match(r'\s+subgraph ([A-Z]+)\[', line):
            group = m.group(1)
        elif line.strip() == 'end':
            group = None
        elif m := re.match(r'\s+([A-Z]+)\["', line):
            member[m.group(1)] = group
    edges = re.findall(r'^\s+([A-Z]+) (?:-->|-\.[^\n]*\.->) ([A-Z]+)$', d, re.M)
    assert len(edges) >= 10, 'the edge pattern found almost nothing'
    ends = {e for pair in edges for e in pair}
    groups = {g for g in member.values() if g}
    assert ends <= set(member) | groups, ends - set(member) - groups
    loose = {b for b, g in member.items() if b not in ends and g not in ends}
    assert loose == set(), f'boxes nothing points to or from: {loose}'


def test_the_overrides_row_says_what_the_folder_holds():
    folder = ROOT / 'data' / 'nfl' / 'qb_overrides'
    assert any(folder.glob('*_week*.json')), 'the premise: overrides have been filed'
    row = next(line for line in TEXT.splitlines() if line.startswith('| QB override files |'))
    assert '`data/nfl/qb_overrides/`' in row and 'None has been filed' not in row
    assert 'merged to main before Thursday' in row
