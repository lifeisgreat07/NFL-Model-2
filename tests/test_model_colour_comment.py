"""The colour figures in the model-identity comment must match the script.

Stage 11 put five measured numbers into a permanent source comment: how far
Model A's dot sits from the pick tick in each theme, under normal vision and
under red-green CVD, and how far apart the chart series are.

This repository has been here before. PR #52 shipped "115 of 992 team/theme
pairs ... 15 effectively identical" as a source comment; Booth re-ran the
stated method and got 71 and 9, an independent re-derivation got 70 and 9, and
the number had been wrong in the code for as long as nobody checked. A comment
is not executable. These tests make this one executable.

src/verify_model_colours.py computes the figures from the tokens as they
actually are in the template, so the pair cannot drift: change the palette and
these fail rather than the comment quietly becoming false.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'src' / 'dashboard_template.html'
sys.path.insert(0, str(ROOT / 'src'))


@pytest.fixture(scope='module')
def measured():
    import verify_model_colours as m
    return m.measure()


@pytest.fixture(scope='module')
def comment():
    """The block comment that introduces .model-chip."""
    src = TEMPLATE.read_text(encoding='utf-8')
    m = re.search(r'/\* -+ Naming a model in prose -+.*?\*/', src, re.S)
    assert m, 'the model-identity comment is missing from the template'
    return m.group(0)


def test_the_prose_pair_distance_is_what_the_script_computes(measured, comment):
    """The defect the change exists for: two blues a reader cannot tell apart."""
    _, _, normal, worst = measured['dark'][('--series-a', '--accent')]

    m = re.search(r'measured ([\d.]+) dE00 apart', comment)
    assert m, 'the comment no longer states the measured prose-pair distance'
    assert abs(float(m.group(1)) - normal) < 0.05, (
        f'comment says {m.group(1)} dE00; src/verify_model_colours.py '
        f'computes {normal:.1f}')

    m2 = re.search(r'([\d.]+) under red-green CVD', comment)
    assert m2, 'the comment no longer states the CVD figure for that pair'
    assert abs(float(m2.group(1)) - worst) < 0.05, (
        f'comment says {m2.group(1)} under CVD; computed {worst:.1f}')


def test_the_chart_pair_distance_is_what_the_script_computes(measured, comment):
    """The comparison that makes the defect legible: the charts got it right."""
    _, _, normal, _worst = measured['dark'][('--series-a', '--series-b')]
    m = re.search(r'charts drew the same pair ([\d.]+) apart', comment)
    assert m, 'the comment no longer states the chart-pair distance'
    assert abs(float(m.group(1)) - normal) < 0.05, (
        f'comment says the charts draw them {m.group(1)} apart; computed '
        f'{normal:.1f}')


def test_the_residual_pair_is_stated_for_both_themes(measured, comment):
    """The honest part of the comment, and the easiest to let rot.

    --accent and --series-a stay close. That is acceptable only because they
    never share a view, so the figures have to stay true for whoever checks
    that claim later.
    """
    m = re.search(r'([\d.]+) dE00 dark, ([\d.]+) light, ([\d.]+) under CVD',
                  comment)
    assert m, (
        'the comment no longer states the residual pair as '
        '"N dE00 dark, N light, N under CVD"')
    dark_n = measured['dark'][('--series-a', '--accent')][2]
    light_n = measured['light'][('--series-a', '--accent')][2]
    light_w = measured['light'][('--series-a', '--accent')][3]
    for claimed, actual, label in ((m.group(1), dark_n, 'dark normal'),
                                   (m.group(2), light_n, 'light normal'),
                                   (m.group(3), light_w, 'light under CVD')):
        assert abs(float(claimed) - actual) < 0.05, (
            f'comment says {claimed} for {label}; computed {actual:.1f}')


def test_the_residual_pair_is_really_below_the_floor(measured):
    """Guards the claim the comment is making ABOUT the numbers, not just the
    numbers. If a palette change pushed this pair above 15, the comment's
    careful hedging would be describing a problem that no longer exists."""
    for theme in ('dark', 'light'):
        normal = measured[theme][('--series-a', '--accent')][2]
        assert normal < 15, (
            f'{theme}: --series-a and --accent are now {normal:.1f} apart, '
            'above the dE00 15 floor. The comment still explains why their '
            'closeness is tolerable; rewrite it rather than leaving prose '
            'that argues about a resolved problem')


def test_the_chart_pair_clears_the_floor(measured):
    """The other half. The chips are only a fix if the colours they carry are
    actually distinguishable."""
    for theme in ('dark', 'light'):
        normal = measured[theme][('--series-a', '--series-b')][2]
        worst = measured[theme][('--series-a', '--series-b')][3]
        assert normal >= 15 and worst >= 15, (
            f'{theme}: the two model series are {normal:.1f} apart normally '
            f'and {worst:.1f} under red-green CVD. Below 15 the dot cannot '
            'carry identity on its own, which is the whole mechanism here')


def test_the_verifier_parses_the_palette_rather_than_copying_it():
    """A copied palette is a second source of truth that goes stale silently.
    Same assertion tests/test_matchup_cvd_comment.py makes, for the same
    reason."""
    src = (ROOT / 'src' / 'verify_model_colours.py').read_text(encoding='utf-8')
    assert 'dashboard_template.html' in src, (
        'verify_model_colours.py must read the tokens out of the template')
    assert not re.search(r"'--accent'\s*:\s*'#", src), (
        'verify_model_colours.py appears to hardcode a token value; it must '
        'parse them so the two cannot drift')


def test_the_verifier_does_not_use_the_matchup_shading_path():
    """The trap that produced a wrong number in the safe direction.

    verify_matchup_cvd.worst_dE() applies matchupColors()' shading push before
    simulating, which is right for two team fills that touch in a bar and
    wrong for two tokens. Using it here reported 34.1 for a pair that is
    10.8 -- a figure three times too flattering, which is the kind nobody
    thinks to re-check.
    """
    src = (ROOT / 'src' / 'verify_model_colours.py').read_text(encoding='utf-8')
    # A CALL, not a mention. The module names worst_dE twice in prose to say
    # why it is the wrong function here -- once as `worst_dE()`, with the
    # parentheses, which is why matching the name plus a bracket is not enough
    # and the docstrings have to come out first. A test that forbade the name
    # outright would forbid explaining the trap, which is the same mistake as
    # wording a rule to dodge its own checker.
    code = re.sub(r'""".*?"""', '', src, flags=re.S)
    assert not re.search(r'\bworst_dE\s*\(', code), (
        'verify_model_colours.py CALLS verify_matchup_cvd.worst_dE. That '
        'function shades its inputs first; these tokens are never shaded, so '
        'it reports a distance no reader ever sees -- 34.1 for a pair that '
        'is 10.8, wrong in the flattering direction')
