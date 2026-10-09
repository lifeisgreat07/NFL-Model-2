"""The NBA's workflows (Stage 65), held to the registration's run times and to
the shapes the NHL's first runs showed they need.

Run with: pytest tests/test_nba_workflows.py -v
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github' / 'workflows'
DAILY = WF / 'nba-daily.yml'
CANARY = WF / 'nba-canary.yml'
STAGE = re.compile(r'^test -d (\S+) && git add (\S+)$')


def text(p):
    return p.read_text(encoding='utf-8').replace('\r\n', '\n')


def test_the_daily_run_is_scheduled_at_the_registered_times_and_by_hand():
    t = text(DAILY)
    assert re.search(r"^on:\n  schedule:\n    - cron: '0 16 \* \* \*'\n    - cron: '30 21 \* \* \*'\n"
                     r"  workflow_dispatch: \{\}", t, re.M)


def test_the_daily_run_stages_each_folder_only_if_it_exists():
    """predictions/nba does not exist until the first pick is saved; the
    NHL's first hand run failed on exactly that."""
    lines = [ln.strip() for ln in text(DAILY).splitlines() if 'git add' in ln and not ln.strip().startswith('#')]
    assert lines
    for ln in lines:
        m = STAGE.match(ln)
        assert m and m.group(1) == m.group(2), ln
    assert {STAGE.match(ln).group(2) for ln in lines} == {'data/nba', 'predictions/nba', 'results/nba'}


def test_the_daily_run_alerts_on_a_failure_and_a_drift_flag():
    t = text(DAILY)
    assert 'python -m src.sports.nba.daily | tee nba-daily.log' in t
    assert '--title "NBA: daily run failed"' in t and "if: failure()" in t
    assert "grep -q 'DRIFT CHECK: FLAGGED' nba-daily.log" in t and '--title "NBA: drift check flagged"' in t


def test_one_daily_run_at_a_time():
    assert 'concurrency:\n  group: nba-daily\n  cancel-in-progress: false' in text(DAILY)


def test_the_canary_raises_one_issue_per_failing_source():
    t = text(CANARY)
    assert '--report nba-canary-report.md --failed nba-canary-failed.txt' in t
    assert 'done < nba-canary-failed.txt' in t
    assert '--title "NBA: $source failing in the nightly canary"' in t
    assert '--title "NBA: nightly canary failing"' in t, 'a canary that names no source still alerts'


def test_the_canary_writes_nothing():
    t = text(CANARY)
    assert 'permissions:\n  contents: read\n  issues: write' in t
    assert 'git push' not in t and 'git add' not in t


def test_the_pages_rebuild_follows_the_daily_run():
    assert '"NBA daily run"' in text(WF / 'deploy-pages.yml')
