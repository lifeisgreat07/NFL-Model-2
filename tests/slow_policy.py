"""Which tests are slow, by what they do (Stage 96 item 49; audit 7, T12 and T13).

`python tasks.py quick` leaves out the tests marked `slow`. The marker used to
be held to per-file counts, so every new slow test meant editing a number in
three places, and nothing said why a test was slow. The policy instead: a test
is slow when it does one of three things, and is marked if and only if it does:

- it drives a whole daily run to the end (`daily.main(...) == 0`), fitting
  every model over every game since the registered first season;
- it re-derives a saved pick over the whole history (`load_history(`, and
  `ratings.features(` over what it read; a history read from a two-game
  fixture is not);
- it draws a paired bootstrap (`paired_bootstrap(`), 100 to 2,000 resamples
  of a season's games.

A test's own body counts, and so does any helper it calls by name that is
defined in its module or imported from another test module, one level deep (the
sources-down tests drive the run through `drive`). A run that is expected to
stop early (the schedule guard raises before any fitting) does not end in
`== 0`, so it is not slow.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

KINDS = {
    'a whole daily run': (re.compile(r'daily\.main\([^()]*\)\s*==\s*0'),),
    'a re-derivation over the whole history': (re.compile(r'\bload_history\('), re.compile(r'\bratings\.features\(')),
    'a paired bootstrap': (re.compile(r'\bpaired_bootstrap\('),),
}


def _functions(path: Path) -> tuple[ast.Module, str, dict[str, ast.FunctionDef]]:
    text = path.read_text(encoding='utf-8')
    tree = ast.parse(text)
    return tree, text, {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}


def _imported_helpers(tree: ast.Module, tests: Path) -> dict[str, Path]:
    out = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith('tests.'):
            path = tests / (node.module.split('.', 1)[1] + '.py')
            for alias in node.names:
                out[alias.asname or alias.name] = path
    return out


def _called(fn: ast.FunctionDef) -> set[str]:
    return {n.func.id for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}


def _is_marked(fn: ast.FunctionDef) -> bool:
    return any(ast.unparse(d) == 'pytest.mark.slow' for d in fn.decorator_list)


def classify(tests: Path) -> list[tuple[str, str, bool, list[str]]]:
    """(file, test, marked slow, the kinds it does) for every test function in tests/test_*.py."""
    out = []
    for path in sorted(tests.glob('test_*.py')):
        tree, text, funcs = _functions(path)
        imported = _imported_helpers(tree, tests)
        for name, fn in funcs.items():
            if not name.startswith('test_'):
                continue
            sources = [ast.get_source_segment(text, fn) or '']
            for called in _called(fn) - {name}:
                if called in funcs:
                    sources.append(ast.get_source_segment(text, funcs[called]) or '')
                elif called in imported and imported[called].exists():
                    _, other_text, other = _functions(imported[called])
                    if called in other:
                        sources.append(ast.get_source_segment(other_text, other[called]) or '')
            body = '\n'.join(sources)
            kinds = [k for k, rxs in KINDS.items() if all(rx.search(body) for rx in rxs)]
            out.append((path.name, name, _is_marked(fn), kinds))
    return out


def violations(tests: Path) -> list[str]:
    bad = []
    for file, name, marked, kinds in classify(tests):
        if kinds and not marked:
            bad.append(f'{file}::{name} does {kinds[0]} and is not marked slow')
        if marked and not kinds:
            bad.append(f'{file}::{name} is marked slow and does none of the slow things')
    return bad
