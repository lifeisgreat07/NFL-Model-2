"""Nothing bleeds between sports (Stage 50 item 4; decision record 0006).

The checks live in `src/core/isolation.py`. This file runs them twice:

- over this repository, where every rule must hold today; and
- over small synthetic repositories built in `tmp_path`, each breaking one
  rule on purpose, where the check must report it.

The second half is what keeps the first honest. Until the NHL arrives, the
real repository has one sport and almost nothing for rules 1, 3 and 4 to
look at, so a check that had stopped working would pass here unseen. The
mutation cases in `tests/mutation/cases/sport_isolation.json` break each
check and name the synthetic test that must catch it.

Rule 5 (a change to one sport moves no byte another publishes) needs a
build, not a scan; it is the proof run at Stages 52 and 60.
"""
import importlib.util
import os
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from src.core import isolation
from src.core.sport import SCHEDULE_COLUMNS, GameStatus, check_schedule, sport_paths

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- this repository

def test_this_repository_breaks_no_isolation_rule():
    assert isolation.all_violations(ROOT) == []


def test_every_listed_workflow_still_exists():
    """The legacy and shared lists name real files. A stale entry would let a
    new workflow reuse the name and skip the rules."""
    present = {p.name for p in (ROOT / '.github' / 'workflows').glob('*.y*ml')}
    assert isolation.LEGACY_NFL_WORKFLOWS <= present
    assert isolation.SHARED_WORKFLOWS <= present
    assert not isolation.LEGACY_NFL_WORKFLOWS & isolation.SHARED_WORKFLOWS


def test_the_legacy_lists_only_shrink():
    """Stage 52 empties them; nothing is ever added. Adding a name here means
    editing this test too, which a reviewer sees."""
    assert isolation.LEGACY_NFL_WORKFLOWS <= {
        'nfl-schedule-probe.yml', 'nightly-canary.yml', 'run-backtest.yml',
        'weekend-refresh.yml', 'weekly-update.yml'}
    assert set(isolation.LEGACY_NFL_PACKAGES) <= {'src.pipeline', 'src.research'}


def test_the_core_type_checks_strictly(tmp_path):
    """The interface is the contract every sport is written against, so it is
    held to the agents' standard (mypy --strict)."""
    if importlib.util.find_spec('mypy') is None:
        if os.environ.get('CI'):
            pytest.fail('mypy is not installed in CI, where requirements-dev.txt installs it')
        pytest.skip('mypy not installed (pip install -r requirements-dev.txt)')
    cmd = ['python', '-m', 'mypy', '--strict', '--ignore-missing-imports', '--follow-imports=silent',
           '--cache-dir', str(tmp_path / 'mypy-cache'), 'src/core']
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-500:]


# ---------------------------------------------------------------- synthetic repositories

def make_repo(tmp_path, files):
    """A repository holding these files (path -> text), with an NHL package so
    there are two sports to keep apart."""
    files = {'src/__init__.py': '', 'src/core/__init__.py': '',
             'src/sports/__init__.py': '', 'src/sports/nhl/__init__.py': '', **files}
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    return tmp_path


def test_a_clean_two_sport_repository_passes(tmp_path):
    root = make_repo(tmp_path, {
        'src/core/lock.py': 'import pandas\n',
        'src/sports/nhl/model.py': 'from src.core import lock\nfrom . import model\nPATH = "data/nhl/x.json"\n',
        'src/site/home.py': 'from src.sports.nhl import model\nfrom src.pipeline import config\n',
        'src/pipeline/config.py': 'from src.core import lock\n',
    })
    assert isolation.sports(root) == ['nfl', 'nhl']
    assert isolation.all_violations(root) == []


def test_a_sport_importing_another_is_caught(tmp_path):
    root = make_repo(tmp_path, {'src/sports/nhl/model.py': 'from src.pipeline import ratings_engine\n'})
    found = isolation.import_violations(root)
    assert found and 'nhl imports another sport (nfl)' in found[0]


