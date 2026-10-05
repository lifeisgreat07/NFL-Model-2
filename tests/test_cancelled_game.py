"""A cancelled game says "Cancelled", is graded for nobody, and closes (Stage 39).

Mark's call, 2026-10-05 (#280's finding): the card stays and shows its pick,
labelled "Cancelled"; the game is never graded and is left out of every count
and accuracy figure. Grading already left it out (tests/test_league_scenarios.py:
a game with no score is never graded). What was missing is the state: on its
own a cancelled game read "started" for the rest of the season and held its
week open for every weekend refresh, TV read and team-news read after it.

nflverse has no cancelled flag, and "no score a while after kickoff" is also
what a late feed looks like, so a cancellation is recorded, not inferred:
data/cancelled_games.json, one entry per game with a link to the source, the
way a QB override is. An unlisted game with no score long after kickoff is
printed as a warning so the file gets written.

Run with: pytest tests/test_cancelled_game.py -v
"""
import json
import re
import shutil
import subprocess
from datetime import UTC, datetime

import pandas as pd
import pytest

from src.pipeline import weekend_refresh as wr
from src.pipeline.template_parts import JOINED_TEMPLATE

NODE = shutil.which('node')
# 2022 week 17's game, as the fixture: Bills at Bengals, Monday night.
ENTRY = {'season': 2026, 'week': 5, 'away': 'BUF', 'home': 'CIN',
         'source': 'https://operations.nfl.com/example-announcement'}


def _write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding='utf-8')


def row(away='BUF', home='CIN', gameday='2026-10-05', gametime='20:15', away_score=None, home_score=None):
    return {'away_team': away, 'home_team': home, 'gameday': gameday, 'gametime': gametime,
            'away_score': away_score, 'home_score': home_score, 'spread_line': 1.0, 'week': 5}


TUESDAY = datetime(2026, 10, 6, 11, 0, tzinfo=UTC)
THURSDAY = datetime(2026, 10, 8, 11, 0, tzinfo=UTC)


# --- the file -----------------------------------------------------------------

def test_no_file_means_no_cancellations(tmp_path):
    assert wr.load_cancelled(tmp_path / 'cancelled_games.json') == set()


def test_a_listed_game_is_read(tmp_path):
    _write(tmp_path / 'c.json', [ENTRY])
    assert wr.load_cancelled(tmp_path / 'c.json') == {(2026, 5, 'BUF', 'CIN')}


@pytest.mark.parametrize('bad', [
    {k: v for k, v in ENTRY.items() if k != 'source'},
    dict(ENTRY, source='the league said so'),
], ids=['no-source', 'source-not-a-link'])
def test_an_entry_without_a_linked_source_fails_the_run(tmp_path, bad):
    """A cancellation takes a game out of every count; not on an unsourced word."""
    _write(tmp_path / 'c.json', [bad])
    with pytest.raises(wr.CancelledGamesError):
        wr.load_cancelled(tmp_path / 'c.json')


def test_a_file_that_is_not_a_list_fails(tmp_path):
    _write(tmp_path / 'c.json', ENTRY)
    with pytest.raises(wr.CancelledGamesError):
        wr.load_cancelled(tmp_path / 'c.json')


# --- the state ----------------------------------------------------------------

def test_a_listed_game_with_no_score_is_cancelled_not_started():
    assert wr.game_status(pd.Series(row()), TUESDAY) == 'started'
    assert wr.game_status(pd.Series(row()), TUESDAY, cancelled=True) == 'cancelled'


def test_a_score_wins_over_a_listing():
    """A listed game that has a score was played after all."""
    assert wr.game_status(pd.Series(row(away_score=17, home_score=20)), TUESDAY, cancelled=True) == 'final'


def test_a_cancelled_game_no_longer_holds_its_week_open(tmp_path):
    preds, results = tmp_path / 'predictions', tmp_path / 'results'
    _write(preds / '2026_week5.json', [{'away': 'BUF', 'home': 'CIN'}, {'away': 'NE', 'home': 'NYJ'}])
    _write(results / '2026_week5_graded.json', [{'away': 'NE', 'home': 'NYJ'}])
    assert wr.weeks_to_refresh(2026, preds, results, cancelled=set()) == [5]
    assert wr.weeks_to_refresh(2026, preds, results, cancelled={(2026, 5, 'BUF', 'CIN')}) == []


