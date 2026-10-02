"""
src/pipeline/paths.py: one definition of the shared locations, the week in a file
name, the current season and the 32 teams (Stage 32 item 15).

The point of the file is that there is ONE of each, so the tests check that
as a class: every module's name for a shared thing is bound to the object
here, and no module in src/ defines its own copy again. The functions are
checked on the cases each old copy handled.

Run with: pytest tests/test_paths.py -v
"""
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'

from src.pipeline import paths  # noqa: E402


@pytest.mark.parametrize('stem,expected', [
    ('2026_week3', (2026, 3)), ('2025_week18', (2025, 18)), ('2026_week03', (2026, 3)),
    ('2026_week3_graded', None), ('2026_week5_lines', None), ('notes', None), ('2026_weekX', None),
])
def test_a_week_is_read_from_a_file_name_the_way_it_always_was(stem, expected):
    assert paths.parse_week(stem) == expected


@pytest.mark.parametrize('when,season', [
    (datetime(2027, 1, 20, tzinfo=timezone.utc), 2026), (datetime(2027, 2, 28, tzinfo=timezone.utc), 2026),
    (datetime(2027, 3, 1, tzinfo=timezone.utc), 2027), (datetime(2026, 9, 30, tzinfo=timezone.utc), 2026),
    (date(2026, 12, 31), 2026),
])
def test_january_and_february_belong_to_last_season(when, season):
    assert paths.current_season(when) == season


def test_the_workflow_asks_paths_for_the_season():
    """The weekly workflow's bash used to hold a third copy of the rule."""
    wf = (ROOT / '.github' / 'workflows' / 'weekly-update.yml').read_text(encoding='utf-8')
    step = re.search(r'- name: Determine current NFL season\n(.*?)\n\n', wf, re.S)
    assert step, 'the season step is not findable -- re-anchor this guard'
    assert 'season=$(python -m src.pipeline.paths --current-season)' in step.group(1)
    assert 'date -u' not in step.group(1), 'the bash copy of the season rule is back'
    r = subprocess.run([sys.executable, str(SRC / 'paths.py'), '--current-season'],
                       capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.strip() == str(paths.current_season())


def test_there_are_32_teams_and_every_team_table_agrees():
    from src.pipeline import simulate_season
    from src.pipeline import tv_channels
    assert len(paths.NFL_TEAMS) == 32 and paths.NFL_TEAMS == frozenset(paths.TEAM_NAMES)
    assert set(simulate_season.TEAM_DIV) == paths.NFL_TEAMS
    assert set(tv_channels.TEAMS.values()) == paths.NFL_TEAMS


def test_each_module_name_is_bound_to_the_one_definition():
    from src.pipeline import canary
    from src.pipeline import check_drift
    from src.pipeline import data_quality
    from src.pipeline import generate_dashboard
    from src.pipeline import grade_predictions
    from src.pipeline import weekend_refresh
    from src.pipeline import weekly_update
    bound = {
        (weekly_update, 'PRED_DIR'): paths.PRED_DIR, (weekly_update, 'PREVIEW_DIR'): paths.PREVIEW_DIR,
        (weekly_update, 'SKIPPED_DIR'): paths.SKIPPED_DIR, (weekly_update, 'DATA_DIR'): paths.DATA_DIR,
        (weekly_update, 'TEAM_NAMES'): paths.TEAM_NAMES,
        (generate_dashboard, 'PRED_DIR'): paths.PRED_DIR, (generate_dashboard, 'RESULTS_DIR'): paths.RESULTS_DIR,
        (generate_dashboard, 'parse_week_stem'): paths.parse_week,
        (grade_predictions, 'PRED_DIR'): paths.PRED_DIR, (grade_predictions, 'RESULTS_DIR'): paths.RESULTS_DIR,
        (weekend_refresh, 'PRED_DIR'): paths.PRED_DIR, (weekend_refresh, 'STATUS_DIR'): paths.STATUS_DIR,
        (weekend_refresh, 'current_season'): paths.current_season,
        (check_drift, 'RESULTS_DIR'): paths.RESULTS_DIR,
        (canary, 'current_season'): paths.current_season,
        (data_quality, 'NFL_TEAMS'): paths.NFL_TEAMS,
    }
    wrong = [f'{m.__name__}.{n}' for (m, n), obj in bound.items() if getattr(m, n) is not obj]
    assert not wrong, f'these are their own copies again, not the one in paths.py: {wrong}'


COPIES = [
    (r'^(PRED_DIR|RESULTS_DIR|DATA_DIR|PREVIEW_DIR|SKIPPED_DIR|STATUS_DIR)\s*=', 'a data folder'),
    (r'^def current_season\(', 'the season rule'),
    (r'^def parse_week(_stem)?\(', 'the week-in-a-file-name rule'),
    # Inline, too: weekend_refresh and weekly_update each still split the
    # stem themselves after #241 (the third audit found both). Stage 35.
    (r"\.split\(['\"]_week['\"]\)", 'the week-in-a-file-name rule, inline'),
    (r'^(NFL_TEAMS|TEAM_NAMES)\s*=', 'the team list'),
]


# Not copies: their RESULTS_DIR is experiments/stageN/results, a different
# folder that happens to share the name.
DIFFERENT_FOLDER = {'stage5_run.py', 'stage6_run.py'}


def copies(sources):
    """[(file, what)] for every module-level redefinition outside paths.py."""
    found = []
    for name, text in sources.items():
        if name == 'paths.py' or name in DIFFERENT_FOLDER:
            continue
        for pattern, what in COPIES:
            if re.search(pattern, text, re.M):
                found.append((name, what))
    return found


def test_no_module_defines_its_own_copy_again():
    sources = {p.name: p.read_text(encoding='utf-8') for p in SRC.glob('*.py')}
    assert len(sources) > 30, 'src/ was not read -- the matcher is broken'
    assert not copies(sources)


def test_a_copy_is_found():
    """Synthetic, so the failing branch stays reachable."""
    assert copies({'x.py': "RESULTS_DIR = ROOT / 'results'\n", 'paths.py': 'PRED_DIR = 1\n'}) == [
        ('x.py', 'a data folder')]
