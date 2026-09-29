"""The generator reads and writes UTF-8 whatever the machine's default
(Stage 25 item 8, agreed with Mark 2026-09-28).

Until then src/generate_dashboard.py opened its inputs and wrote index.html
with the platform default. On Linux CI that is UTF-8; on Windows it is
cp1252, so a character outside cp1252 in generated text (#164's en dash
was the near miss) crashed the local build, and the file a Windows build
wrote was not the bytes CI would write. docs/context.md carried it as
"known and deliberately not fixed", with a standing instruction to avoid
non-ASCII in generated text. Every open() now names its encoding.
"""
import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / 'src' / 'generate_dashboard.py'


def open_calls():
    tree = ast.parse(SRC.read_text(encoding='utf-8'))
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'open']


def test_the_scan_finds_the_reads_and_the_write():
    calls = open_calls()
    assert len(calls) >= 10, f'only {len(calls)} open() calls found -- re-anchor this test'
    writes = [c for c in calls if len(c.args) > 1 and getattr(c.args[1], 'value', None) == 'w']
    assert writes, 'the index.html write is not found'


def test_every_open_names_utf8():
    bad = [n.lineno for n in open_calls()
           if not any(k.arg == 'encoding' and getattr(k.value, 'value', None) == 'utf-8'
                      for k in n.keywords)]
    assert not bad, f'open() without encoding="utf-8" at lines {bad}'
