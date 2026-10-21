"""The NBA page as it was before opening night.

Three checks (the countdown, the rows' "Locks ..." labels, the empty accuracy
charts) are about the state before the first pick is saved and before any game
is played. The real page has left that state: it now carries saved picks and
games that are final or live. So they are checked against a copy of the built
page with its data rewound to the day before opening, rather than against the
page as it is today, which would fail the day the season began.
"""
import json
import re
from pathlib import Path

DATA = re.compile(r'(<script id="nba-data" type="application/json">)(.*?)(</script>)', re.S)


def pre_opening(path):
    """Write `<name>-pre-opening.html` beside `path`: no picks, every game still to be played."""
    path = Path(path)
    html = path.read_text(encoding='utf-8')
    m = DATA.search(html)
    data = json.loads(m.group(2))
    board = data['board']
    board['picks'] = {}
    for g in board['games']:
        g['status'] = 'scheduled'
        g['hs'] = None
        g['as'] = None
    body = json.dumps(data).replace('<', '\\u003c')
    copy = path.with_name(path.stem + '-pre-opening.html')
    copy.write_text(html[:m.start(2)] + body + html[m.end(2):], encoding='utf-8')
    return copy
