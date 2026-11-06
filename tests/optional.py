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
import shutil

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


def require_tool(name: str) -> str:
    """The path of the command-line tool `name`, or skip (locally) / fail (CI).

    Stage 96 item 48 (audit 7, T11): about a hundred tests each carried
    `if not NODE: pytest.skip('node not available')`, so a CI image without
    node would have skipped every page-script test green. CI installs node
    (run-tests.yml, setup-node), so there a missing tool is a failure."""
    path = shutil.which(name)
    if path is None:
        if in_ci():
            pytest.fail(f'{name} is not on PATH in CI, where the workflow installs it', pytrace=False)
        pytest.skip(f'{name} is not on PATH')
    return path
