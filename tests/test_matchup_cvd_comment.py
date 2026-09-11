"""The CVD figures in the game-card comment must match the script that makes them.

PR #52 shipped "115 of 992 team/theme pairs ... 15 effectively identical" as a
permanent source comment. Booth re-ran the stated method and got 71 and 9; an
independent re-derivation got 70 and 9. The number was wrong in the code for as
long as it took someone to check by hand, and nothing would ever have caught it,
because a comment is not executable.

This makes it executable. `src/verify_matchup_cvd.py` computes the figures from
TEAM_COLOR and CONTRAST_THRESHOLD as they actually are in the template; these
tests assert the comment agrees with it. Change the palette or the threshold and
the comment goes stale -- loudly, here, rather than silently in review.

The repo has the same arrangement for the low-confidence finding
(`src/verify_low_confidence_finding.py`), added after Booth flagged an
unverifiable number on PR #18.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'src' / 'dashboard_template.html'
sys.path.insert(0, str(ROOT / 'src'))

# These tests used to run twice, against the template and against index.html,
# and a fifth test asserted the two copies agreed. That made sense while
# index.html was committed: a generated file under version control can be left
# stale, and the pair check was the thing that noticed.
#
# Stage 8c phase 2 untracked it. The root conftest.py now builds index.html
# from this very template at the start of every session, so the generated copy
# cannot differ from the template -- not "is unlikely to", cannot. A test that
# can only fail if the generator stops copying a comment verbatim is testing
# the generator, and tests/test_dashboard_charts.py already does that against
# the real placeholders.
#
# So the [generated] parametrisation and test_the_two_copies_of_the_comment_agree
# were removed rather than left passing. A test that cannot fail is worse than
# no test: it reports coverage it does not provide.


@pytest.fixture(scope='module')
def computed():
    import verify_matchup_cvd as v
    tc = v.team_colors()
    from itertools import permutations
    best = {}
    for a, h in permutations(sorted(tc), 2):
        key = tuple(sorted((a, h)))
        best[key] = min(best.get(key, 1e9), v.worst_dE(tc[a], tc[h]))
    return best


def comment(path):
    src = path.read_text(encoding='utf-8')
    m = re.search(r'/\* The 2px gap is the accessibility half.*?\*/', src, re.S)
    assert m, f'the game-card CVD comment is missing from {path.name}'
    return m.group(0)


def test_the_pair_counts_in_the_comment_are_what_the_script_computes(computed):
    path = TEMPLATE
    total = len(computed)
    under15 = sum(1 for d in computed.values() if d < 15)
    under5 = sum(1 for d in computed.values() if d < 5)
    text = comment(path)

    m = re.search(r'(\d+) of the (\d+) distinct team pairs \(([\d.]+)%\)', text)
    assert m, 'the comment no longer states "N of the M distinct team pairs (P%)"'
    assert (int(m.group(1)), int(m.group(2))) == (under15, total), (
        f'comment says {m.group(1)} of {m.group(2)} pairs under the dE00 15 floor; '
        f'src/verify_matchup_cvd.py computes {under15} of {total}')
    assert abs(float(m.group(3)) - under15 / total * 100) < 0.05, (
        f'comment says {m.group(3)}%; computed {under15 / total * 100:.1f}%')

    m5 = re.search(r'(\d+) are effectively identical', text)
    assert m5, 'the comment no longer states how many pairs are effectively identical'
    assert int(m5.group(1)) == under5, (
        f'comment says {m5.group(1)} effectively identical; computed {under5}')


def test_the_worst_pairs_named_in_the_comment_are_the_worst_pairs(computed):
    """The count is threshold-fragile; the worst pairs are not. So they are
    checked exactly, and they are what the comment tells a reader to trust."""
    # \d+\.\d+ rather than [\d.]+ so a sentence-ending period is not swallowed
    named = re.findall(r'([A-Z]{2,3})/([A-Z]{2,3}) (\d+\.\d+)', comment(TEMPLATE))
    assert named, 'the comment names no worst pairs'

    ranked = sorted(computed.items(), key=lambda kv: kv[1])
    for i, (a, b, quoted) in enumerate(named):
        key = tuple(sorted((a, b)))
        assert key in computed, f'{a}/{b} is not a team pair'
        assert ranked[i][0] == key, (
            f'the comment lists {a}/{b} in position {i + 1}; '
            f'computed rank {i + 1} is {"/".join(ranked[i][0])}')
        assert abs(float(quoted) - computed[key]) < 0.005, (
            f'comment says {a}/{b} is {quoted}; computed {computed[key]:.2f}')


def test_the_threshold_fragility_count_is_what_the_script_computes(computed):
    """The sentence that got away.

    The comment's caveat originally read "seven pairs sit between 14.9 and
    15.25". The real figure is nine. Booth caught it on PR #52 and named the
    reason it survived: the two tests above cover the headline count and the
    worst-pairs list, and nothing covered this sentence -- so a number read off
    the script's output by eye went straight into the file that exists to stop
    numbers being read off by eye. Every number in that comment is asserted now.
    """
    lo, hi = 14.9, 15.25
    actual = sum(1 for d in computed.values() if lo < d < hi)
    text = comment(TEMPLATE)
    m = re.search(r'(\d+) pairs sit between ([\d.]+) and ([\d.]+)', text)
    assert m, 'the comment no longer states "N pairs sit between X and Y"'
    assert (float(m.group(2)), float(m.group(3))) == (lo, hi), (
        f'the comment quotes the band {m.group(2)}-{m.group(3)}; this test '
        f'checks {lo}-{hi}. Change both together or neither.')
    assert int(m.group(1)) == actual, (
        f'comment says {m.group(1)} pairs between {lo} and {hi}; '
        f'src/verify_matchup_cvd.py computes {actual}')


def test_the_verifier_reads_the_palette_rather_than_copying_it():
    """A copied palette is a second source of truth that goes stale silently."""
    src = (ROOT / 'src' / 'verify_matchup_cvd.py').read_text(encoding='utf-8')
    assert 'TEAM_COLOR' in src and 'dashboard_template.html' in src, (
        'verify_matchup_cvd.py must read TEAM_COLOR out of the template')
    assert not re.search(r"ARI\s*:\s*'#", src), (
        'verify_matchup_cvd.py appears to hardcode the team palette; it must '
        'parse it out of the template so the two cannot drift')
