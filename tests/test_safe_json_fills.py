"""No string that reaches the page can end its <script> element (Stage 23).

The 2026-09-28 audit reproduced it: the agent-log collector accepts a Booth
report from any GitHub account, a report's `implicates` and `head` are copied
into data/agent_log.json as written, and the generator put that file inside
the page's <script> with plain json.dumps, which leaves `</script>` alone. The
HTML parser ends a script at the first `</script` it sees, in a string or
not, so a comment on any issue could put markup on the published page.

The fix is one helper, generate_dashboard.safe_json(). The guards:

- the helper itself (no `<` survives, and the value still round-trips);
- the CLASS, not a list: every placeholder the template puts inside a
  <script> element must be filled through safe_json(), found by reading the
  template, so a new data fill is covered without anyone remembering this
  file (CLAUDE.md: "enumerate the class instead");
- a vacuity check that the scan finds the fills it must find;
- the whole build, with a payload in the agent log and in the release notes:
  the page keeps exactly the template's script elements and gains no image.
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from src.pipeline import generate_dashboard as gd
from src.pipeline.template_parts import JOINED_TEMPLATE

TEMPLATE = JOINED_TEMPLATE
GENERATOR = ROOT / 'src' / 'pipeline' / 'generate_dashboard.py'
PAYLOAD = '</script><img src=x onerror=alert(1)><!--<script>'


# ---------------------------------------------------------------------------
# The helper
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('value', [
    PAYLOAD,
    {'implicates': [PAYLOAD], 'head': PAYLOAD},
    ['a < b', '</SCRIPT >', '<!--'],
])
def test_safe_json_leaves_no_angle_bracket_and_round_trips(value):
    out = gd.safe_json(value, indent=2)
    assert '<' not in out, f'a `<` survived: {out!r}'
    assert json.loads(out) == value, 'the escape changed the value'


def test_safe_json_passes_its_arguments_through():
    assert gd.safe_json({'a': 1}) == '{"a": 1}'
    assert gd.safe_json({'a': 1}, indent=2) == json.dumps({'a': 1}, indent=2)


# ---------------------------------------------------------------------------
# Every fill inside a script, found from the template
# ---------------------------------------------------------------------------

def script_placeholders(template_text):
    """Placeholders (`__NAME__`) that sit between <script> and </script>."""
    found = set()
    for body in re.findall(r'<script\b[^>]*>(.*?)</script>', template_text, re.S | re.I):
        found.update(re.findall(r'__[A-Z][A-Z0-9_]*__', body))
    return found


def test_the_scan_finds_the_fills_it_must_find():
    """A broken scan fails open: an empty set would pass the check below."""
    found = script_placeholders(TEMPLATE.read_text(encoding='utf-8'))
    for must in ('__AGENT_LOG_JSON__', '__WEEKS_JSON__', '__TEAMS_JSON__',
                 '__VERSION_HISTORY_JSON__', '__MODEL_VERSION__'):
        assert must in found, f'the template scan did not find {must}'


def test_every_fill_inside_a_script_goes_through_safe_json():
    found = script_placeholders(TEMPLATE.read_text(encoding='utf-8'))
    src = GENERATOR.read_text(encoding='utf-8')
    unsafe = [p for p in sorted(found)
              if not re.search(rf"html\s*=\s*(?:html|template)\.replace\(\s*'{p}',\s*safe_json\(", src)]
    assert not unsafe, (
        f'{unsafe} sit inside a <script> but are not filled through safe_json(); '
        'a `</script` in their data would end the script')


# ---------------------------------------------------------------------------
# The whole build, with a payload in it
# ---------------------------------------------------------------------------

class _Tags(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.scripts = 0
        self.imgs = []

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.scripts += 1
        elif tag == 'img':
            self.imgs.append(dict(attrs))


def _tags(text):
    p = _Tags()
    p.feed(text)
    return p


def test_a_payload_in_the_data_stays_data(tmp_path, monkeypatch):
    forged = {'summary': {'audits_total': 1}, 'generated_utc': '2026-09-28T00:00:00Z',
              'audits': [{'pr': 999, 'head': PAYLOAD, 'implicated': [PAYLOAD]}]}
    monkeypatch.setattr(gd, 'load_agent_log', lambda: forged)
    notes = [dict(v, headline=PAYLOAD) for v in gd.VERSION_HISTORY[:1]] + list(gd.VERSION_HISTORY[1:])
    monkeypatch.setattr(gd, 'VERSION_HISTORY', notes)
    monkeypatch.setattr(gd, 'OUTPUT_PATH', tmp_path / 'index.html')
    monkeypatch.setattr(gd, 'DIST_DIR', tmp_path / 'dist')
    monkeypatch.setitem(sys.modules, 'generate_picks_pdf', None)  # no PDFs: faster
    gd.main()

    built = (tmp_path / 'index.html').read_text(encoding='utf-8')
    template = TEMPLATE.read_text(encoding='utf-8')
    assert _tags(built).scripts == _tags(template).scripts, (
        'the built page has a different number of <script> elements than the '
        'template: a string in the data opened or closed one')
    def onerror_imgs(text):
        return len([i for i in _tags(text).imgs if 'onerror' in i])
    assert onerror_imgs(built) == onerror_imgs(template), (
        'a string in the data became an <img> with an onerror handler')
    assert '\\u003c/script>\\u003cimg' in built, (
        'the payload is not in the page as escaped data, so this test proved nothing')
