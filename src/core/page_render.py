"""One page renderer for the home, NFL, NHL and NBA pages (Stage 87 item 3).

Each page used to put itself together its own way: the NFL through
`template_parts.read_template`, the home, NHL and NBA pages through a chain of
`str.replace` calls, one per include, and each filled its placeholders and
looked for leftovers in its own words (the NHL and NBA for two named tokens,
the home page for any). Now every page is:

    assemble(directory, shared)   the shell, its includes joined by template_parts.join
    finish(template, fills)       comments stripped, placeholders filled, CSP hashed

`fill` refuses both ways: a fill for a placeholder the page does not have
(a renamed placeholder would otherwise fill nothing, silently), and a
placeholder left without a fill. It replaces every placeholder in one pass,
so text a fill puts on the page is never searched for a later placeholder.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

from src.core import csp
from src.core.page_comments import strip_page_comments
from src.core.template_parts import DIRECTIVE, join

#: A placeholder: two underscores, capitals, digits or underscores, two underscores.
PLACEHOLDER = re.compile(r'__[A-Z0-9_]+__')
SHELL = 'page.html'


def assemble(directory: Path, shared: Mapping[str, Path] | None = None) -> str:
    """`directory`/page.html with each include replaced by its part: from
    `shared` when it names the part, otherwise the file of that name in
    `directory`."""
    parts = dict(shared or {})

    def read_part(name: str) -> str:
        return (parts.get(name) or directory / name).read_text(encoding='utf-8')

    return join((directory / SHELL).read_text(encoding='utf-8'), read_part)


def fill(template: str, fills: Mapping[str, str]) -> str:
    """Every placeholder in `template` replaced by its fill, in one pass.

    Raises ValueError for a fill whose placeholder the template does not
    have, for a placeholder without a fill, and for an include directive
    still in the template."""
    tokens = set(PLACEHOLDER.findall(template))
    bad = [k for k in fills if not PLACEHOLDER.fullmatch(k)]
    if bad:
        raise ValueError(f'not placeholders: {sorted(bad)}')
    unknown = sorted(set(fills) - tokens)
    if unknown:
        raise ValueError(f'fills for placeholders the page does not have: {unknown}')
    left = sorted(tokens - set(fills)) + ([DIRECTIVE] if DIRECTIVE in template else [])
    if left:
        raise ValueError(f'unfilled placeholders: {left}')
    return PLACEHOLDER.sub(lambda m: fills[m.group(0)], template)


def finish(template: str, fills: Mapping[str, str]) -> str:
    """The page a visitor downloads: the template's comments stripped (before
    the fills, so no data is lexed; src/core/page_comments.py), every
    placeholder filled, then each inline script and style hashed into the
    content security policy (Stage 88 item 5)."""
    return csp.harden(fill(strip_page_comments(template), fills))
