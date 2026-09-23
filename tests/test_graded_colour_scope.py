"""
Stage 9's colour decisions, held (2026-09-22).

THE RULE. --good / --warn (the graded pair, aliased --graded-correct /
--graded-wrong) mean one thing: a scored pick was right, or wrong. Before
Stage 9 they were also painted on an experiment's ACCEPT/REJECT pill, the
"Built" pill, Methodology's numbered gaps, a team's W/L on Team Deep-Dive,
a rating moving up or down, the Model Lab "Current." version dot and the
incident labels on the reliability page -- so green meant "correct", "shipped",
"current", "went up" and "won" at once, and red meant "wrong", "rejected" and
"lost". The design record's rule (docs/design/STAGE8-DESIGN.md, "a colour that
means correct must never appear on a game that has not happened") was being
broken nine ways, none of them on a game.

WHAT EACH THING NOW LOOKS LIKE -- the Stage 9 queue item, decided:
  * the model was wrong  -> --warn plus a word or a cross, ONLY on a scored pick
  * a flagged game       -> the --accent left border (.game-card.has-flag)
  * confidence           -> no hue at all: the bar's length and the number
  * a decision label     -> the neutral pill; the word is the label
  * the Net Rating sign  -> the neutral --text-3 fill; the zero line and the
                            bar's direction say which side, the number prints

Every consumer of the graded pair is enumerated from the template and
compared with the list below as a SET, and the rule is also run over a
synthetic template so both of its branches stay alive.

Run with: pytest tests/test_graded_colour_scope.py -v
"""
import re
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).parent.parent / 'src' / 'dashboard_template.html'

GRADED_TOKENS = ('--good', '--good-dim', '--warn', '--warn-dim',
                 '--graded-correct', '--graded-correct-soft',
                 '--graded-wrong', '--graded-wrong-soft')

#: Every place allowed to wear the graded pair, and the scored pick behind it.
SCORED_PICK_CONSUMERS = {
    '.streak-cell.win': 'a My Picks week the user won',
    '.streak-cell.loss': 'a My Picks week the user lost',
    '.streak-label.win': 'the My Picks streak label',
    '.streak-label.loss': 'the My Picks streak label',
    '.graded-tag.correct': 'a model pick on the Board, scored right',
    '.graded-tag.incorrect': 'a model pick on the Board, scored wrong',
    '.pick-badge.correct': "the user's pick, scored right",
    '.pick-badge.incorrect': "the user's pick, scored wrong",
    '.dive-tick': 'Team Deep-Dive: this model was right about this game',
    '.dive-cross': 'Team Deep-Dive: this model was wrong about this game',
}

_VAR = re.compile(r'var\((' + '|'.join(re.escape(t) for t in GRADED_TOKENS) + r')\)')


def strip_comments(src):
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    return re.sub(r'<!--.*?-->', '', src, flags=re.S)


def graded_consumers(src):
    """{selector-or-location: line} for every use of the graded pair.

    A CSS rule reports its selector. Anything else -- an inline style, a JS
    string -- reports 'inline:<text>', which is never on the allowed list.
    The :root alias line that defines --graded-* from --good/--warn is the
    definition, not a consumer, and is skipped.
    """
    out = {}
    for line in strip_comments(src).splitlines():
        if not _VAR.search(line):
            continue
        stripped = line.strip()
        if re.match(r'--graded-(correct|wrong)\s*:', stripped):
            continue
        m = re.match(r'([^{}<>]+)\{', stripped)
        if m and 'style=' not in stripped:
            for sel in m.group(1).split(','):
                out[sel.strip()] = stripped
        else:
            out['inline:' + stripped[:80]] = stripped
    return out


def violations(src):
    return {k: v for k, v in graded_consumers(src).items() if k not in SCORED_PICK_CONSUMERS}


def test_the_scan_finds_the_scored_pick_consumers():
    """Vacuity: a scan that finds nothing passes the rule below perfectly."""
    found = graded_consumers(TEMPLATE.read_text(encoding='utf-8'))
    assert '.graded-tag.correct' in found and '.dive-cross' in found, sorted(found)
    assert len(found) >= 8, sorted(found)


