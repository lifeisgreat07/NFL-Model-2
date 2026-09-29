"""One matchup title, built in one place, styled two ways.

Two functions render a `.game-card`: renderGames() for the Week Board and
renderPicksGrid() for My Picks. Both hand-built the title
`AWAY <span class="at-symbol">at</span> HOME`. That is why the `@` separator
survived on My Picks after being changed everywhere else -- one edit, two
sites, one of them missed, and the diff looked complete either way.

What is NOT unified is appearance, and that is deliberate. On My Picks the two
pick buttons already carry both team abbreviations, so the title is a quiet
label rather than a heading. Measured on the rendered page before the change:
11px, weight 400, --text-2, .03em, 19px from the card top, 30px to the
buttons, card height 263px. Measured after: identical. Whether a quiet title
is the right design there is a Stage 9/10 question about the card; a refactor
that answered it on the way past would be the undisclosed-scope change Booth
has flagged on this repository before.

So the guard is: the markup may exist in exactly one place, both render paths
must use it, and the variant must keep its own box model rather than
inheriting the heading's flex layout.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'src' / 'dashboard_template.html'
HARNESS = Path(__file__).parent / 'matchup_header_harness.js'
NODE = shutil.which('node')


@pytest.fixture(scope='module')
def source():
    return TEMPLATE.read_text(encoding='utf-8')


def test_the_matchup_title_is_built_in_exactly_one_place(source):
    """The defect itself, asserted as a count.

    A second construction site is invisible in review: both copies read
    correctly, and a change to one of them leaves the other looking like code
    nobody touched rather than code that should have been touched.
    """
    sites = source.count('<span class="at-symbol">')
    assert sites == 1, (
        f'the matchup title is constructed in {sites} places. It must be one: '
        'the `@`-to-`at` change was made in one of two copies and the missed '
        'one shipped. Call matchupHeader() instead of writing the markup.')


def test_both_render_paths_use_the_helper(source):
    """Naming the coverage rather than asserting a protection exists.

    "The title is built in one place" is satisfied by a helper nobody calls.
    This repository has shipped exactly that -- src/collect_agent_log.py was
    written, tested and never invoked -- so the two call sites are enumerated
    here instead of trusted.
    """
    for call, where in ((r'\$\{matchupHeader\(g\)\}', 'the Week Board'),
                        (r"\$\{matchupHeader\(g, 'quiet'\)\}", 'My Picks')):
        assert re.search(call, source), (
            f'{where} no longer calls matchupHeader(). If its card lost its '
            'title that is a defect; if it went back to building its own, '
            'that is the drift this file exists to stop.')


def test_the_quiet_variant_keeps_its_own_box_model(source):
    """The one thing a shared class could silently change.

    `.matchup-header` is a flex container with an 8px gap, so its words are
    flex items. The span this replaced on My Picks was ordinary inline text
    with single spaces. Inheriting flex would have widened "NE at SEA" with
    nobody deciding to -- a visual change riding along inside a refactor.
    """
    m = re.search(r'\.matchup-header\.quiet\{([^}]*)\}', source)
    assert m, '.matchup-header.quiet is gone; My Picks now renders a heading'
    assert 'display:block' in m.group(1).replace(' ', ''), (
        'the quiet variant no longer overrides display, so it inherits '
        '.matchup-header\'s flex layout and its 8px inter-word gap')


@pytest.fixture(scope='module')
def rendered():
    """What the shipped function actually returns, executed rather than read."""
    if not NODE:
        pytest.skip('node not available')
    r = subprocess.run([NODE, str(HARNESS)], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    assert r.returncode == 0, f'harness failed:\n{r.stderr}'
    import json
    out = json.loads(r.stdout)
    assert 'fatal' not in out, out['fatal']
    return out



LOGO = ('<img class="card-end-logo" src="https://a.espncdn.com/i/teamlogos/nfl/500/{code}.png" '
        'alt="" loading="lazy" onerror="this.style.display=\'none\'">')


def test_the_helper_renders_both_teams_and_the_separator(rendered):
    """The title is text: the logos moved to the ends of Model B's bar on
    2026-09-28, where Mark preferred them."""
    assert rendered['board'] == (
        '<div class="matchup-header">NE <span class="at-symbol">at</span> SEA</div>'), (
        'the Week Board title changed shape. If that was intended, it is now '
        'one edit rather than two -- which is the point -- but it is still a '
        'visible change and belongs in the description.')


def test_the_variant_adds_a_class_and_nothing_else(rendered):
    """A variant that could alter the text would reintroduce the defect in a
    subtler form: one construction site producing two different sentences."""
    assert rendered['picks'] == (
        '<div class="matchup-header quiet">NE <span class="at-symbol">at</span> SEA</div>')
    assert rendered['picks'].replace(' quiet', '') == rendered['board'], (
        'the quiet variant changes more than the class list')


def test_the_bar_ends_carry_the_logo_beside_the_abbreviation(rendered, source):
    """Each end of the bar is the logo, then the abbreviation, and the board's
    card draws both ends through barTeam()."""
    assert rendered['bar'] == ('<span class="card-end-team">' + LOGO.format(code='ne') + 'NE</span>')
    for side in ('away', 'home'):
        assert '${barTeam(g.' + side + ')}</span>' in source, side


def test_a_logo_is_decorative_and_falls_back_to_the_name(rendered):
    """alt="" because the abbreviation beside it is the name; a screen reader
    would otherwise read every team twice. onerror hides a logo ESPN will not
    serve, leaving the abbreviation -- the fallback every other logo here has,
    and what the browser-checks job relies on with ESPN blocked."""
    imgs = re.findall(r'<img [^>]*>', rendered['bar'])
    assert len(imgs) == 1
    assert ' alt=""' in imgs[0], imgs[0]
    assert 'onerror="this.style.display=\'none\'"' in imgs[0], imgs[0]
    assert '<img' not in rendered['board'], 'the header has logos again as well as the bar'


def test_the_logo_is_twenty_pixels(source):
    """The size the Stage 8 restyle set for logos returning to the core UI."""
    m = re.search(r'\.card-end-logo\{([^}]*)\}', source)
    assert m, '.card-end-logo has no rule'
    rule = m.group(1).replace(' ', '')
    assert 'width:20px' in rule and 'height:20px' in rule, rule


def test_on_a_phone_the_logo_stacks_above_the_abbreviation(source):
    """Side by side, logo and abbreviation took about 30px from each end of
    the probability line on a 375px phone, below the 176px CARD_NEAR was
    measured on; stacked, the ends are no wider than the abbreviation."""
    m = re.search(r'@media \(max-width:767px\)\{\s*\.card-end-team\{([^}]*)\}', source)
    assert m, 'the phone rule for .card-end-team is gone'
    assert 'flex-direction:column' in m.group(1).replace(' ', '')


def test_no_variant_leaves_the_class_list_clean(rendered):
    """A trailing space in a class attribute is harmless until something
    matches on `class="matchup-header"` exactly -- which the guard above does."""
    assert rendered['undefinedVariant'] == rendered['board']
    assert rendered['emptyVariant'] == rendered['board']
