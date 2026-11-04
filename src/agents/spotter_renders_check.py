"""Hold Spotter's pictures to what its renderer writes, before they are published.

Stage 82 item 6 (the 2026-11-02 review). Spotter's render job runs the pull
request's own `tests/browser/spotter_render.py`, so the folder it uploads is
whatever that code chose to write. The publish job then commits every `.png`
and `.json` in it to the `spotter-renders` branch with a write token, and the
reading job hands the folder to the model. Nothing checked that a `.png` was a
picture, or that the manifests said what the renderer says.

`.github/workflows/spotter.yml` runs this in its `vet` job, from a checkout of
the base, between the render and the publish; the publish waits for it. The
folder passes only when:

  * it holds regular files and nothing else, no more than a full render makes;
  * every name is a picture name the renderer writes
    (`<page>-<width>x<height>-<theme>-<label>.png`) or `renders-<label>.json`;
  * every picture is a PNG -- its signature, then its IHDR chunk -- exactly as
    wide as its viewport (the renderer's scale factor is 1), at least as tall,
    and no larger than MAX_BYTES or taller than MAX_HEIGHT;
  * both manifests exist and are lists of the renderer's two entry shapes,
    with exactly its keys and types, each entry's file named from its own
    fields and its byte count the file's;
  * every picture is named by exactly one manifest entry, and every entry's
    file exists.

Standard library only: the vet job installs nothing.

Usage (as the workflow runs it):
    python3 -m src.agents.spotter_renders_check RENDERS_DIR
Exit 0 with a one-line count, or 1 with every problem found.
"""
from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path
from typing import Any

#: The renderer's pages, sizes, themes and labels (tests/browser/spotter_render.py;
#: tests/test_spotter_renders_check.py holds these to it).
PAGES = ('home', 'nfl', 'nhl', 'nba')
VIEWPORTS = {'390x844': (390, 844), '1440x900': (1440, 900)}
THEMES = ('light', 'dark')
LABELS = ('head', 'base')

PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
#: A full-page picture of the longest page is a few megabytes; this is well past it.
MAX_BYTES = 15_000_000
#: In CSS pixels at scale 1: far longer than any page the site has.
MAX_HEIGHT = 50_000
#: Every page at every size and theme for both labels, and the two manifests.
MAX_FILES = len(PAGES) * len(VIEWPORTS) * len(THEMES) * len(LABELS) + len(LABELS)

PICTURE = re.compile(r'^(home|nfl|nhl|nba)-(390x844|1440x900)-(light|dark)-(head|base)\.png$')
MANIFEST = re.compile(r'^renders-(head|base)\.json$')
PICTURE_KEYS = frozenset({'page', 'label', 'viewport', 'theme', 'file', 'bytes', 'parked'})
MISSING_KEYS = frozenset({'page', 'label', 'missing'})


def png_size(data: bytes) -> tuple[int, int]:
    """(width, height) from a PNG's IHDR chunk; ValueError if it is not a PNG."""
    if data[:8] != PNG_SIGNATURE:
        raise ValueError('not a PNG: its first eight bytes are not the PNG signature')
    if len(data) < 24 or data[12:16] != b'IHDR' or struct.unpack('>I', data[8:12])[0] != 13:
        raise ValueError('not a PNG: no IHDR chunk after the signature')
    width, height = struct.unpack('>II', data[16:24])
    return width, height


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def check_entry(entry: Any, label: str, sizes: dict[str, int]) -> list[str]:
    """Problems with one manifest entry, for the manifest of `label`."""
    if not isinstance(entry, dict):
        return [f'an entry is a {type(entry).__name__}, not an object']
    keys = frozenset(entry)
    where = f"entry {entry.get('file') or entry.get('page')!r}"
    if keys == MISSING_KEYS:
        out = []
        if entry['missing'] is not True:
            out.append(f'{where}: "missing" is {entry["missing"]!r}, not true')
    elif keys == PICTURE_KEYS:
        out = []
        if entry['viewport'] not in VIEWPORTS:
            out.append(f'{where}: viewport {entry["viewport"]!r} is not one the renderer uses')
        if entry['theme'] not in THEMES:
            out.append(f'{where}: theme {entry["theme"]!r} is not one the renderer uses')
        expected = f"{entry['page']}-{entry['viewport']}-{entry['theme']}-{entry['label']}.png"
        if entry['file'] != expected:
            out.append(f'{where}: names {entry["file"]!r}, but its own fields make {expected!r}')
        elif entry['file'] not in sizes:
            out.append(f'{where}: no such picture in the folder')
        elif not _is_count(entry['bytes']) or entry['bytes'] != sizes[entry['file']]:
            out.append(f'{where}: says {entry["bytes"]!r} bytes, the file has {sizes[entry["file"]]}')
        if not _is_count(entry['parked']):
            out.append(f'{where}: "parked" is {entry["parked"]!r}, not a count')
    else:
        return [f'{where}: keys {sorted(keys)} are neither shape the renderer writes']
    if entry['page'] not in PAGES:
        out.append(f'{where}: page {entry["page"]!r} is not one the renderer knows')
    if entry['label'] != label:
        out.append(f'{where}: label {entry["label"]!r} in renders-{label}.json')
    return out


