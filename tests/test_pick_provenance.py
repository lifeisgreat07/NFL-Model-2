"""Day-sport picks say what trained them; NFL picks say their game type (Stage 68 item 27, E26).

Run with: pytest tests/test_pick_provenance.py -v
"""
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from src.core.provenance import code_identity, ids_digest, training

ROOT = Path(__file__).resolve().parents[1]


def test_the_record_is_the_fitted_table():
    table = pd.DataFrame({'day': pd.to_datetime(['2024-10-01', '2026-04-15', '2025-01-02']),
                          'home_prob': [0.6, np.nan, 0.4]})
    assert training(table, 2015) == {
        'training_through': '2026-04-15',
        'data_provenance': {'training_from_season': 2015, 'training_games': 3, 'training_games_priced': 2,
                            'training_ids_sha256': None}}


def test_an_empty_table_says_so():
    out = training(pd.DataFrame({'day': pd.to_datetime([]), 'home_prob': []}), 2019)
    assert out['training_through'] is None and out['data_provenance']['training_games'] == 0


def test_both_day_sports_save_it_with_every_pick():
    for sport, call in (('nhl', 'injury_list) | trained\n'), ('nba', 'injury_list, now, why) | trained\n')):
        src = (ROOT / 'src' / 'sports' / sport / 'daily.py').read_text(encoding='utf-8')
        # Stage 85 item 4: the provenance comes from the rows the models were
        # fitted on, strictly before the slate day (fit_before).
        assert 'training(before, first)' in src and 'fit_before(table, day,' in src, sport
        assert call in src, sport


def test_nfl_picks_carry_game_type():
    src = (ROOT / 'src' / 'sports' / 'nfl' / 'weekly_update.py').read_text(encoding='utf-8')
    assert "'game_type': str(g['game_type']) if pd.notna(g.get('game_type')) else None," in src


# --- Stage 95 items 39 and 40 (audit 7, M5, M8, M9) -------------------------------------------------------


def test_the_training_ids_are_a_digest_of_the_sorted_ids():
    table = pd.DataFrame({'day': pd.to_datetime(['2026-10-01', '2026-10-02']), 'home_prob': [0.5, 0.6],
                          'game_id': ['401b', '401a']})
    got = training(table, 2024)['data_provenance']['training_ids_sha256']
    assert got == hashlib.sha256(b'401a\n401b').hexdigest()
    assert got == training(table.iloc[::-1], 2024)['data_provenance']['training_ids_sha256'], 'order matters not'
    assert got != training(table.iloc[:1], 2024)['data_provenance']['training_ids_sha256'], 'one game fewer differs'
    assert ids_digest([]) is None


def test_the_code_digest_follows_the_code_and_not_the_line_endings(tmp_path, monkeypatch):
    for rel, text in (('src/core/a.py', 'x = 1\n'), ('src/sports/nhl/b.py', 'y = 2\n'), ('src/sports/nba/c.py', 'z\n')):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_bytes(text.encode())
    monkeypatch.setenv('GITHUB_SHA', 'abc123')
    code_identity.cache_clear()
    first = code_identity('nhl', tmp_path)
    assert first['code_commit'] == 'abc123'
    (tmp_path / 'src/core/a.py').write_bytes(b'x = 1\r\n')
    code_identity.cache_clear()
    assert code_identity('nhl', tmp_path)['code_sha256'] == first['code_sha256'], 'CRLF is the same code'
    (tmp_path / 'src/sports/nba/c.py').write_bytes(b'changed\n')
    code_identity.cache_clear()
    assert code_identity('nhl', tmp_path)['code_sha256'] == first['code_sha256'], "another sport's code is not this one's"
    (tmp_path / 'src/sports/nhl/b.py').write_bytes(b'y = 3\n')
    code_identity.cache_clear()
    assert code_identity('nhl', tmp_path)['code_sha256'] != first['code_sha256']
    code_identity.cache_clear()


def test_both_day_sports_save_their_code_identity_with_every_pick():
    for sport in ('nhl', 'nba'):
        src = (ROOT / 'src' / 'sports' / sport / 'daily.py').read_text(encoding='utf-8')
        assert f"trained = trained | code_identity('{sport}')" in src, sport
