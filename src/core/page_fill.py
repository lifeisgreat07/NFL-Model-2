"""What the home, NHL and NBA pages fill their templates with (Stage 68 item 24).

Each of the three builds carried its own copy of `safe_json` and
`font_faces_css`, and the NHL's and NBA's scripts their own `escapeHtml`
(the 2026-10-09 audit, E17). One of each lives here now.

The NFL's board keeps its own `safe_json` (src/sports/nfl/generate_dashboard.py):
it passes json.dumps's arguments through and its fills are ASCII-escaped,
which tests/test_safe_json_fills.py holds; it uses this module's
`font_faces_css`, whose output was already the same.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
FONT_DIR = ROOT / 'assets' / 'fonts'
#: The escape helper the NHL's and NBA's scripts share, included ahead of
#: each sport's own script in the same <script> element.
ESCAPE_JS = Path(__file__).with_name('escape.js')


def safe_json(obj: Any) -> str:
    """JSON for a <script> block: nothing in it can close the tag."""
    return (json.dumps(obj, separators=(',', ':'), ensure_ascii=False)
            .replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026'))


def font_faces_css(font_dir: Path = FONT_DIR) -> str:
    """@font-face rules for the self-hosted Plus Jakarta Sans, as data URIs.

    Every file is checked against the SHA-256 in assets/fonts/manifest.json
    before it is inlined. A mismatch raises: a corrupted font does not fail
    loudly in a browser, it silently falls back (Stage 12).
    """
    manifest = json.loads((font_dir / 'manifest.json').read_text(encoding='utf-8'))
    rules = []
    for f in manifest['files']:
        data = (font_dir / f['file']).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != f['sha256']:
            raise ValueError(f"{f['file']}: sha256 {digest} does not match the "
                             f"manifest's {f['sha256']}")
        weight = '400 800' if f['style'] == 'normal' else '500'
        rules.append(
            "@font-face{font-family:'Plus Jakarta Sans';"
            f"font-style:{f['style']};font-weight:{weight};font-display:swap;"
            f"src:url(data:font/woff2;base64,{base64.b64encode(data).decode('ascii')}) format('woff2');"
            f"unicode-range:{f['unicode_range']};}}")
    return '\n'.join(rules)
