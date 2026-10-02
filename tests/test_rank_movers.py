"""
Power Ratings' rank change and biggest-moves line (Stage 19, 2026-09-28).

The arrow follows RANK, not rating (Mark's call): a team can gain rating and
drop places when others gain more, and the old rating-delta arrow could point
up beside a team that fell. The number is places moved since the previous
weekly update, computed in Python from the live team history so it agrees
with the # column.

Held here: the sign (up the table is positive, and the arrow and words say
the same thing), the refusal to guess when there is no clean previous
ranking, the tie-break, the premise that the latest history week IS the
ratings snapshot, and the sentence's grammar over ties and quiet weeks.

Run with: pytest tests/test_rank_movers.py -v
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

from src.pipeline import generate_dashboard as gd  # noqa: E402

TEMPLATE = REPO_ROOT / 'src' / 'pipeline' / 'dashboard_template.html'
NODE = shutil.which('node')


def rating(team, net):
    return {'team': team, 'name': team, 'off': 0.0, 'def': 0.0, 'net': net}


def history(*weeks):
    """weeks: dicts of team -> net, one per week, numbered from 1."""
    out = {}
    for w, nets in enumerate(weeks, start=1):
        for team, net in nets.items():
            out.setdefault(team, []).append({'week': w, 'net': net})
    return out


# Week 1: A first, B second, C third. Week 2 (the snapshot): C first, A, B.
W1 = {'A': 0.3, 'B': 0.2, 'C': 0.1}
W2 = {'A': 0.25, 'B': 0.15, 'C': 0.4}
NOW = [rating(t, n) for t, n in W2.items()]


def rows(now, previous):
    """The Power Ratings rows exactly as main() builds them."""
    return {t['team']: t for t in gd.with_rank_change(gd.build_teams_js(now), previous)}


def test_moving_up_the_table_is_positive():
    teams = rows(NOW, gd.previous_ranks(NOW, history(W1, W2)))
    assert teams['C']['rank_change'] == 2, teams['C']
    assert teams['A']['rank_change'] == -1, teams['A']
    assert teams['B']['rank_change'] == -1, teams['B']


def test_the_arrow_follows_rank_not_rating():
    """The case that separates the two readings: A's rating ROSE, from 0.3
    to 0.35, while C passed it. A rating arrow would point up; the rank moved
    down one place, and that is what must be shown."""
    w2 = {'A': 0.35, 'B': 0.2, 'C': 0.5}      # A's rating up 0.05, yet C passes it
    now = [rating(t, n) for t, n in w2.items()]
    teams = rows(now, gd.previous_ranks(now, history(W1, w2)))
    assert teams['A']['rank_change'] == -1, (
        f"A's rating rose and it lost a place; rank_change is {teams['A']['rank_change']}")


def test_one_week_of_history_has_nothing_to_compare_with():
    assert gd.previous_ranks(NOW, history(W2)) is None
    assert all(t['rank_change'] is None for t in rows(NOW, None).values()), (
        'no previous ranking must print no movement, not "no change"')


def test_main_adds_the_rank_change_to_the_rows_it_ships():
    """Every function above can be right and the page still show nothing, if
    main() never calls them (the collector that never ran, CLAUDE.md)."""
    src = Path(gd.__file__).read_text(encoding='utf-8')
    assert re.search(r'teams_js = with_rank_change\(teams_js, previous_ranks\(ratings, '
                     r'load_latest_live_history\(\)\)\)', src)


def test_a_team_missing_from_the_previous_week_means_no_ranking():
    """A partial previous week would rank 31 teams and call it the league."""
    w1 = {'A': 0.3, 'B': 0.2}
    assert gd.previous_ranks(NOW, history(w1, W2)) is None


def test_a_history_that_is_not_the_snapshot_is_refused(capsys):
    """If the latest history week is not today's ratings, the comparison
    would be against the wrong week. Refused, and said."""
    stale = [rating('A', 0.9), rating('B', 0.15), rating('C', 0.4)]
    assert gd.previous_ranks(stale, history(W1, W2)) is None
    assert 'does not match' in capsys.readouterr().out
    missing = [rating('A', 0.25), rating('B', 0.15), rating('C', 0.4), rating('D', 0.0)]
    assert gd.previous_ranks(missing, history(W1, W2)) is None


def test_the_previous_ranking_breaks_ties_like_the_current_one():
    tied = {'A': 0.2, 'B': 0.2, 'C': 0.1}
    assert gd.previous_ranks(NOW, history(tied, W2)) == {'A': 1, 'B': 2, 'C': 3}


def test_the_committed_ratings_are_the_latest_history_week():
    """The premise previous_ranks rests on, checked against the real files:
    the weekly run writes current_ratings.json and appends the same numbers
    to the season's history. If a run ever writes one and not the other, this
    goes red rather than the page quietly comparing against the wrong week."""
    ratings = json.loads((REPO_ROOT / 'data' / 'current_ratings.json').read_text(encoding='utf-8'))
    live = gd.load_latest_live_history()
    assert live, 'no data/team_history_<season>.json -- vacuity: nothing was checked'
    latest = max(p['week'] for pts in live.values() for p in pts)
    for r in ratings:
        point = [p for p in live[r['team']] if p['week'] == latest]
        assert point and abs(point[0]['net'] - r['net']) < 1e-9, (
            f"{r['team']}: current rating {r['net']} is not week {latest}'s {point}")


# ---- the page half, executed in node over the real functions ----

def function_source(src, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def t(name, change):
    return {'name': name, 'rank_change': change}


SENTENCES = {
    'one_each': [t('Chicago Bears', 3), t('Dallas Cowboys', -2), t('Buffalo Bills', 0)],
    'singular': [t('Chicago Bears', 1), t('Dallas Cowboys', -1)],
    'tied_rise': [t('Detroit Lions', 2), t('Atlanta Falcons', 2), t('Miami Dolphins', 2),
                  t('Tennessee Titans', 2), t('Dallas Cowboys', -1)],
    'only_rises': [t('Chicago Bears', 2), t('Dallas Cowboys', 0)],
    'quiet': [t('Chicago Bears', 0), t('Dallas Cowboys', 0)],
    'no_history': [t('Chicago Bears', None), t('Dallas Cowboys', None)],
}
MOVES = {'up3': 3, 'down1': -1, 'still': 0, 'none': None}


@pytest.fixture(scope='module')
def page():
    if not NODE:
        pytest.skip('node not available')
    src = TEMPLATE.read_text(encoding='utf-8')
    # Caught per case, so a case that throws fails its own test (CLAUDE.md:
    # a guard must fail on its own assertion, never through its fixture).
    js = function_source(src, 'rankMoveHtml') + function_source(src, 'moversSentence') + \
        f'\nconst S={json.dumps(SENTENCES)};const M={json.dumps(MOVES)};const o={{s:{{}},m:{{}}}};' \
        'for(const k in S){try{o.s[k]=moversSentence(S[k]);}catch(e){o.s[k]="THREW: "+e.message;}}' \
        'for(const k in M){try{o.m[k]=rankMoveHtml(M[k]);}catch(e){o.m[k]="THREW: "+e.message;}}' \
        'process.stdout.write(JSON.stringify(o));'
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_the_sentence_names_the_biggest_rise_and_fall(page):
    assert page['s']['one_each'] == (
        'Biggest moves since the last update: Chicago Bears up 3 places; '
        'Dallas Cowboys down 2 places.')


def test_one_place_is_singular(page):
    assert 'up 1 place;' in page['s']['singular']
    assert 'down 1 place.' in page['s']['singular']


def test_ties_are_named_two_at_most_then_counted(page):
    assert page['s']['tied_rise'] == (
        'Biggest moves since the last update: Atlanta Falcons, Detroit Lions and 2 more '
        'up 2 places; Dallas Cowboys down 1 place.')


def test_a_week_with_no_fall_names_no_fall(page):
    assert page['s']['only_rises'] == 'Biggest moves since the last update: Chicago Bears up 2 places.'


def test_a_quiet_week_says_so_and_no_history_says_nothing(page):
    assert page['s']['quiet'] == 'No team changed places since the last update.'
    assert page['s']['no_history'] == '', 'with nothing to compare, the line must stay hidden'


def test_the_arrow_points_the_way_the_number_moved(page):
    up, down = page['m']['up3'], page['m']['down1']
    assert 'trend-arrow up' in up and '&#9650;3' in up and 'up 3 places' in up, up
    assert 'trend-arrow down' in down and '&#9660;1' in down and 'down 1 place ' in down, down


def test_no_move_and_no_history_draw_no_arrow(page):
    assert page['m']['none'] == ''
    assert 'trend-arrow' not in page['m']['still'] and 'no change' in page['m']['still']


def test_the_table_and_the_line_both_use_them():
    body = function_source(TEMPLATE.read_text(encoding='utf-8'), 'renderRatings')
    assert 'rankMoveHtml(t.rank_change)' in body
    assert 'moversSentence(teams)' in body, (
        'the line must be computed from the whole league, not the searched view')


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
