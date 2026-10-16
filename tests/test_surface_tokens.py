"""A surface wears a surface token (Stage 78 item 42, the 2026-10-13 UI/UX audit's C3).

.agent-stat, the Methodology page's section links (.page-jump a),
.status-planned, the undo toast and .tag-neutral were filled with
var(--border), a token meant for lines (measured 2026-10-14: each drew the
border colour, rgb(35, 40, 48) dark and rgb(228, 231, 235) light). They use
--surface-2 now (.tag-neutral since Stage 78 item 37). A bar's track is a
drawn line, not a surface, and keeps the border token; the More sheet's
items are Stage 78 item 43's.

Run with: pytest tests/test_surface_tokens.py -v
"""
import re

from src.core.template_parts import every_stylesheet

#: Rules that may fill with the border token: tracks and marks drawn as lines.
TRACKS = {'::-webkit-scrollbar-thumb', '.streak-cell', '.srs-bar-track', '.why-bar-track', '.score-track',
          '.tele-bar', '.dive-game-head:hover', '.bnav-more-item', '.ts-bar'}


def border_fills():
    out = []
    for name, css in every_stylesheet():
        body = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
        for sel, b in re.findall(r'([^{}]+)\{([^{}]*)\}', body):
            if re.search(r'(?<![\w-])background\s*:\s*var\(--border\)', b):
                out.append(' '.join(sel.split()))
    return out


def test_only_tracks_fill_with_the_border_token():
    stray = [s for s in border_fills() if s not in TRACKS]
    assert not stray, f'a surface filled with the border token: {stray}'


def test_the_named_surfaces_wear_surface_2():
    css = re.sub(r'/\*.*?\*/', '', dict(every_stylesheet())['the NFL template'], flags=re.S)
    for sel in ('.agent-stat', '.page-jump a', '.status-planned', '.undo-toast'):
        rule = [b for s, b in re.findall(r'([^{}]+)\{([^{}]*)\}', css) if ' '.join(s.split()) == sel]
        assert rule and any('background:var(--surface-2)' in b for b in rule), sel
