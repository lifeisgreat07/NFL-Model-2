"""Plus Jakarta Sans is self-hosted: inlined at build time, no font host.

Stage 12 (CLAUDE.md, "Stage 12 - Self-hosted assets and browser checks in
CI"). The page loaded its face from Google Fonts at runtime. CLAUDE.md's
webfont traps record why that matters beyond privacy: a render without the
face can find NO defect where one exists, so every later browser check rests
on the font actually being there.

Mark approved exactly four files on 2026-09-26 (latin and latin-ext; the
normal face is one variable file for 400-800, plus italic 500). These tests
hold the files to the manifest's hashes, the built rules to the files, the
licence to the fonts, and the page to having no font host left in it.

Run with: pytest tests/test_self_hosted_font.py -v
"""
import base64
import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from src.pipeline import generate_dashboard as gd  # noqa: E402
from src.pipeline.template_parts import JOINED_TEMPLATE  # noqa: E402

FONT_DIR = ROOT / 'assets' / 'fonts'
TEMPLATE = JOINED_TEMPLATE
APPROVED = {  # file -> bytes, as approved and downloaded 2026-09-26
    'plus-jakarta-sans-latin-normal.woff2': 27348,
    'plus-jakarta-sans-latin-ext-normal.woff2': 21728,
    'plus-jakarta-sans-latin-italic.woff2': 13104,
    'plus-jakarta-sans-latin-ext-italic.woff2': 11512,
}


@pytest.fixture(scope='module')
def manifest():
    return json.loads((FONT_DIR / 'manifest.json').read_text(encoding='utf-8'))


def test_exactly_the_approved_files_are_committed(manifest):
    on_disk = {p.name for p in FONT_DIR.glob('*.woff2')}
    assert on_disk == set(APPROVED), f'font files differ from the approved four: {sorted(on_disk)}'
    assert {f['file']: f['bytes'] for f in manifest['files']} == APPROVED


def test_every_file_matches_its_recorded_hash(manifest):
    """A binary damaged in transit (the file bridge has done it to PNGs)
    still has the right name and roughly the right size."""
    for f in manifest['files']:
        data = (FONT_DIR / f['file']).read_bytes()
        assert len(data) == f['bytes'], f['file']
        assert hashlib.sha256(data).hexdigest() == f['sha256'], f['file']
        assert data[:4] == b'wOF2', f"{f['file']} is not a WOFF2 file"


def test_the_licence_travels_with_the_fonts():
    text = (FONT_DIR / 'OFL.txt').read_text(encoding='utf-8')
    assert 'SIL OPEN FONT LICENSE' in text.upper()
    assert 'Plus Jakarta Sans' in text


@pytest.fixture(scope='module')
def rules():
    return gd.font_faces_css()


def test_each_file_becomes_one_rule_carrying_exactly_its_bytes(rules, manifest):
    blocks = re.findall(r'@font-face\{.*?\}', rules)
    assert len(blocks) == len(manifest['files']) == 4
    for f in manifest['files']:
        data = (FONT_DIR / f['file']).read_bytes()
        encoded = base64.b64encode(data).decode('ascii')
        match = [b for b in blocks if encoded in b]
        assert len(match) == 1, f"{f['file']} is not inlined exactly once"
        assert f"font-style:{f['style']};" in match[0]
        assert f"unicode-range:{f['unicode_range']};" in match[0]


def test_the_normal_face_covers_every_weight_the_page_uses(rules):
    """The page sets 400 to 800; the variable file serves that whole range.
    A single declared weight would make the browser synthesise bold."""
    normal = [b for b in re.findall(r'@font-face\{.*?\}', rules) if 'font-style:normal' in b]
    assert normal and all('font-weight:400 800;' in b for b in normal)


def test_a_damaged_font_stops_the_build(tmp_path, manifest):
    for f in manifest['files']:
        (tmp_path / f['file']).write_bytes((FONT_DIR / f['file']).read_bytes())
    (tmp_path / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    victim = tmp_path / manifest['files'][0]['file']
    data = bytearray(victim.read_bytes())
    data[len(data) // 2] ^= 0xFF  # a flip, so it cannot equal the original byte
    victim.write_bytes(bytes(data))
    with pytest.raises(ValueError, match='does not match'):
        gd.font_faces_css(tmp_path)


def test_the_page_asks_no_font_host_for_anything():
    src = TEMPLATE.read_text(encoding='utf-8')
    code = re.sub(r'<!--.*?-->', '', src, flags=re.S)
    for host in ('fonts.googleapis.com', 'fonts.gstatic.com'):
        assert host not in code, f'the page still loads from {host}'
    assert '__FONT_FACES__' in code, 'the template no longer asks for the inlined faces'
