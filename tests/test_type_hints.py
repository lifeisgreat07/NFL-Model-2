"""
The pipeline's public functions carry type hints (Stage 32 item 18).

The 2026-09-29 re-audit counted 8 annotated functions out of 389. It asked
for hints on the public surface of the modules the weekly pipeline is built
from, not a sweep of the whole repository. This file holds that surface
as a class: every public top-level function in each listed module has an
annotated return and annotated parameters. A module joins the list when its
hints land, so the list is also the record of how far the item has got.

Hints are not checked at run time. Each listed module uses
`from __future__ import annotations`, so they are never evaluated and cannot
change behaviour. They are for the reader and for any checker run over
the code.

Run with: pytest tests/test_type_hints.py -v
"""
import inspect
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

ANNOTATED = ['ratings_engine', 'data_loader', 'weekly_update', 'grade_predictions',
             'generate_dashboard']


def missing_hints(module):
    """['function(param)' or 'function -> return'] for every public top-level
    function of `module` with a parameter or return left unannotated."""
    out = []
    for name, fn in inspect.getmembers(module, inspect.isfunction):
        if fn.__module__ != module.__name__ or name.startswith('_'):
            continue
        sig = inspect.signature(fn)
        out += [f'{name}({p})' for p in sig.parameters
                if sig.parameters[p].annotation is inspect.Parameter.empty]
        if sig.return_annotation is inspect.Signature.empty:
            out.append(f'{name} -> return')
    return out


@pytest.mark.parametrize('name', ANNOTATED)
def test_every_public_function_is_annotated(name):
    module = __import__(name)
    assert not missing_hints(module), f'{name}: {missing_hints(module)}'


@pytest.mark.parametrize('name', ANNOTATED)
def test_the_hints_are_never_evaluated(name):
    """PEP 563: with the future import every hint stays a string, so an
    import used only in a hint (pandas under TYPE_CHECKING) costs nothing."""
    text = (ROOT / 'src' / f'{name}.py').read_text(encoding='utf-8')
    assert 'from __future__ import annotations' in text


def test_an_unannotated_function_is_found():
    """Synthetic, so the failing branch stays reachable."""
    import types
    m = types.ModuleType('fake')
    exec('def f(a, b: int) -> int:\n    return b\ndef g(x: int):\n    return x\n', m.__dict__)
    for f in (m.f, m.g):
        f.__module__ = 'fake'
    assert missing_hints(m) == ['f(a)', 'g -> return']