def check(renders: Path) -> list[str]:
    """Every problem with the folder, one line each; empty when it passes."""
    if not renders.is_dir():
        return [f'{renders} is not a folder']
    entries = sorted(renders.iterdir())
    problems: list[str] = []
    if len(entries) > MAX_FILES:
        problems.append(f'{len(entries)} entries, more than a full render makes ({MAX_FILES})')
    sizes: dict[str, int] = {}
    manifests: dict[str, Path] = {}
    for p in entries:
        if p.is_symlink() or not p.is_file():
            problems.append(f'{p.name}: not a regular file')
            continue
        is_manifest = MANIFEST.match(p.name)
        if is_manifest:
            manifests[is_manifest.group(1)] = p
            continue
        m = PICTURE.match(p.name)
        if not m:
            problems.append(f'{p.name}: not a name the renderer writes')
            continue
        size = p.stat().st_size
        sizes[p.name] = size
        if size > MAX_BYTES:
            problems.append(f'{p.name}: {size} bytes, more than {MAX_BYTES}')
            continue
        try:
            width, height = png_size(p.read_bytes()[:24])
        except ValueError as exc:
            problems.append(f'{p.name}: {exc}')
            continue
        want_w, want_h = VIEWPORTS[m.group(2)]
        if width != want_w:
            problems.append(f'{p.name}: {width} pixels wide, its viewport is {want_w}')
        if not want_h <= height <= MAX_HEIGHT:
            problems.append(f'{p.name}: {height} pixels tall, outside {want_h} to {MAX_HEIGHT}')
    named: list[str] = []
    for label in LABELS:
        path = manifests.get(label)
        if path is None:
            problems.append(f'renders-{label}.json is missing')
            continue
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (UnicodeDecodeError, ValueError) as exc:
            problems.append(f'{path.name}: not JSON ({exc})')
            continue
        if not isinstance(data, list):
            problems.append(f'{path.name}: a {type(data).__name__}, not a list of entries')
            continue
        for entry in data:
            problems += [f'{path.name}: {line}' for line in check_entry(entry, label, sizes)]
            if isinstance(entry, dict) and isinstance(entry.get('file'), str):
                named.append(entry['file'])
    for name in sorted(sizes):
        if named.count(name) != 1:
            problems.append(f'{name}: named by {named.count(name)} manifest entries, not one')
    return problems


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print('usage: python3 -m src.agents.spotter_renders_check RENDERS_DIR')
        return 2
    folder = Path(args[0])
    problems = check(folder)
    if problems:
        print(f'FAIL: the pictures are not what the renderer writes ({len(problems)} problems):')
        for line in problems:
            print(f'  {line}')
        return 1
    pictures = sum(1 for p in folder.iterdir() if p.suffix == '.png')
    print(f'OK: {pictures} pictures and both manifests, as the renderer writes them')
    return 0


if __name__ == '__main__':
    sys.exit(main())
