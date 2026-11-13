"""
Stage 84 item 6: the NBA's checks page says where the drift check stands,
from the file the daily run writes, as the NHL's does.

Run with: pytest tests/test_nba_drift_on_page.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.optional import in_ci
from tests.page_script import day_script

ROOT = Path(__file__).resolve().parents[1]
JS = day_script('nba')
NODE = shutil.which('node')
RULE = {'rule': {'min_games': 100}}


def drift_status(d, rule):
    # Stage 95 item 33: driftStatus says the leak line through leakNote.
    src = ''.join(re.search(rf'function {name}\(.*?\n\}}\n', JS, re.S).group(0)
                  for name in ('leakNote', 'driftStatus'))
    prog = src + f'process.stdout.write(driftStatus({json.dumps(d)}, {json.dumps(rule)}));'
    return subprocess.run([NODE, '-e', prog], capture_output=True, text=True, check=True).stdout


@pytest.mark.skipif(NODE is None and not in_ci(), reason='node not installed')
@pytest.mark.parametrize('d, says', [
    (None, 'nothing to test'),
    ({'games': 92, 'mean_log_loss': 0.6267, 'baseline': 0.5983, 'flagged': False}, '92 of the 100 graded games'),
    ({'games': 120, 'mean_log_loss': 0.6267, 'baseline': 0.5983, 'flagged': False}, 'Not flagged.'),
    ({'games': 120, 'mean_log_loss': 0.70, 'baseline': 0.5983, 'flagged': True}, 'Flagged.'),
])
def test_the_status_follows_the_file(d, says):
    out = drift_status(d, RULE)
    assert says in out
    if d and d['games']:
        assert f"{d['mean_log_loss']:.4f}" in out and f"{d['baseline']:.4f}" in out


def test_the_page_renders_it_and_the_build_passes_the_rule():
    body = re.search(r'function renderReliability\(\)\{.*?\n\}\n', JS, re.S).group(0)
    assert '${driftStatus(BD.drift, BD.drift_rule)}' in body
    site = (ROOT / 'src' / 'sports' / 'nba' / 'site.py').read_text(encoding='utf-8')
    assert "'drift_rule': _maybe(PATHS.data / 'drift_baseline.json')" in site
