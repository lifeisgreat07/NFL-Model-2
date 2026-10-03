"""The Week Board card's channel, quarterbacks and team-news line (Stage 17).

Three small facts on the card, each from a file checked before it got here:
the TV channel from src/pipeline/tv_channels.py, the quarterbacks from the saved pick,
the news from src/pipeline/team_news.py. The rules they are held to are the plan's
(CLAUDE.md Stages 15 to 17): the network name only, and one line on the page
saying Sunday-afternoon CBS and FOX games are regional; the quarterbacks the
pick was made with, saying so when one was only assumed; at most one news
line, only when a starter is out or doubtful or the quarterback changed.

The functions are run in node rather than read.

Run with: pytest tests/test_card_context.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.pipeline.template_parts import JOINED_TEMPLATE

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = JOINED_TEMPLATE

from src.pipeline import generate_dashboard as gd  # noqa: E402

NODE = shutil.which('node')


def src():
    return TEMPLATE.read_text(encoding='utf-8').replace('\r\n', '\n')


def fn(s, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', s, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def run(expr):
    if not NODE:
        pytest.skip('node not available')
    s = src()
    js = ''.join(fn(s, f) for f in ('escapeHtml', 'cardTvPill', 'boardTvNote', 'cardQbLine',
                                     'cardNewsTeam', 'cardNewsLine'))
    r = subprocess.run([NODE, '-e', js + f'\nprocess.stdout.write(JSON.stringify({expr}));'],
                       capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def j(x):
    return json.dumps(x)


GAME = {'away': 'ATL', 'home': 'GB', 'tv': 'Prime Video', 'tv_regional': False,
        'graded': False, 'status': None}


# ---- the channel -----------------------------------------------------------

def test_the_channel_is_the_network_name_and_nothing_else():
    html = run(f'cardTvPill({j(GAME)})')
    assert html == ('<span class="tv-pill"><span class="visually-hidden">On TV: </span>'
                    'Prime Video</span>')
    assert run(f'cardTvPill({j(dict(GAME, tv=None))})') == '', 'no channel, no pill'


def test_the_channel_leaves_once_the_game_is_over():
    assert run(f'cardTvPill({j(dict(GAME, status="started"))})') != '', 'on air now: still useful'
    assert run(f'cardTvPill({j(dict(GAME, status="final"))})') == ''
    assert run(f'cardTvPill({j(dict(GAME, graded=True))})') == ''


def test_the_regional_line_appears_only_with_a_regional_game_on_screen():
    cbs = dict(GAME, tv='CBS', tv_regional=True)
    assert run(f'boardTvNote({j([GAME])})') is False, 'a national game says nothing'
    assert run(f'boardTvNote({j([GAME, cbs])})') is True
    assert run(f'boardTvNote({j([dict(cbs, status="final")])})') is False, (
        'no pill on screen, so nothing for the line to explain')


def test_the_card_puts_the_channel_in_the_kickoff_line_and_the_note_by_the_grid():
    s = src()
    body = fn(s, 'renderGames')
    assert '<div class="card-kickoff">${kickoff}${tvPill}</div>' in body
    assert 'tvNote.hidden = !boardTvNote(sorted);' in body
    assert re.search(r'<p class="board-note" id="board-tv-note" hidden>CBS and FOX games on '
                     r'Sunday afternoon are regional[^<]*</p>\s*<div class="game-grid"', s)


def _tv_record(networks, territory='NATIONAL', listed=None):
    return {'elias': '1', 'away': 'ATL', 'home': 'GB', 'networks': networks,
            'listed': listed if listed is not None else networks, 'territory': territory,
            'held_back': [] if networks else ['kickoff disagrees'], 'reported': []}


PRED = {'away': 'ATL', 'home': 'GB', 'model_a_home_win_prob': 0.75,
        'model_b_home_win_prob': 0.68}


def test_a_held_back_channel_never_reaches_the_page():
    """src/pipeline/tv_channels.py leaves `networks` empty when a channel fails a check
    and keeps what nfl.com listed under `listed`, for provenance only."""
    held = gd.build_games_js([PRED], {}, {}, {('GB', 'ATL'): _tv_record([], listed=['FOX'])})
    assert held[0]['tv'] is None and held[0]['tv_regional'] is False
    shown = gd.build_games_js([PRED], {}, {}, {('GB', 'ATL'): _tv_record(['FOX'], 'REGIONAL')})
    assert shown[0]['tv'] == 'FOX' and shown[0]['tv_regional'] is True
    national = gd.build_games_js([PRED], {}, {}, {('GB', 'ATL'): _tv_record(['NBC'], 'NATIONAL')})
    assert national[0]['tv'] == 'NBC' and national[0]['tv_regional'] is False, (
        'a national game is not regional just because it has a channel')
    assert gd.build_games_js([PRED], {})[0]['tv'] is None, 'no file, no channel'


def test_the_tv_folder_is_read_by_week_and_its_exceptions_file_is_not_a_week(tmp_path):
    (tmp_path / 'exceptions.json').write_text('{"exceptions": []}', encoding='utf-8')
    (tmp_path / '2026_week4.json').write_text(json.dumps(
        {'reads': [], 'changes': [], 'games': [_tv_record(['NBC']),
                                               {'elias': '2', 'networks': [],
                                                'held_back': ['no nflverse game has this id']}]}),
        encoding='utf-8')
    got = gd.load_tv(tmp_path)
    assert list(got) == [(2026, 4)]
    assert list(got[(2026, 4)]) == [('GB', 'ATL')], 'a record with no teams joins nothing'
    assert gd.load_tv(tmp_path / 'absent') == {}


# ---- the quarterbacks ------------------------------------------------------

QBS = dict(GAME, away_qb='Michael Penix Jr.', home_qb='Jordan Love',
           away_qb_basis='announced', home_qb_basis='override')


def test_quarterbacks_are_away_first_like_the_card():
    assert run(f'cardQbLine({j(QBS)})') == (
        'Quarterbacks: ATL <b>Michael Penix Jr.</b> · GB <b>Jordan Love</b>')


def test_a_fallback_quarterback_is_said_to_be_assumed():
    line = run(f'cardQbLine({j(dict(QBS, home_qb_basis="last_game"))})')
    assert line.endswith("GB <b>Jordan Love</b> (assumed: last game&#39;s starter)")
    assert 'assumed' not in line.split('·')[0], 'only the side that fell back says so'


def test_a_week_saved_before_names_were_kept_draws_no_line():
    assert run(f'cardQbLine({j(GAME)})') == ''
    assert run(f'cardQbLine({j(dict(QBS, home_qb=None))})').endswith('GB none on record')


def test_the_quarterbacks_reach_the_page():
    pred = dict(PRED, away_qb='Michael Penix Jr.', home_qb='Jordan Love',
                away_qb_basis='announced', home_qb_basis='last_game')
    g = gd.build_games_js([pred, PRED], {})
    assert (g[0]['away_qb'], g[0]['home_qb']) == ('Michael Penix Jr.', 'Jordan Love')
    assert (g[0]['away_qb_basis'], g[0]['home_qb_basis']) == ('announced', 'last_game')
    assert g[1]['away_qb'] is None and g[1]['home_qb'] is None, 'absent stays absent'


# ---- team news -------------------------------------------------------------

def team(qb='Jordan Love', changed_from=None, out=(), doubtful=(), report='published'):
    entry = {'qb': {'name': qb, 'basis': 'announced', 'changed_from': changed_from},
             'injury_report': report}
    if report == 'published':
        person = lambda n: {'name': n, 'position': 'WR', 'injury': 'Knee'}
        entry.update(out=[person(n) for n in out], doubtful=[person(n) for n in doubtful],
                     questionable_starters=3)
    return entry


def news(away, home):
    return {'read_at': '2026-09-24T12:00:00Z', 'teams': {'ATL': away, 'GB': home}}


def test_no_news_is_no_line():
    """Questionable players alone are not card news (Team Deep-Dive has
    them), and an unpublished report is not "nobody hurt": both draw nothing."""
    quiet = news(team(qb='Michael Penix Jr.'), team(report='not yet published'))
    assert run(f'cardNewsLine({j(GAME)}, {j(quiet)})') == ''
    assert run(f'cardNewsLine({j(GAME)}, null)') == ''


def test_a_starter_out_or_a_new_quarterback_makes_one_labelled_line():
    n = news(team(qb='Michael Penix Jr.', changed_from='Cooper Rush'),
             team(out=['Christian Watson'], doubtful=['Xavier McKinney']))
    assert run(f'cardNewsLine({j(GAME)}, {j(n)})') == (
        '<b>Team news</b> ATL: new QB · GB: Christian Watson out, Xavier McKinney doubtful')


def test_the_picks_quarterback_on_the_report_leads_the_line():
    n = news(team(qb='Michael Penix Jr.', changed_from='Cooper Rush',
                  doubtful=['Michael Penix Jr.', 'Drake London']), team())
    assert run(f'cardNewsLine({j(GAME)}, {j(n)})') == (
        '<b>Team news</b> ATL: QB Michael Penix Jr. doubtful, Drake London doubtful')


def test_more_than_two_starters_become_a_count():
    n = news(team(qb='Michael Penix Jr.'), team(out=['A One', 'B Two'], doubtful=['C Three']))
    assert run(f'cardNewsLine({j(GAME)}, {j(n)})') == (
        '<b>Team news</b> GB: 3 starters out or doubtful')


def test_news_leaves_the_card_once_the_game_is_over():
    n = news(team(qb='Michael Penix Jr.', changed_from='Cooper Rush'), team())
    assert run(f'cardNewsLine({j(dict(GAME, status="final"))}, {j(n)})') == ''
    assert run(f'cardNewsLine({j(dict(GAME, graded=True))}, {j(n)})') == ''


def test_names_are_escaped():
    n = news(team(qb='Michael Penix Jr.', out=['<img src=x>']), team())
    assert '&lt;img src=x&gt; out' in run(f'cardNewsLine({j(GAME)}, {j(n)})')
    assert '&lt;b&gt;' in run(f'cardQbLine({j(dict(QBS, away_qb="<b>"))})')