def test_a_cancellation_in_another_week_does_not_close_this_one(tmp_path):
    preds, results = tmp_path / 'predictions', tmp_path / 'results'
    _write(preds / '2026_week5.json', [{'away': 'BUF', 'home': 'CIN'}, {'away': 'NE', 'home': 'NYJ'}])
    _write(results / '2026_week5_graded.json', [{'away': 'NE', 'home': 'NYJ'}])
    assert wr.weeks_to_refresh(2026, preds, results, cancelled={(2026, 6, 'BUF', 'CIN')}) == [5]


def test_the_refresh_writes_cancelled_into_the_snapshot(tmp_path):
    preds, results, status = tmp_path / 'predictions', tmp_path / 'results', tmp_path / 'status'
    _write(preds / '2026_week5.json', [{'away': 'BUF', 'home': 'CIN'}, {'away': 'NE', 'home': 'NYJ'}])
    load = lambda season: pd.DataFrame([row(), row('NE', 'NYJ', gameday='2026-10-04', gametime='13:00',
                                                   away_score=10, home_score=13)])
    assert wr.main(['--season', '2026'], now=TUESDAY, load=load, pred_dir=preds, results_dir=results,
                   status_dir=status, snapshot=lambda *a: None,
                   cancelled={(2026, 5, 'BUF', 'CIN')}) == 0
    games = json.loads((status / '2026_week5.json').read_text(encoding='utf-8'))['games']
    assert [g['status'] for g in games] == ['cancelled', 'final']
    assert games[0]['away_score'] is None and games[0]['home_score'] is None


# --- the nudge ----------------------------------------------------------------

def test_an_unlisted_game_long_without_a_score_is_flagged():
    preds = [{'away': 'BUF', 'home': 'CIN'}]
    rows = pd.DataFrame([row()])
    assert wr.overdue(preds, rows, THURSDAY) == [('BUF', 'CIN')]
    assert wr.overdue(preds, rows, TUESDAY) == [], 'eleven hours is a late feed, not a cancellation'
    assert wr.overdue(preds, rows, THURSDAY, {('BUF', 'CIN')}) == [], 'a listed game is settled'
    scored = pd.DataFrame([row(away_score=17, home_score=20)])
    assert wr.overdue(preds, scored, THURSDAY) == []


def test_the_refresh_prints_the_nudge(tmp_path, capsys):
    preds, results, status = tmp_path / 'predictions', tmp_path / 'results', tmp_path / 'status'
    _write(preds / '2026_week5.json', [{'away': 'BUF', 'home': 'CIN'}])
    wr.main(['--season', '2026'], now=THURSDAY, load=lambda s: pd.DataFrame([row()]), pred_dir=preds,
            results_dir=results, status_dir=status, snapshot=lambda *a: None, cancelled=set())
    out = capsys.readouterr().out
    assert 'BUF at CIN kicked off over 36 hours ago with no score' in out
    assert 'data/cancelled_games.json' in out


# --- the card -----------------------------------------------------------------

def function_source(src, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def test_the_card_says_cancelled_and_not_graded():
    if not NODE:
        pytest.skip('node not available')
    src = JOINED_TEMPLATE.read_text(encoding='utf-8')
    case = {'away': 'BUF', 'home': 'CIN', 'status': 'cancelled', 'graded': False}
    js = (function_source(src, 'gameHasScore') + function_source(src, 'cardStatusLine')
          + f'\nprocess.stdout.write(cardStatusLine({json.dumps(case)}));')
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    assert r.stdout == 'Cancelled · not played, so not graded'


def test_a_cancelled_card_drops_its_channel_and_news():
    """Where to watch and who is hurt are moot for a game nobody will play,
    as they are once a game is final (rendered and looked at, 2026-10-05:
    the first version still showed ESPN and the injury list)."""
    if not NODE:
        pytest.skip('node not available')
    src = JOINED_TEMPLATE.read_text(encoding='utf-8')
    case = {'away': 'ATL', 'home': 'NO', 'status': 'cancelled', 'graded': False, 'tv': 'ESPN'}
    news = {'teams': {'NO': {'out': [{'name': 'A Player'}]}}}
    js = (function_source(src, 'escapeHtml') + function_source(src, 'cardTvPill')
          + f'\nconst g={json.dumps(case)};'
          + 'process.stdout.write(JSON.stringify([cardTvPill(g), cardTvPill(Object.assign({}, g, {status: "upcoming"}))]));')
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    cancelled, upcoming = json.loads(r.stdout)
    assert cancelled == '' and 'ESPN' in upcoming
    news_src = function_source(src, 'cardNewsLine')
    assert "g.status === 'cancelled'" in news_src.split('\n')[1], news_src.split('\n')[1]
    assert news  # the news shape the line would otherwise read
