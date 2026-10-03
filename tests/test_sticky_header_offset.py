"""Below 1080px a fitting table's sticky header sticks under the top bar.

Stage 30 item 2, from the 2026-09-29 re-audit. The top bar is sticky at
top:0 with z-index 40 below 1080px; a fitting table's header was sticky at
top:0 too, so once scrolled past it sat under the bar and nobody saw it.
The header's top is now the bar's measured height.

What is drawn is proven by tests/browser/check_page.py's "sticky" rule,
which needs a browser and runs in CI. This file holds what a static read can
check, so the fix cannot be undone by an ordinary tidy-up: the offset lives
in the under-1080 block, and the page writes the variable it reads.

Run with: pytest tests/test_sticky_header_offset.py -v
"""
import json
import re
import shutil
import subprocess

import pytest

from src.pipeline.template_parts import JOINED_TEMPLATE  # noqa: E402

TEMPLATE = JOINED_TEMPLATE
NODE = shutil.which('node')


def _css():
    """The template's CSS with comments blanked (an unclosed comment swallows
    the rules after it, and a test of the raw text still passes)."""
    text = TEMPLATE.read_text(encoding='utf-8')
    style = re.search(r'<style>(.*?)</style>', text, re.S)
    assert style, 'no <style> block in the template'
    return re.sub(r'/\*.*?\*/', '', style.group(1), flags=re.S)


def _media_block(css, query):
    """The bodies of every @media block whose query is exactly `query`,
    joined. There is more than one (the undo toast has its own one-line
    block), and reading only the first found nothing -- the vacuity guard
    below caught that on this file's first run."""
    bodies = []
    for m in re.finditer(re.escape('@media ' + query + '{'), css):
        i = m.end()
        depth = 1
        j = i
        while depth:
            depth += {'{': 1, '}': -1}.get(css[j], 0)
            j += 1
        bodies.append(css[i:j - 1])
    assert bodies, f'no "@media {query}" block'
    return '\n'.join(bodies)


def test_under_1080_the_header_sticks_below_the_bar():
    block = _media_block(_css(), '(max-width:1079px)')
    assert re.search(r'\.table-wrap\.fits thead th\{[^}]*top:var\(--topbar-h', block), (
        'below 1080px the fitting table header no longer sticks under the '
        'top bar; it will stick at top:0, under the bar, where nobody sees it')


def test_the_page_writes_the_bar_height_it_reads():
    """initTopbarHeight run in node against a fake bar and a fake
    ResizeObserver (Stage 35: this was a regex over its source). It must
    write --topbar-h from offsetHeight at load, write it again when the
    observer fires, and observe the BORDER box: offsetHeight is the border
    box, and the default content box does not fire when only the padding
    changes -- which is how the safe area (--safe-top) reaches the bar."""
    if not NODE:
        pytest.skip('node not available')
    text = TEMPLATE.read_text(encoding='utf-8')
    fn = re.search(r'\(function initTopbarHeight\(\)\{.*?\n\}\)\(\);', text, re.S)
    assert fn, 'initTopbarHeight() is gone or no longer runs at load'
    js = ("const written=[];let cb=null,opts=null;"
          "const bar={offsetHeight:52};"
          "const document={querySelector:s=>s==='.topbar'?bar:null,"
          "documentElement:{style:{setProperty:(k,v)=>written.push([k,v])}}};"
          "const window={addEventListener:()=>{}};"
          "class ResizeObserver{constructor(f){cb=f;}observe(el,o){opts=o===undefined?null:o;"
          "if(el!==bar)throw new Error('observes the wrong element');}}"
          + fn.group(0) +
          "bar.offsetHeight=64;if(cb)cb();"
          "process.stdout.write(JSON.stringify({written,opts,observed:cb!==null}));")
    r = subprocess.run([NODE, '-'], input=js, capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    got = json.loads(r.stdout)
    assert got['written'][0] == ['--topbar-h', '52px'], '--topbar-h is not the measured height at load'
    assert got['observed'], 'the height is measured once only; it changes when the title wraps'
    assert got['written'][-1] == ['--topbar-h', '64px'], 'a resize does not rewrite --topbar-h'
    assert got['opts'] == {'box': 'border-box'}, (
        f"the observer watches {got['opts'] or 'the content box'}; a padding-only change "
        '(the safe area) would not fire it')


def test_the_media_block_reader_finds_the_block():
    """Vacuity guard: the block reader must return the real block, not an
    empty or truncated string that every search above would fail on for
    the wrong reason."""
    block = _media_block(_css(), '(max-width:1079px)')
    assert '.topbar{' in block and '.bottom-nav{display:block;}' in block