def test_a_relative_import_into_another_sport_is_caught(tmp_path):
    root = make_repo(tmp_path, {
        'src/sports/nba/__init__.py': '',
        'src/sports/nba/x.py': 'from ..nhl import model\n',
        'src/sports/nhl/model.py': '',
    })
    found = isolation.import_violations(root)
    assert any('nba imports another sport (nhl)' in f for f in found)


def test_the_core_importing_a_sport_is_caught(tmp_path):
    root = make_repo(tmp_path, {'src/core/grading.py': 'import src.sports.nhl.model\n'})
    found = isolation.import_violations(root)
    assert found and 'the core imports no sport' in found[0]


def test_the_core_importing_the_legacy_nfl_is_caught(tmp_path):
    """Until Stage 52, src/pipeline is the NFL; the core may not reach it."""
    root = make_repo(tmp_path, {'src/core/grading.py': 'from src.pipeline.model_specs import ModelSpec\n'})
    assert any('the core imports no sport' in f for f in isolation.import_violations(root))


def test_importing_the_site_layer_is_caught(tmp_path):
    root = make_repo(tmp_path, {'src/site/home.py': '', 'src/agents/x.py': 'from src.site import home\n'})
    assert any('only src/site sees every sport' in f for f in isolation.import_violations(root))


def test_a_path_into_another_sport_is_caught(tmp_path):
    root = make_repo(tmp_path, {'src/sports/nhl/io.py': 'P = "predictions/nfl/2026_week5.json"\n'})
    found = isolation.literal_violations(root)
    assert found and "'predictions/nfl'" in found[0]


def test_a_dynamic_import_of_another_sport_is_caught(tmp_path):
    root = make_repo(tmp_path, {'src/core/registry.py': 'import importlib\nimportlib.import_module("src.sports.nhl")\n'})
    assert isolation.literal_violations(root)


def test_a_docstring_about_another_sport_is_not_a_path(tmp_path):
    root = make_repo(tmp_path, {'src/sports/nhl/io.py': '"""Unlike data/nfl/, the NHL..."""\n'})
    assert isolation.literal_violations(root) == []


WF = '.github/workflows/'


def test_an_unclassified_workflow_is_caught(tmp_path):
    root = make_repo(tmp_path, {WF + 'daily-update.yml': 'name: Daily update\n'})
    assert any('neither a sport' in f for f in isolation.workflow_violations(root))


NHL_OK = '''name: NHL daily update
jobs:
  run:
    steps:
      - uses: stefanzweifel/git-auto-commit-action@abc
        with:
          file_pattern: 'predictions/nhl/** data/nhl/**'
      - run: |
          git add results/nhl/2026-10-06.json
          python -m src.pipeline.alerts --title "NHL: daily update failed" --body-file b.md
      - uses: actions/upload-artifact@v4
        with:
          name: report
          path: |
            results/nhl/report.md
      - run: echo done
'''


def test_a_well_behaved_sport_workflow_passes(tmp_path):
    root = make_repo(tmp_path, {WF + 'nhl-daily-update.yml': NHL_OK})
    assert isolation.workflow_violations(root) == []


@pytest.mark.parametrize('bad, expected', [
    ("file_pattern: 'predictions/nhl/** data/nhl/**'", "file_pattern: 'predictions/nhl/** data/**'"),
    ('git add results/nhl/2026-10-06.json', 'git add results/nfl/2026-10-06.json'),
    ('git add results/nhl/2026-10-06.json', 'git add -A'),
    ('results/nhl/report.md', 'results/report.md'),
], ids=['commit-pattern', 'git-add-other-sport', 'git-add-everything', 'upload'])
def test_a_sport_workflow_writing_outside_its_folders_is_caught(tmp_path, bad, expected):
    root = make_repo(tmp_path, {WF + 'nhl-daily-update.yml': NHL_OK.replace(bad, expected)})
    found = isolation.workflow_violations(root)
    assert any('outside its own folders' in f for f in found), found


