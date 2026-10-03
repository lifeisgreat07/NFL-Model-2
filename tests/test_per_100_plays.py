"""Ratings are shown per 100 plays; the model and the data stay per play.

Stage 14 (CLAUDE.md). Mark chose it on 2026-09-26 from a rendered
side-by-side of Power Ratings: BUF's net rating reads +14.9 instead of
+0.149, offense +15.4, SOS +5.1, and the bar's scale +/-17. The rescaling is
display-only: fmtRating() multiplies by ratingScale() and rounds to a tenth,
and these tests hold every displayed rating to the value it came from.

Run with: pytest tests/test_per_100_plays.py -v
"""
import json
import random
import re
import shutil
import subprocess

import pytest

from src.pipeline.template_parts import JOINED_TEMPLATE  # noqa: E402

TEMPLATE = JOINED_TEMPLATE
NODE = shutil.which('node')
FIXED = [0.149, 0.154, 0.005, 0.051, -0.051, -0.0004, 0.0004, 0, -0.12, 0.1705, -0.00049]
rng = random.Random(14)
SAMPLE = [round(rng.uniform(-0.3, 0.3), 5) for _ in range(400)]


@pytest.fixture(scope='module')
def src():
    return TEMPLATE.read_text(encoding='utf-8').replace('\r\n', '\n')


@pytest.fixture(scope='module')
def run(src):
    if not NODE:
        pytest.skip('node not available')
    code = re.search(r'function ratingScale\(\).*?\nfunction fmtRatingScale\(.*?\n\}\n', src, re.S)
    assert code, 'the rating formatters are not findable -- re-anchor this guard'
    js = (code.group(0) +
          f'\nprocess.stdout.write(JSON.stringify({{'
          f'fixed: {json.dumps(FIXED)}.map(fmtRating),'
          f'sample: {json.dumps(SAMPLE)}.map(fmtRating),'
          f'scale: [0.1705, -0.1705, 0.004].map(fmtRatingScale)}}));')
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_the_ratings_mark_saw_read_as_he_chose(run):
    f = dict(zip(map(str, FIXED), run['fixed']))
    assert f['0.149'] == '+14.9' and f['0.154'] == '+15.4' and f['0.051'] == '+5.1'
    assert f['-0.051'] == '-5.1' and f['0.005'] == '+0.5' and f['-0.12'] == '-12.0'


def test_zero_has_no_sign(run):
    f = dict(zip(map(str, FIXED), run['fixed']))
    for key in ('0', '-0.0004', '0.0004', '-0.00049'):
        assert f[key] == '0.0', f'{key} displays as {f[key]!r}; a rating that rounds to zero is 0.0'


def test_every_display_is_the_data_times_100_to_a_tenth(run):
    """Held to the data: parse each shown value back and compare."""
    for x, shown in zip(SAMPLE, run['sample']):
        assert re.fullmatch(r'[+-]?\d+\.\d', shown), shown
        assert abs(float(shown) - x * 100) <= 0.05 + 1e-9, f'{x} shown as {shown}'
        assert (shown.startswith('+')) == (round(x * 1000) > 0), f'sign of {x} shown as {shown}'


def test_the_bar_scale_is_a_whole_number_in_the_same_units(run):
    assert run['scale'] == ['17', '17', '0']


def test_power_ratings_and_team_dive_show_every_rating_through_it(src):
    ratings = re.search(r'function renderRatings\(\)\{.*?\n\}\n', src, re.S).group(0)
    # The old trend arrow's tooltip ('${fmtRating(delta)} per 100 plays') left
    # this list in Stage 19: the arrow now shows places moved, not a rating
    # change, so there is no rating in it to format.
    for cell in ('${fmtRating(t.net)}', '${fmtRating(t.off)}', '${fmtRating(t.def)}', 'fmtRating(t.sos)',
                 'fmtRatingScale(maxAbs)'):
        assert cell in ratings, f'Power Ratings no longer shows {cell} through the formatter'
    assert '.toFixed(3)' not in ratings, 'a rating in Power Ratings is still printed per play'
    dive = re.search(r'function renderTeamDive\(\)\{.*?\n\}\n', src, re.S).group(0)
    assert '${fmtRating(p.net)}' in dive and '.toFixed(3)' not in dive, (
        'Team Deep-Dive shows the same net rating in a different unit')


def test_the_page_says_what_the_unit_is(src):
    assert 'in expected points per 100 plays, rebuilt each week' in src, (
        'Power Ratings no longer says its numbers are per 100 plays')