def test_graded_colours_appear_only_on_scored_picks():
    bad = violations(TEMPLATE.read_text(encoding='utf-8'))
    assert not bad, (
        'the graded pair is painted on something that is not a scored pick:\n  '
        + '\n  '.join(f'{k}: {v}' for k, v in bad.items())
        + '\nGreen means "this pick was right" and red "this pick was wrong". '
          'Use the neutral ramp and let the word say it.')


def test_every_listed_consumer_still_exists():
    """The other direction: an entry nothing uses is an excuse for nothing."""
    found = graded_consumers(TEMPLATE.read_text(encoding='utf-8'))
    gone = sorted(set(SCORED_PICK_CONSUMERS) - set(found))
    assert not gone, f'listed as graded consumers but not in the template: {gone}'


SYNTHETIC = """
  :root{ --graded-correct:var(--good); --graded-wrong:var(--warn); }
  .graded-tag.correct{color:var(--good);}
  .tag-good{background:var(--good-dim); color:var(--good);}
  /* .old-rule{color:var(--warn);} */
  <b style="color:var(--warn)">Claim made:</b>
"""


def test_the_rule_reports_a_decision_pill_and_an_inline_style():
    bad = violations(SYNTHETIC)
    assert '.tag-good' in bad
    assert any(k.startswith('inline:') for k in bad)
    assert '.graded-tag.correct' not in bad, 'an allowed consumer was reported'
    assert not any('old-rule' in k for k in bad), 'a commented-out rule was counted'


# ------------------------------------------------------------ Net Rating bar

def theme_hex(theme, token):
    src = TEMPLATE.read_text(encoding='utf-8')
    marker = ':root{' if theme == 'dark' else '[data-theme="light"]{'
    start = src.index(marker)
    block = src[start:src.index('\n  }', start)]
    m = re.search(re.escape(token) + r'\s*:\s*(#[0-9A-Fa-f]{6})', block)
    return m.group(1) if m else None


def luminance(h):
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_the_net_rating_fill_is_the_neutral_text_3():
    src = strip_comments(TEMPLATE.read_text(encoding='utf-8'))
    rule = re.search(r'\.srs-bar-fill\{[^}]*\}', src).group(0)
    assert 'background:var(--text-3)' in rule, (
        f'the Net Rating bar wears something other than the neutral fill: {rule}. '
        'Its sign is the zero line and the direction, not a hue (Stage 9).')
    assert 'accent' not in rule


@pytest.mark.parametrize('theme', ['dark', 'light'])
def test_the_net_rating_fill_clears_3_to_1_against_surface_and_track(theme):
    """WCAG 1.4.11: a graphical object needs 3:1 against what it sits on.

    --text-3 is --n6, the surface --n1 and the track --border (--n3).
    """
    fill, surface, track = (theme_hex(theme, t) for t in ('--n6', '--n1', '--n3'))
    assert fill and surface and track
    assert contrast(fill, surface) >= 3.0, (theme, fill, surface)
    assert contrast(fill, track) >= 3.0, (theme, fill, track)


def test_accent_strong_is_retired():
    src = strip_comments(TEMPLATE.read_text(encoding='utf-8'))
    assert '--accent-strong' not in src, (
        '--accent-strong is back. It was retired in Stage 9 with its one '
        'consumer; a new use needs a new colour-pair trace, not a revert.')


def test_model_lab_does_not_keep_a_second_version_history():
    """Model Lab carried a hand-written copy of VERSION_HISTORY that marked
    v2.4 "Current." in the graded green. What's Changed renders the real one."""
    src = strip_comments(TEMPLATE.read_text(encoding='utf-8'))
    assert 'class="version-item"' not in src and 'class="version-dot' not in src


def test_the_neutral_pill_is_neutral():
    """.tag-neutral carries decision labels and the game card's toss-up tag.
    It wore the accent until Stage 9; a toss-up is the absence of a lean."""
    src = strip_comments(TEMPLATE.read_text(encoding='utf-8'))
    for cls in ('.tag-neutral', '.status-done', '.status-planned'):
        rule = re.search(re.escape(cls) + r'\{[^}]*\}', src).group(0)
        assert 'accent' not in rule and not _VAR.search(rule), rule
    assert 'var(--text-2)' in re.search(r'\.tag-neutral\{[^}]*\}', src).group(0)
