"""The NBA explains itself before its first pick (Stage 68 item 6).

The 2026-10-09 audit found the NBA's home card showing "Picks this season
—" because its "Live from" status waited for no games within two weeks,
which a loaded schedule never allows; the board's "no picks yet" state
waited for an empty schedule, which never happens either; and opening night
was written by hand in three places, one of them four hours off the
schedule's first tip-off. Now the card and the board key on no saved picks,
read opening night from the schedule, and the board shows the backtest's
H3 answer before the season.

Run with: pytest tests/test_nba_preseason.py -v
"""
import json
from datetime import UTC, datetime
from pathlib import Path

from src.site import home

ROOT = Path(__file__).resolve().parents[1]
NBA_JS = (ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js').read_text(encoding='utf-8')
HOME_JS = (home.TEMPLATE / 'home.js').read_text(encoding='utf-8')
NOW = datetime(2026, 10, 10, 16, 0, tzinfo=UTC)


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding='utf-8')


def test_the_card_knows_the_first_game_and_how_many_picks_are_saved(tmp_path):
    games = [{'start_utc': '2026-10-21T23:00:00Z', 'status': 'scheduled', 'game_type': 'regular'},
             {'start_utc': '2026-10-20T19:00:00Z', 'status': 'scheduled', 'game_type': 'regular'},
             {'start_utc': '2026-11-30T00:00:00Z', 'status': 'scheduled', 'game_type': 'regular'}]
    write(tmp_path / 'results/nba/schedule_2026.json', {'games': games})
    f = home.nba_facts(tmp_path, NOW)
    assert f['first_game'] == '2026-10-20T19:00:00Z' and f['picks'] == 0
    write(tmp_path / 'results/nba/graded_2026.json', [{'result': 'pending'}, {'result': 'correct'}])
    assert home.nba_facts(tmp_path, NOW)['picks'] == 2


def test_the_home_card_keys_on_no_picks_not_on_no_games():
    assert 'NBA_OPENING' not in HOME_JS and '2026-10-20' not in HOME_JS
    assert 'return !f.picks && first > NOW - 3 * HOUR ? first : null;' in HOME_JS
    assert "const first = beforeFirstPick(f);" in HOME_JS and "{text:`Live from ${day}`}" in HOME_JS


def test_the_board_reads_opening_night_from_the_schedule():
    assert NBA_JS.count("'2026-10-20'") == 1, 'only the fallback for a page with no schedule'
    assert NBA_JS.count('dayDate(OPENING_DAY)') == 3
    assert "const FIRST_GAME = BD.games.filter(g => g.start).sort((a, b) => a.start.localeCompare(b.start))[0] || null;" in NBA_JS


def test_the_board_says_no_picks_yet_with_the_backtests_h3_answer():
    assert "if(Object.keys(BD.picks || {}).length || !FIRST_GAME) return '';" in NBA_JS
    assert "const verdict = h3 && h3.label" in NBA_JS and '<b>${escapeHtml(h3.label)}</b>' in NBA_JS
    assert '<b>${better(h3.diff)}</b>' in NBA_JS, 'the direction is read, not written'
    assert NBA_JS.count('head + preseasonHtml() + ') == 2, 'on a day with games and on one without'
    assert NBA_JS.count('labLinks(grid);') == 2
