"""Team Deep-Dive opens on the top-rated team (Stage 19).

With no #team/<code> link, the page used to open on the first option
alphabetically: Arizona, whatever Arizona's season. It now opens on rank 1 of
Power Ratings, by the rank Python computed for that table. A link still wins,
because applyRoute() sets the select after the first render. With no rank 1,
or a rank 1 the history file has no name for, it falls back to the first team
alphabetically, so the page never opens on nothing.

tests/team_dive_default_harness.js runs the shipped teamDiveDefault(); the
rest reads where the template calls it. Requires node; skipped loudly if
absent.

Run with: pytest tests/test_team_dive_default.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.pipeline.template_parts import JOINED_TEMPLATE

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = JOINED_TEMPLATE
HARNESS = Path(__file__).parent / 'team_dive_default_harness.js'
NODE = shutil.which('node')


@pytest.fixture(scope='module')
def picked():
    if NODE is None:
        pytest.skip('node not on PATH -- teamDiveDefault() cannot be executed')
    proc = subprocess.run([NODE, str(HARNESS)], cwd=REPO_ROOT,
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, f'harness failed:\n{proc.stderr}'
    data = json.loads(proc.stdout)
    assert 'fatal' not in data, data.get('fatal')
    return data


def render_team_dive():
    src = TEMPLATE.read_text(encoding='utf-8').replace('\r\n', '\n')
    start = src.index('function renderTeamDive(')
    return src[start:src.index('\n}\n', start)]


def test_the_page_opens_on_rank_one(picked):
    assert picked['top_rated'] == 'BUF'
    assert picked['top_rated_reversed'] == 'BUF', 'the default follows file order, not rank'


def test_without_a_usable_rank_one_it_falls_back_to_the_first_team_alphabetically(picked):
    for case in ('no_ratings', 'ratings_missing', 'no_rank_one', 'rank_one_without_history'):
        assert picked[case] == 'ARI', f'{case}: {picked[case]!r}'


def test_the_fallback_sorts_by_name_like_the_options_do(picked):
    assert picked['alphabetical_by_name'] == 'ZZ'


def test_the_first_render_sets_the_default_before_building_the_listbox():
    """The listbox reads the select once it is built; set after it, the
    button would name one team while the page below it showed another."""
    body = render_team_dive()
    set_at = body.find('select.value = teamDiveDefault(teamHistory.names, teams);')
    build_at = body.find('enhanceSelect(select)')
    assert set_at != -1, 'the first render no longer sets the default team'
    assert build_at != -1, 'enhanceSelect(select) is gone -- re-anchor this guard'
    assert set_at < build_at


def test_a_team_link_still_overrides_the_default():
    src = TEMPLATE.read_text(encoding='utf-8').replace('\r\n', '\n')
    route = src[src.index('function applyRoute('):]
    route = route[:route.index('\n}\n')]
    assert re.search(r"if\(r\.team\)\{\s*const s = document\.getElementById\('teamdive-select'\);", route)
    first_render = src.index('\nrenderTeamDive();')
    load_route = src.index('  if(location.hash) applyRoute(parseRoute(location.hash, routeKnown));')
    assert first_render < load_route, (
        'the page applies a #team/ link before its first render sets the default, '
        'so the default would overwrite the link')
