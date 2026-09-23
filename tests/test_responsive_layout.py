"""
Stage 10's mobile pass, held (2026-09-23).

THE DEFECT. At 320px the Week Board and My Picks scrolled sideways: the card
grid was `minmax(340px, 1fr)`, the content box on a 320px phone is 296px, and
a bare minimum in a grid track is a floor the column cannot go under. Model
Lab's reliability plot did the same with `min-width:300px`. Both are the
same shape -- a hard pixel floor wider than the narrowest phone's content
box -- so the rule is stated about the SHAPE, over the whole template, not
about the two selectors that happened to have it.

THE BREAKPOINTS. The sidebar gave way to the bottom nav at 820px, which left
a 236px sidebar squeezing the content box from 821 to about 1065, and the
ratings table clipped behind its scroller across that band. The nav now
switches at 1079px and the full team names drop at 1180px. The template
carries a comment listing every viewport breakpoint and what changes at it;
these tests hold that comment to the media queries that actually exist, so a
new breakpoint cannot arrive undocumented and a documented one cannot quietly
move.

A browser is what proves the layout; no CI job here has one. So the rendered
widths are a process note in the PR, and what is guarded here is the premise
each fix rests on, checked over the real template and over synthetic inputs
that keep every branch of each rule reachable.

Run with: pytest tests/test_responsive_layout.py -v
"""
import re
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).parent.parent / 'src' / 'dashboard_template.html'
NARROWEST_PHONE = 320


def strip_comments(src):
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    return re.sub(r'<!--.*?-->', '', src, flags=re.S)


def media_blocks(src):
    """[(max_width, body)] for every `@media (max-width:Npx){...}` block.

    Bodies are read by brace depth, so nested rules stay inside their query.
    """
    out = []
    for m in re.finditer(r'@media\s*\(\s*max-width\s*:\s*(\d+)px\s*\)\s*\{', src):
        depth, i = 1, m.end()
        while depth and i < len(src):
            depth += {'{': 1, '}': -1}.get(src[i], 0)
            i += 1
        out.append((int(m.group(1)), src[m.end():i - 1]))
    return out


def phone_content_box(src):
    """The content width on the narrowest phone: viewport minus <main>'s
    horizontal padding in the narrowest max-width query that sets it."""
    candidates = []
    for width, body in media_blocks(strip_comments(src)):
        m = re.search(r'(?<![\w-])main\s*\{[^}]*padding\s*:\s*(\d+)px\s+(\d+)px', body)
        if m:
            candidates.append((width, int(m.group(2))))
    assert candidates, "found no <main> padding inside any max-width query"
    _, gutter = min(candidates)
    return NARROWEST_PHONE - 2 * gutter


def hard_floors(src, limit):
    """Every bare pixel floor wider than `limit`: a `minmax(Npx` grid track
    minimum, or a `min-width:Npx` declaration. `min(Npx, 100%)` is not a
    bare floor and is not matched; neither is `@media (min-width:...)`."""
    src = strip_comments(src)
    found = []
    for rx in (r'minmax\(\s*(\d+)px', r'(?<!\()min-width\s*:\s*(\d+)px'):
        for m in re.finditer(rx, src):
            if int(m.group(1)) > limit:
                line = src.count('\n', 0, m.start()) + 1
                found.append((int(m.group(1)), line, src[max(0, m.start() - 40):m.end()].strip()))
    return found


def documented_breakpoints(src):
    m = re.search(r'-{5,} Breakpoints -{5,}(.*?)\*/', src, flags=re.S)
    assert m, "the Breakpoints comment block is gone from the template"
    return {int(w) for w in re.findall(r'^\s*(\d+)px\s', m.group(1), flags=re.M)}


def viewport_breakpoints(src):
    return {w for w, _ in media_blocks(strip_comments(src))}


def query_width_containing(src, needle):
    """The max-width of the one media query whose body contains `needle`."""
    hits = [w for w, body in media_blocks(strip_comments(src))
            if needle in re.sub(r'\s+', '', body)]
    assert len(hits) == 1, f"{needle!r} is in {len(hits)} media queries, expected 1"
    return hits[0]


@pytest.fixture(scope='module')
def src():
    return TEMPLATE.read_text(encoding='utf-8')


# ---- the phone floor --------------------------------------------------------

def test_the_narrowest_phone_content_box_is_296(src):
    """The figure every floor below is measured against, derived rather than
    typed: 320 minus the 12px gutters the small-phone query gives <main>."""
    assert phone_content_box(src) == 296


def test_no_hard_width_floor_wider_than_a_phone(src):
    floors = hard_floors(src, phone_content_box(src))
    assert not floors, (
        "a bare pixel minimum wider than a 320px phone's content box makes the "
        "page scroll sideways there. Write it as min(Npx, 100%):\n"
        + "\n".join(f"  line {ln}: {px}px  ...{ctx}" for px, ln, ctx in floors))


@pytest.mark.parametrize('css, flagged', [
    ('.g{grid-template-columns:repeat(auto-fit, minmax(340px, 1fr));}', [340]),
    ('.g{grid-template-columns:repeat(auto-fit, minmax(min(340px, 100%), 1fr));}', []),
    ('.p{min-width:300px;}', [300]),
    ('.p{min-width:min(300px, 100%);}', []),
    ('.p{min-width:240px;}', []),
    ('@media (min-width:900px){ .x{color:red;} }', []),
    ('/* minmax(400px, 1fr) in a comment */', []),
])
def test_the_floor_rule_over_synthetic_css(css, flagged):
    assert [px for px, _, _ in hard_floors(css, 296)] == flagged


# ---- the breakpoints --------------------------------------------------------

def test_every_breakpoint_is_documented_and_every_documented_one_exists(src):
    assert documented_breakpoints(src) == viewport_breakpoints(src), (
        "the Breakpoints comment in the template and its @media (max-width) "
        "queries disagree. Document a new breakpoint there, or delete a "
        "retired one from the comment.")


def test_the_toast_lifts_exactly_where_the_bottom_nav_appears(src):
    """The undo toast sits 90px up so the bottom nav does not cover it. Keyed
    to a different width than the nav, it either floats over empty space or
    hides behind the bar -- which is what 900 against 820 used to do."""
    nav = query_width_containing(src, '.bottom-nav{display:block;}')
    toast = query_width_containing(src, '.undo-toast{bottom:')
    assert toast == nav


def test_full_team_names_are_gone_wherever_the_bottom_nav_is(src):
    """The names drop at a width at least as wide as the nav switch, so no
    width shows the bottom nav with the names still costing the table."""
    nav = query_width_containing(src, '.bottom-nav{display:block;}')
    names = query_width_containing(src, '.team-full{display:none;}')
    assert names >= nav


def test_the_sidebar_is_gone_where_the_bottom_nav_appears(src):
    nav = query_width_containing(src, '.bottom-nav{display:block;}')
    sidebar = query_width_containing(src, '.sidebar{display:none;}')
    assert sidebar == nav


def test_the_nav_query_finder_is_not_blind(src):
    """Vacuity guard: the three rules above compare widths the finder
    returns, and a finder matching nothing would fail loudly -- but one
    matching the WRONG block would not. Pin what it must find today."""
    assert query_width_containing(src, '.bottom-nav{display:block;}') == 1079
    assert query_width_containing(src, '.team-full{display:none;}') == 1180
    assert len(viewport_breakpoints(src)) >= 4
