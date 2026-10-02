"""Every chart says what it is, or is hidden as decoration (Stage 26 item 8).

The 2026-09-28 audit: the Season Accuracy trend chart and its calibration
chart had no role and no label, so a screen reader met an unlabelled
graphic. Each is now role="img" with an aria-label naming what it plots and
where its numbers are in text. The rule is held over every chart the
template draws from data (an <svg> whose viewBox is computed, `0 0 ${...}`),
so the next chart is held too: it needs a role and a label, or
aria-hidden="true". Fixed-size icons (a 24x24 nav glyph beside its label)
are outside this rule.
"""
import re
from pathlib import Path

TEMPLATE = (Path(__file__).resolve().parents[1] / 'src' / 'pipeline' / 'dashboard_template.html').read_text(encoding='utf-8')


def svgs():
    return re.findall(r'<svg\b[^>]*viewBox="0 0 \$\{[^>]*>', TEMPLATE)


def test_the_scan_finds_the_charts():
    tags = svgs()
    assert len(tags) >= 3, f'only {len(tags)} data charts found -- re-anchor this test'
    assert any('running accuracy' in t for t in tags), 'the trend chart is not found'


def test_every_svg_is_labelled_or_hidden():
    bad = [t[:120] for t in svgs()
           if 'aria-hidden="true"' not in t
           and not (re.search(r'role="(img|group)"', t) and 'aria-label="' in t)]
    assert not bad, f'<svg> with neither a role and label nor aria-hidden: {bad}'


def test_the_accuracy_charts_point_at_their_tables():
    trend = next(t for t in svgs() if 'running accuracy' in t)
    calib = next(t for t in svgs() if 'Calibration chart' in t)
    assert 'Week by week table below' in trend and 'role="img"' in trend
    assert 'table below' in calib and 'role="img"' in calib
    assert '<h3>Week by week</h3>' in TEMPLATE or 'Week by week</h3>' in TEMPLATE
