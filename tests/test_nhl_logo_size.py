"""The NHL's team logos draw as big as the NFL Week Board's (Stage 62 item 3).

Both boards box a logo with the shared `.card-end-logo` rule, 20 x 20 with
`object-fit: contain`. The two leagues' files are different shapes, so the
same box drew different marks. Measured 2026-10-09 on every file each page
loads (32 NHL `*_dark.svg` from assets.nhle.com, 34 ESPN NFL PNGs), drawing
each with `contain` into a square canvas in Chromium and taking the bounding
box of pixels with alpha over 40:

- ESPN's NFL files are 500 x 500; the mark spans a median 0.92 of the width.
- The NHL's files are 225 x 150 (3:2), and the mark spans a median 0.59 of
  the file's width.

So in 20 x 20 the NFL's mark drew about 18px wide and the NHL's about 12px
(20 x 0.59), a third smaller, which is what Mark saw. A 30 x 20 box holds the
NHL file whole at the same height (the row does not grow) and draws the mark
about 18px wide. The figures above are the measurement; this file holds the
arithmetic and the CSS that rests on it, so a change to either shows here.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / 'src' / 'dashboard' / 'styles.css'
NHL = ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.css'

NFL_FILE = (500, 500)
NHL_FILE = (225, 150)
NFL_INK_WIDTH = 0.92   # of the file's width, median of 34
NHL_INK_WIDTH = 0.59   # of the file's width, median of 32
TOLERANCE = 0.10       # the drawn marks within 10% of each other


def rule(css: str, selector: str) -> str:
    text = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    m = re.search(re.escape(selector) + r'\s*\{([^}]*)\}', text)
    assert m, f'no rule for {selector}'
    return m.group(1)


def px(body: str, prop: str) -> float:
    m = re.search(rf'(?:^|;)\s*{prop}\s*:\s*([\d.]+)px', body)
    assert m, f'{prop} is not set in px: {body}'
    return float(m.group(1))


def drawn_width(box_w: float, box_h: float, file_wh: tuple[int, int], ink: float) -> float:
    """The mark's width under object-fit: contain."""
    scale = min(box_w / file_wh[0], box_h / file_wh[1])
    return file_wh[0] * scale * ink


def boxes():
    shared = rule(SHARED.read_text(encoding='utf-8'), '.card-end-logo')
    nhl = rule(NHL.read_text(encoding='utf-8'), '[data-sport="nhl"] .card-end-logo')
    w, h = px(shared, 'width'), px(shared, 'height')
    return (w, h), (px(nhl, 'width'), h)


def test_the_nhl_mark_draws_as_wide_as_the_nfl_mark():
    (nw, nh), (hw, hh) = boxes()
    nfl = drawn_width(nw, nh, NFL_FILE, NFL_INK_WIDTH)
    nhl = drawn_width(hw, hh, NHL_FILE, NHL_INK_WIDTH)
    assert abs(nhl - nfl) / nfl <= TOLERANCE, (
        f'the NHL logo draws {nhl:.1f}px wide against the NFL board\'s {nfl:.1f}px')


def test_the_nhl_box_keeps_the_rows_height():
    """Wider, not taller: a taller box would push the bar beside it down
    (the shared rule's negative margin is set for 20px)."""
    nhl = rule(NHL.read_text(encoding='utf-8'), '[data-sport="nhl"] .card-end-logo')
    assert 'height' not in nhl, 'the NHL rule sets only the width; the height stays the shared 20px'
    (_, nh), (hw, hh) = boxes()
    assert hh == nh == 20
    assert hw / hh <= NHL_FILE[0] / NHL_FILE[1] + 1e-9, 'a box wider than the file only adds margin'
