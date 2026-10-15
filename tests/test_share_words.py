"""What the share button and the shared view say (Stage 77 items 18 and 19, the 2026-10-13 UI/UX audit's copy fixes 7 and 8).

Run with: pytest tests/test_share_words.py -v
"""
import json
import re
import shutil
import subprocess

import pytest

from src.core.template_parts import JOINED_TEMPLATE

NODE = shutil.which('node')


def call(name, *args):
    if not NODE:
        pytest.skip('node not available')
    js = JOINED_TEMPLATE.read_text(encoding='utf-8')
    fn = re.search(rf'^function {name}\(.*?(?:\}}$|\n\}}\n)', js, re.S | re.M)
    assert fn, f'{name} is not findable -- re-anchor this guard'
    code = fn.group(0) + f'\nconsole.log(JSON.stringify({name}(...{json.dumps(list(args))})));'
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_the_share_button_says_the_link_is_copied_and_counts_right():
    assert call('copiedText', 1) == 'Link copied · 1 pick'
    assert call('copiedText', 4) == 'Link copied · 4 picks'
    assert 'flash(copiedText(encoded.picked))' in JOINED_TEMPLATE.read_text(encoding='utf-8')
