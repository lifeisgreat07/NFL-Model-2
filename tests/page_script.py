"""The day-sport page script as the page includes it (Stage 87 item 1).

The NHL's and NBA's pages include src/core/day_board.js, the functions the two
boards share, ahead of their own nhl.js or nba.js in the same <script> element.
A test that reads a sport's script for one of those functions reads both, in
that order.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAY_BOARD = ROOT / 'src' / 'core' / 'day_board.js'


def day_script(sport: str) -> str:
    """src/core/day_board.js and the sport's own script, joined as its page joins them."""
    own = ROOT / 'src' / 'sports' / sport / 'pages' / f'{sport}.js'
    return DAY_BOARD.read_text(encoding='utf-8') + '\n' + own.read_text(encoding='utf-8')
