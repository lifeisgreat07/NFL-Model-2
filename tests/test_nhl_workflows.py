"""The NHL's workflows, held to the shapes their first runs showed they need.

Run with: pytest tests/test_nhl_workflows.py -v
"""
import re
from pathlib import Path

DAILY = Path(__file__).resolve().parents[1] / '.github' / 'workflows' / 'nhl-daily.yml'
STAGE = re.compile(r'^test -d (\S+) && git add (\S+)$')


def test_the_daily_run_stages_each_folder_only_if_it_exists():
    """Staging a path that does not exist is an error. predictions/nhl does
    not exist until the first pick is saved, and the first hand run of the
    daily run (2026-10-06) failed on exactly that with nothing to save."""
    lines = [ln.strip() for ln in DAILY.read_text(encoding='utf-8').splitlines()
             if 'git add' in ln and not ln.strip().startswith('#')]
    assert lines, 'the daily run stages nothing'
    for ln in lines:
        m = STAGE.match(ln)
        assert m and m.group(1) == m.group(2), f'not guarded by its own folder: {ln!r}'
    staged = {STAGE.match(ln).group(2) for ln in lines}
    assert staged == {'data/nhl', 'predictions/nhl', 'results/nhl'}
