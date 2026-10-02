"""Model Lab's results lead with their interval, drawn against zero (Stage 18).

The UX review's target for Model Lab: "the result column leads with the
proper scoring rule and a small interval glyph (├──●──┤ against a zero line),
then the sentence", with a text equivalent. generate_dashboard.interval_glyph()
draws it for every pre-registered row that has an interval; the 46 moved rows
keep their stored HTML, which carries no structured interval to draw.

Each glyph is on its own row's scale, symmetric about zero, because what it
shows is the thing the decision rests on: does the interval include zero?

Run with: pytest tests/test_model_lab_glyph.py -v
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from src.pipeline import generate_dashboard as gd  # noqa: E402
from src.pipeline import model_lab as ml  # noqa: E402

ROW = re.compile(r'<tr><td>(.*?)</td><td>(.*?)</td><td>(.*?)</td></tr>', re.S)


def parts(svg):
    """(zero x, [range x...], point x, aria-label) from one glyph."""
    zero = float(re.search(r'class="lab-ci-zero" x1="([\d.]+)"', svg).group(1))
    rng = [float(v) for v in re.findall(r'class="lab-ci-range" x1="([\d.]+)"', svg)]
    point = float(re.search(r'class="lab-ci-point" cx="([\d.]+)"', svg).group(1))
    label = re.search(r'aria-label="([^"]+)"', svg).group(1)
    return zero, rng, point, label


def test_an_interval_that_includes_zero_straddles_the_zero_line():
    zero, rng, point, label = parts(gd.interval_glyph({'diff': -0.0109, 'ci': [-0.0319, 0.0096]}))
    svg = gd.interval_glyph({'diff': -0.0109, 'ci': [-0.0319, 0.0096]})
    lo, hi = rng[0], float(re.search(r'class="lab-ci-range" x1="[\d.]+" y1="7.0" x2="([\d.]+)"', svg).group(1))
    assert lo < zero < hi and lo < point < zero
    assert label == '&minus;0.0109, interval &minus;0.0319 to +0.0096, includes zero'


def test_an_interval_clear_of_zero_says_so():
    svg = gd.interval_glyph({'diff': 0.03, 'ci': [0.01, 0.05]})
    zero, rng, point, label = parts(svg)
    assert all(x > zero for x in rng) and point > zero
    assert label.endswith('excludes zero')


def test_the_scale_is_symmetric_about_zero():
    zero, _, _, _ = parts(gd.interval_glyph({'diff': 0.5, 'ci': [0.1, 0.9]}))
    assert zero == pytest.approx(48.0), 'zero sits in the middle of a 96px glyph'


def test_the_text_equivalent_is_ascii():
    """The page is written in the platform's default encoding; on Windows
    (cp1252) a literal U+2212 minus crashed the build, found by running the
    suite on markys. The minus goes in as &minus;."""
    svg = gd.interval_glyph({'diff': -0.0109, 'ci': [-0.0319, 0.0096]})
    assert svg.isascii(), [c for c in svg if not c.isascii()]


def test_a_bound_that_rounds_to_zero_gets_the_decimals_it_needs():
    """H2's lower bound prints as +0.0000 in the sentence; the text
    equivalent must not then say "excludes zero" beside a zero."""
    assert gd._plain_signed(0.00001) == '+0.00001'
    assert gd._plain_signed(-0.0109) == '&minus;0.0109'
    assert gd._plain_signed(0.0) == '+0.0000'


def test_every_registered_result_leads_with_its_own_interval():
    entries = ml.entries()
    rows = ROW.findall(gd.render_model_lab_rows(entries))
    drawn = 0
    for e, (_, result, _) in zip(entries, rows):
        h = e['headline'] if e['stage'] else None
        if not h:
            assert 'lab-ci' not in result, (e['id'], 'a glyph with no interval behind it')
            continue
        assert result.startswith('<span class="lab-lead"><svg class="lab-ci"'), e['id']
        label = parts(result)[3]
        lo, hi = h['ci']
        assert label.endswith('includes zero' if lo <= 0 <= hi else 'excludes zero'), e['id']
        for v in (h['diff'], lo, hi):
            assert gd._plain_signed(v) in label, (e['id'], v)
        drawn += 1
    assert drawn >= 11


def test_a_correlation_is_not_read_as_a_difference():
    """R1 is a correlation across referees; a positive one is the finding it
    looked for. The sentence every other row ends with ("a negative difference
    favours the new idea") would read it backwards."""
    entries = ml.entries()
    rows = ROW.findall(gd.render_model_lab_rows(entries))
    by_id = {e['id']: result for e, (_, result, _) in zip(entries, rows) if e['stage']}
    assert 'favours the new idea' not in by_id['R1']
    assert 'The screen needed the whole interval above zero.' in by_id['R1']
    assert 'A negative difference favours the new idea.' in by_id['N1']


def test_every_glyph_sits_in_the_same_frame():
    """Each row's interval is on its own scale, so without a frame the bare
    lines read as graphs of different sizes in different places (Mark,
    2026-09-28). Every glyph now draws one frame, the same size, first; only
    the interval inside it moves, and zero is always its centre."""
    entries = ml.entries()
    rows = ROW.findall(gd.render_model_lab_rows(entries))
    frames = set()
    for e, (_, result, _) in zip(entries, rows):
        if not (e['stage'] and e['headline']):
            continue
        svg = re.search(r'<svg class="lab-ci".*?</svg>', result).group(0)
        first = re.search(r'<svg[^>]*>(<[a-z]+[^>]*>)', svg).group(1)
        assert first.startswith('<rect class="lab-ci-frame"'), (e['id'], 'the frame must be drawn first, under the interval')
        frames.add(first)
        assert parts(svg)[0] == pytest.approx(48.0), e['id']
    assert len(frames) == 1, frames
    src = (ROOT / 'src' / 'pipeline' / 'dashboard_template.html').read_text(encoding='utf-8')
    rule = re.search(r'\.lab-ci-frame\{([^}]*)\}', src)
    assert rule and 'stroke:var(--border)' in rule.group(1).replace(' ', ''), 'the frame has no visible edge'
