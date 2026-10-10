"""Every third-party package src/ imports is pinned, or says why not (Stage 68 item 14).

The 2026-10-09 audit found scipy imported (src/sports/nfl/research/
kalman_ratings.py) and pinned nowhere: it arrived with scikit-learn, at
whatever version resolved that day. Now every top-level import under src/
that is not the standard library is either pinned in requirements.txt or
named below with its reason. The nightly audit reads requirements-dev.txt
too.

Run with: pytest tests/test_imports_pinned.py -v
"""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
#: import name -> the name requirements.txt pins it under.
PINNED_AS = {'sklearn': 'scikit-learn'}
#: Imported but deliberately not pinned here, and why.
UNPINNED = {
    'polars': "arrives with nflreadpy, whose own pin decides it",
    'playwright': "a research script run where Playwright is installed, never by a workflow",
    'loader': "tests/booth_fixtures/loader.py, this repository's own module",
}


def third_party_imports():
    found = set()
    for p in (ROOT / 'src').rglob('*.py'):
        for node in ast.walk(ast.parse(p.read_text(encoding='utf-8'))):
            if isinstance(node, ast.Import):
                found |= {a.name.split('.')[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                found.add(node.module.split('.')[0])
    return {n for n in found if n not in sys.stdlib_module_names and n != 'src'}


def pins():
    text = (ROOT / 'requirements.txt').read_text(encoding='utf-8')
    return {m.lower() for m in re.findall(r'^([A-Za-z0-9_.-]+)==', text, re.M)}


def test_the_scan_sees_the_packages_it_must():
    assert {'pandas', 'numpy', 'sklearn', 'scipy'} <= third_party_imports()


def test_every_import_is_pinned_or_explained():
    missing = sorted(n for n in third_party_imports()
                     if PINNED_AS.get(n, n).lower() not in pins() and n not in UNPINNED)
    assert not missing, f'imported by src/ and pinned nowhere: {missing}'


def test_the_nightly_audit_reads_both_files():
    wf = (ROOT / '.github' / 'workflows' / 'nightly-dependency-audit.yml').read_text(encoding='utf-8')
    assert 'pip-audit -r requirements.txt -r requirements-dev.txt ' in wf
