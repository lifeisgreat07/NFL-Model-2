"""Stage 39 item 4: the NFL page says the ratings freeze through the playoffs,
and that stays true.

`src/sports/nfl/ratings_engine.prep_plays` keeps regular-season plays only
(nflverse `season_type == 'REG'`), so team and QB ratings stop moving after
week 18. Mark chose to disclose it rather than change it (2026-10-09): a
change would be a model change that about 13 playoff games a season could
never test. This holds the sentence and the filter together: if the
ratings ever read playoff plays, the page's sentence turns false and this
fails, and if the sentence goes, so does the disclosure.

Run with: pytest tests/test_ratings_freeze_disclosed.py -v
"""
import re
from pathlib import Path

import pandas as pd

from src.sports.nfl import ratings_engine

ROOT = Path(__file__).resolve().parents[1]
BODY = ROOT / 'src' / 'dashboard' / 'body.html'


def test_the_ratings_read_regular_season_plays_only():
    """Executed, not read: a playoff play never reaches the ratings."""
    raw = pd.DataFrame([
        {'season': 2026, 'week': 18, 'season_type': 'REG', 'pass': 1, 'rush': 0, 'epa': 0.4,
         'posteam': 'KC', 'defteam': 'LV'},
        {'season': 2026, 'week': 19, 'season_type': 'POST', 'pass': 1, 'rush': 0, 'epa': -0.9,
         'posteam': 'KC', 'defteam': 'BUF'},
    ])
    plays, weeks, _ = ratings_engine.prep_plays(raw)
    assert set(plays['season_type']) == {'REG'}
    assert weeks == [(2026, 18)], 'a playoff week entered the ratings: the page\'s freeze sentence is now false'


def test_the_qb_ratings_read_regular_season_dropbacks_only():
    """The QB ratings filter on their own (`build_qb_ratings`), so the
    sentence's "and quarterback's" needs its own check."""
    raw = pd.DataFrame([
        {'season': 2026, 'week': 18, 'season_type': 'REG', 'posteam': 'KC', 'qb_dropback': 1, 'qb_epa': 0.3,
         'passer_player_id': 'qb1', 'passer_player_name': 'P. Mahomes'},
        {'season': 2026, 'week': 19, 'season_type': 'POST', 'posteam': 'KC', 'qb_dropback': 1, 'qb_epa': -1.2,
         'passer_player_id': 'qb1', 'passer_player_name': 'P. Mahomes'},
    ])
    qb = ratings_engine.build_qb_ratings(raw)
    assert qb['week_keys'] == [(2026, 18)], 'a playoff dropback entered the QB ratings'


def test_the_methodology_page_says_so():
    body = BODY.read_text(encoding='utf-8')
    m = re.search(r'<p[^>]*id="ratings-freeze"[^>]*>(.*?)</p>', body, re.S)
    assert m, 'the freeze disclosure is gone from the Methodology page'
    text = m.group(1)
    assert 'The ratings freeze through the playoffs.' in text
    assert 'regular-season plays only' in text and 'week 18' in text
    assert 'filtered to regular-season pass/rush attempts' in body
