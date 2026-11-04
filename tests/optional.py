"""
Optional test dependencies: skip on a machine without them, fail in CI.

Stage 86 item 6 (the 2026-11-02 review). A guard that needs a tool the
suite does not always have (vulture, mypy, hypothesis, polars) used to skip
quietly wherever the tool was missing, including CI, so a dropped line in
requirements-dev.txt would turn the guard off with nothing red. CI sets
`CI=true`; there a missing tool is a failure, because requirements-dev.txt
installs every one of them. On Mark's PC or a fresh clone it is a skip that
says what to install.
"""
import importlib
import importlib.util
import os

import pytest


def in_ci() -> bool:
    return bool(os.environ.get('CI'))


def require(module: str, *, module_level: bool = False):
    """Import `module`, or skip (locally) / fail (CI) the calling test or module."""
    if importlib.util.find_spec(module) is None:
        why = f'{module} is not installed (pip install -r requirements-dev.txt)'
        if in_ci():
            pytest.fail(f'{module} is not installed in CI, where requirements-dev.txt installs it', pytrace=False)
        pytest.skip(why, allow_module_level=module_level)
    return importlib.import_module(module)
