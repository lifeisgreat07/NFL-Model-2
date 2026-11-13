"""The board-picks browser check reads registered picks only, never a shadow's records.

tests/browser/check_board_picks.py imports Playwright, so it is read here as text: a game's pick is found through
`pick_files`, which keeps only a season folder (`predictions/<sport>/2026/`). A shadow's folder (`2026-v2`,
`2026-v3`) holds records with no `pick`; read as a pick, the check stopped with KeyError: 'pick_model' on #738.

Run with: pytest tests/test_board_picks_reads_picks_only.py -v
"""
import ast
from pathlib import Path

SRC = (Path(__file__).resolve().parent / 'browser' / 'check_board_picks.py').read_text(encoding='utf-8')


def test_a_pick_is_read_from_a_season_folder_only():
    tree = ast.parse(SRC)
    [fn] = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'pick_files']
    body = ast.get_source_segment(SRC, fn)
    assert "p.parent.name.isdigit()" in body


def test_every_lookup_of_a_saved_pick_goes_through_it():
    assert SRC.count(".glob(f'*/{gid}.json')") == 1, 'only inside pick_files'
    assert SRC.count('pick_files(pred, sport, gid)') == 3, 'its definition and its two callers'
