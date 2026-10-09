"""A game at a neutral site says so on its card (Stage 37 item 6).

Nine 2026 regular-season games are at neutral sites (London, Munich, Sao
Paulo and others). Each still has a listed home team, and both models still
give that team the home edge: a modelling choice, which Stage 38 leaves to
Mark as a registration. Until then the card says it plainly. nflverse's
schedule has `location` ('Home' or 'Neutral') and `stadium`; nothing in
src/ read either before this. Eight of the nine say 'Neutral'. The ninth,
week 5's PHI at JAX at Tottenham Hotspur Stadium, says 'Home', so a game
away from the home team's usual stadium counts as neutral too (Mark,
2026-10-08, after the gap was found by building the week's page).

The flag reaches the card two ways: on picks locked from now on, and, for
weeks locked before picks carried it, through the weekend refresh's status
snapshot. These tests hold each step and execute the card line.

Run with: pytest tests/test_neutral_site.py -v
"""
import json
import re
import shutil
import subprocess
from datetime import UTC, datetime

import pandas as pd
import pytest

from src.core.template_parts import JOINED_TEMPLATE
from src.sports.nfl import generate_dashboard as gd
from src.sports.nfl import weekend_refresh as wr
from src.sports.nfl import weekly_update as wu

NODE = shutil.which('node')


