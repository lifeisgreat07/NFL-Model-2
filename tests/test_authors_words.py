"""The NHL's and NBA's pages in a reader's words, not their author's (audit 9 D15, the day sports' part).

The audit listed words that only the person who wrote the code would read easily: "ridge regression" in the
Ratings ledes; the NBA's "the playoffs 81%, the play-in 60%", which reads as 141%; "No report yet" beside a
goalie on a game already played; one heading, "How sure, and how often right", over two sections on Season
Accuracy; dates as 2026-11-15 in sentences; "(H = 120 days, K = 2,000 shots)" and a bare 98.33% in the
Model Lab's ledes; and file paths where a reader needs a link.

Run with: pytest tests/test_authors_words.py -v
"""
import json
import re
import subprocess
from pathlib import Path

from tests.optional import require_tool

ROOT = Path(__file__).resolve().parents[1]
NHL = (ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js').read_text(encoding='utf-8').replace('\r\n', '\n')
NBA = (ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js').read_text(encoding='utf-8').replace('\r\n', '\n')
BOARD = (ROOT / 'src' / 'core' / 'day_board.js').read_text(encoding='utf-8').replace('\r\n', '\n')
ACC = (ROOT / 'src' / 'core' / 'accuracy.js').read_text(encoding='utf-8').replace('\r\n', '\n')


def fn(src, name):
    return re.search(rf'^function {name}\(.*?\n\}}\n', src, re.S | re.M).group(0)


def node(code):
    out = subprocess.run([require_tool('node'), '-e', code], capture_output=True, text=True, encoding='utf-8', check=True)
    return json.loads(out.stdout)


def test_the_ratings_say_what_the_fit_does_without_naming_it():
    for sport, src, unit in (('nhl', NHL, 'goal'), ('nba', NBA, 'point')):
        lede = re.search(rf'A club&#39;s {unit} rating is how many [^.]*\.', src).group(0)
        assert 'ridge' not in lede, sport
        assert 'recent games counting more and every club pulled a little toward average' in lede, sport


def test_the_nbas_playoff_and_play_in_chances_do_not_read_as_one_total():
    assert ("Makes the playoffs in <b>${chance(odds_.playoff_pct)}</b> of simulated seasons; finishes 7th to 10th, "
            "in the play-in, in ${chance(odds_.playin_pct)}, some of them on the way to the playoffs.") in NBA
    assert 'the playoffs <b>${chance(odds_.playoff_pct)}</b>, the play-in' not in NBA


def test_a_goalie_with_no_report_on_a_game_under_way_is_not_waiting_for_one():
    code = fn(NHL, 'goalieText') + "function escapeHtml(s){ return String(s); }\n" + (
        "const gl = {name: 'Jake Allen', basis: 'projected', status: null};"
        "process.stdout.write(JSON.stringify([goalieText('NJD', gl, false), goalieText('NJD', gl, true)]));")
    before, after = node(code)
    assert '>No report yet</span>' in before
    assert '>No report at the pick</span>' in after and 'yet' not in after
    for call in ("goalieText(g.away, p.goalies.away, g.status !== 'scheduled')",
                 "goalieText(g.away, gl.away, g.status !== 'scheduled')"):
        assert call in NHL, call


def test_season_accuracy_has_one_heading_a_section():
    for sport, src in (('nhl', NHL), ('nba', NBA)):
        assert 'How sure, and how often right' not in src, f"{sport}: the table under the chart's heading again"
        assert 'Each pick&#39;s chance, and how often it was right' in src, sport
    assert ACC.count('<h3>How sure, and how often right</h3>') == 1


def test_a_date_reads_as_a_date():
    code = fn(BOARD, 'dayText') + "process.stdout.write(JSON.stringify(['2026-11-15', '2026-11-14T03:10:12Z', 'week 9', ''].map(dayText)));"
    assert node(code) == ['Nov 15, 2026', 'Nov 13, 2026', 'week 9', ''], 'a time is the day it falls on in Eastern time'
    for sport, src in (('nhl', NHL), ('nba', NBA)):
        assert not re.search(r'amended on \d{4}-\d\d-\d\d', src), sport
        assert 'As of ${escapeHtml(s.as_of)}' not in src and 'As of ${escapeHtml(r.as_of)}' not in src, sport
    assert 'of them through ${dayText(f.through)}' in BOARD


def test_the_model_labs_settings_and_level_are_said_in_words():
    for sport, src in (('nhl', NHL), ('nba', NBA)):
        lede = re.search(r'Registered before any (?:NHL|NBA) model was fitted.*?</p>', src, re.S).group(0)
        assert 'H = ' not in lede and 'K = ' not in lede and '<code>' not in lede, sport
        assert 'an earlier game counting half as much every' in lede, sport
        assert 'wider than the usual 95% because three questions share that 95%' in lede, sport
