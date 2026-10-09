"""No dead code in src/ (Stage 48 item 18).

vulture, pinned in requirements-dev.txt, reads src/, the tests and tasks.py
for definitions nothing uses, at 60% confidence and above. Code used only by
a test still counts as used. Anything kept on purpose is in
tests/dead_code_allowlist.py with its reason. A new unused function,
variable or class fails here with vulture's own line for it.

The first run (2026-10-06) found 25 names. Five were dead and were deleted,
none of them in src/pipeline/; the rest are in the allowlist: the multi-sport
contract's fields, two overrides a framework calls, a written-down
vocabulary, and the NHL's former abbreviations.

Run with: pytest tests/test_dead_code.py -v
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = 'tests/dead_code_allowlist.py'


@pytest.mark.skipif(importlib.util.find_spec('vulture') is None, reason='vulture not installed')
def test_nothing_in_src_is_unused():
    r = subprocess.run([sys.executable, '-m', 'vulture', 'src', 'tests', 'tasks.py', ALLOWLIST,
                        '--min-confidence', '60', '--exclude', 'tests/booth_fixtures'],
                       cwd=ROOT, capture_output=True, text=True)
    found = [ln for ln in r.stdout.splitlines() if ln.replace('\\', '/').startswith('src/')]
    assert not found, 'unused code in src/ (delete it, or add it to ' + ALLOWLIST + ' with a reason):\n' + '\n'.join(found)


def test_every_allowlist_entry_has_a_reason():
    lines = (ROOT / ALLOWLIST).read_text(encoding='utf-8').splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith('_.'):
            above = [x for x in lines[:i] if x.strip()]
            assert any(x.startswith('#') for x in above), f'{ln} has no reason above it'


def test_vulture_is_pinned_for_ci():
    reqs = (ROOT / 'requirements-dev.txt').read_text(encoding='utf-8').splitlines()
    assert any(r.startswith('vulture==') for r in reqs)