def function_source(src, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


@pytest.mark.parametrize('location, expected', [
    ('Neutral', True), ('neutral', True), ('Home', False), (None, None), (float('nan'), None)])
def test_the_schedule_location_reads_as_neutral_or_not_or_unknown(location, expected):
    game = pd.Series({'home_team': 'JAX', 'away_team': 'NYJ', 'location': location})
    assert wu.site_is_neutral(game) is expected


def test_a_schedule_without_the_column_is_unknown_not_home():
    assert wu.site_is_neutral(pd.Series({'home_team': 'JAX'})) is None
    assert wu._venue(pd.Series({'home_team': 'JAX'})) is None


def _season():
    """A small season: JAX hosts three games at home and one in London that
    the schedule lists as 'Home'; LA hosts one listed 'Neutral'."""
    rows = [('NYJ', 'JAX', 1, 'Home', 'EverBank Stadium'), ('TEN', 'JAX', 2, 'Home', 'EverBank Stadium'),
            ('PHI', 'JAX', 3, 'Home', 'Tottenham Hotspur Stadium'), ('HOU', 'JAX', 4, 'Home', 'EverBank Stadium'),
            ('SF', 'LA', 3, 'Neutral', 'Melbourne Cricket Ground'), ('ARI', 'LA', 4, 'Home', 'SoFi Stadium')]
    return pd.DataFrame([{'away_team': a, 'home_team': h, 'week': w, 'location': loc, 'stadium': st,
                          'gameday': '2026-10-11', 'gametime': '13:00', 'away_score': None,
                          'home_score': None, 'spread_line': 1.0} for a, h, w, loc, st in rows])


def test_the_usual_stadium_is_where_a_team_hosts_most_of_its_games():
    usual = wu.usual_home_stadiums(_season())
    assert usual['JAX'] == 'EverBank Stadium'
    assert wu.usual_home_stadiums(_season().drop(columns='stadium')) == {}


def test_a_game_away_from_the_usual_stadium_is_neutral_even_when_listed_home():
    sched = _season()
    rows = wu.with_usual_stadium(sched, sched[sched['week'] == 3])
    by_home = {r['home_team']: wu.site_is_neutral(r) for _, r in rows.iterrows()}
    assert by_home == {'JAX': True, 'LA': True}
    home_week = wu.with_usual_stadium(sched, sched[sched['week'] == 1])
    assert wu.site_is_neutral(home_week.iloc[0]) is False


def test_both_readers_add_the_usual_stadium_from_the_whole_season():
    """The weekly run and the weekend refresh must annotate the week's rows
    from the full schedule; a week's own rows cannot know a team's usual
    ground, and without the column the London game reads as home again."""
    import inspect
    assert "with_usual_stadium(sched, sched[sched['week'] == week])" in inspect.getsource(wu.plan_week)
    assert "with_usual_stadium(sched, sched[sched['week'] == week])" in inspect.getsource(wr.main)


def test_the_status_snapshot_carries_it_for_weeks_locked_before_picks_did():
    rows = pd.DataFrame([{'away_team': 'NYJ', 'home_team': 'JAX', 'gameday': '2026-10-11',
                          'gametime': '09:30', 'away_score': None, 'home_score': None,
                          'spread_line': 3.0, 'week': 6, 'location': 'Neutral',
                          'stadium': 'Wembley Stadium'}])
    games, _ = wr.build_week([{'away': 'NYJ', 'home': 'JAX'}], rows, datetime(2026, 10, 9, tzinfo=UTC))
    assert games[0]['neutral_site'] is True and games[0]['venue'] == 'Wembley Stadium'


def _pick(**over):
    p = {'away': 'NYJ', 'home': 'JAX', 'model_a_home_win_prob': 0.55, 'model_b_home_win_prob': 0.52,
         'market_prob_home': 0.5, 'spread_line': 1.0}
    p.update(over)
    return p


@pytest.mark.parametrize('pick, status, neutral, venue', [
    (_pick(neutral_site=True, venue='Wembley Stadium'), {}, True, 'Wembley Stadium'),
    (_pick(), {'neutral_site': True, 'venue': 'Allianz Arena'}, True, 'Allianz Arena'),
    (_pick(neutral_site=False), {'neutral_site': True}, False, None),
    (_pick(), {}, False, None),
], ids=['from-the-pick', 'from-the-snapshot', 'the-pick-wins', 'unknown-is-not-neutral'])
def test_the_page_takes_the_pick_first_then_the_snapshot(pick, status, neutral, venue):
    game = gd.build_games_js([pick], {}, {('JAX', 'NYJ'): status})[0]
    assert game['neutral'] is neutral and game['venue'] == venue


CASES = {
    'neutral_with_venue': {'home': 'JAX', 'neutral': True, 'venue': 'Wembley Stadium'},
    'neutral_no_venue': {'home': 'JAX', 'neutral': True, 'venue': None},
    'home_game': {'home': 'JAX', 'neutral': False, 'venue': 'EverBank Stadium'},
    'escaped': {'home': 'JAX', 'neutral': True, 'venue': 'A <b>'},
    'edge_out': {'home': 'JAX', 'neutral': True, 'venue': 'Wembley Stadium', 'edge_out': True},
}


@pytest.fixture(scope='module')
def lines():
    if not NODE:
        pytest.skip('node not available')
    src = JOINED_TEMPLATE.read_text(encoding='utf-8')
    js = (function_source(src, 'escapeHtml') + function_source(src, 'cardSiteLine')
          + f'\nconst C={json.dumps(CASES)};const o={{}};for(const k in C)o[k]=cardSiteLine(C[k]);'
          'process.stdout.write(JSON.stringify(o));')
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_a_pick_saved_before_v2_6_says_the_models_gave_the_home_edge(lines):
    """Saved picks are never rewritten, so a card shows the edge its pick was
    made with: an international game picked under v2.5 keeps its edge."""
    assert lines['neutral_with_venue'] == ('Neutral site · Wembley Stadium. The models gave JAX the home edge '
                                           '(picks saved before v2.6).')
    assert lines['neutral_no_venue'] == 'Neutral site. The models gave JAX the home edge (picks saved before v2.6).'


def test_a_v2_6_pick_says_neither_model_gives_a_home_edge(lines):
    assert lines['edge_out'] == 'Neutral site · Wembley Stadium. Neither model gives JAX a home edge here.'


def test_the_page_carries_whether_the_pick_took_the_edge_out():
    game = gd.build_games_js([_pick(neutral_site=True, home_edge_removed=True)], {}, {})[0]
    assert game['edge_out'] is True
    assert gd.build_games_js([_pick(neutral_site=True)], {}, {})[0]['edge_out'] is False


def test_a_home_game_draws_nothing(lines):
    assert lines['home_game'] == ''


def test_the_venue_is_escaped(lines):
    assert '<b>' not in lines['escaped'] and '&lt;b&gt;' in lines['escaped']


def test_the_line_sits_under_the_kickoff_and_status_above_the_picks():
    src = JOINED_TEMPLATE.read_text(encoding='utf-8')
    card = src[src.index('return `<div class="game-card'):]
    assert card.index('card-kickoff') < card.index('card-status') < card.index('card-site') < card.index('game-top')
