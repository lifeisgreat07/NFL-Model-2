"""Day-sport picks say what trained them; NFL picks say their game type (Stage 68 item 27, E26).

Run with: pytest tests/test_pick_provenance.py -v
"""
from pathlib import Path

import numpy as np
import pandas as pd

from src.core.provenance import training

ROOT = Path(__file__).resolve().parents[1]


def test_the_record_is_the_fitted_table():
    table = pd.DataFrame({'day': pd.to_datetime(['2024-10-01', '2026-04-15', '2025-01-02']),
                          'home_prob': [0.6, np.nan, 0.4]})
    assert training(table, 2015) == {
        'training_through': '2026-04-15',
        'data_provenance': {'training_from_season': 2015, 'training_games': 3, 'training_games_priced': 2}}


def test_an_empty_table_says_so():
    out = training(pd.DataFrame({'day': pd.to_datetime([]), 'home_prob': []}), 2019)
    assert out['training_through'] is None and out['data_provenance']['training_games'] == 0


def test_both_day_sports_save_it_with_every_pick():
    for sport, call in (('nhl', 'injury_list) | trained\n'), ('nba', 'injury_list, now) | trained\n')):
        src = (ROOT / 'src' / 'sports' / sport / 'daily.py').read_text(encoding='utf-8')
        assert 'trained = training(table, first)' in src, sport
        assert call in src, sport


def test_nfl_picks_carry_game_type():
    src = (ROOT / 'src' / 'sports' / 'nfl' / 'weekly_update.py').read_text(encoding='utf-8')
    assert "'game_type': str(g['game_type']) if pd.notna(g.get('game_type')) else None," in src