def test_a_sport_workflow_name_without_its_sport_is_caught(tmp_path):
    root = make_repo(tmp_path, {WF + 'nhl-daily-update.yml': NHL_OK.replace('name: NHL daily update', 'name: Daily update')})
    assert any('its name must start with "NHL "' in f for f in isolation.workflow_violations(root))


def test_an_alert_title_without_its_sport_is_caught(tmp_path):
    root = make_repo(tmp_path, {WF + 'nhl-daily-update.yml': NHL_OK.replace('"NHL: daily update failed"', '"Daily update failed"')})
    assert any('alert title' in f for f in isolation.workflow_violations(root))


def test_a_storage_key_without_its_sport_is_caught(tmp_path):
    root = make_repo(tmp_path, {'src/sports/nhl/page/app.js':
                                "const PICKS_KEY = 'nhl:my-picks';\nlocalStorage.getItem('my-picks');\n"})
    found = isolation.name_violations(root)
    assert len(found) == 1 and "'my-picks'" in found[0]


def test_unscoped_css_is_caught(tmp_path):
    root = make_repo(tmp_path, {'src/sports/nhl/page/styles.css':
                                '[data-sport="nhl"] .card{color:red}\n.nhl-goalie{x:1}\n'
                                '@keyframes nhl-pulse{from{a:1}to{a:2}}\n.card{color:blue}\n'})
    found = isolation.name_violations(root)
    assert len(found) == 1 and "'.card'" in found[0]


def test_a_sport_folder_that_is_not_a_code_is_caught(tmp_path):
    root = make_repo(tmp_path, {'src/sports/Hockey/__init__.py': ''})
    assert any('a sport folder is its code' in f for f in isolation.name_violations(root))


# ---------------------------------------------------------------- the interface

def test_sport_paths_stay_under_the_sport():
    p = sport_paths('nhl')
    for folder in (p.data, p.predictions, p.results, p.experiments, p.site):
        assert folder.parts[-1] == 'nhl'
    with pytest.raises(ValueError):
        sport_paths('../nfl')


def test_cancelled_is_a_state_the_core_knows():
    """Mark, 2026-10-05: a cancelled game shows "Cancelled" and is not graded."""
    assert GameStatus('cancelled') is GameStatus.CANCELLED


def _schedule(**over):
    row = {'game_id': 1, 'season': 2026, 'slate': '2026-10-06',
           'start_utc': pd.Timestamp('2026-10-06T23:00Z'), 'home': 'TOR', 'away': 'NSH',
           'status': 'scheduled', 'home_score': None, 'away_score': None, 'home_win': None}
    row.update(over)
    return pd.DataFrame([row])


def test_a_schedule_meeting_the_contract_has_no_problems():
    assert list(_schedule().columns) == list(SCHEDULE_COLUMNS)
    assert check_schedule('nhl', _schedule()) == []


@pytest.mark.parametrize('df, expected', [
    (_schedule().drop(columns='slate'), "no 'slate' column"),
    (pd.concat([_schedule(), _schedule()]), 'game_id is not unique'),
    (_schedule(status='OFF'), 'unknown status'),
    (_schedule(start_utc=pd.Timestamp('2026-10-06 23:00')), 'not timezone-aware'),
], ids=['missing-column', 'duplicate-id', 'league-status-word', 'naive-time'])
def test_a_schedule_breaking_the_contract_is_named(df, expected):
    assert any(expected in p for p in check_schedule('nhl', df))


def test_the_model_spec_has_the_shape_the_core_asks_for():
    """The core describes ModelSpec instead of importing it (rule 2), so this
    holds the two together until Stage 52 moves the file."""
    from src.pipeline.model_specs import MODEL_SPECS
    for spec in MODEL_SPECS.values():
        assert isinstance(spec.features, tuple) and callable(spec.fit)
