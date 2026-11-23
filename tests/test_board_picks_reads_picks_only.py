"""The board-picks browser check reads registered picks only, never a shadow's records, and always finds a day
to compare.

tests/browser/check_board_picks.py imports Playwright, so it is read here as text: a game's pick is found through
`pick_files`, which keeps only a season folder (`predictions/<sport>/2026/`). A shadow's folder (`2026-v2`,
`2026-v3`) holds records with no `pick`; read as a pick, the check stopped with KeyError: 'pick_model' on #738.

Run with: pytest tests/test_board_picks_reads_picks_only.py -v
"""
import ast
import asyncio
import importlib.util
import json
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


# --- a board with no saved pick steps back to the latest day with one (2026-11-23) ---------------------------

SPEC = importlib.util.spec_from_file_location('check_board_picks', Path(__file__).resolve().parent / 'browser' /
                                              'check_board_picks.py')
cbp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cbp)


class Board:
    """A day board as the check drives it: weeks of days, each day its rows; the board opens on `day` of `week`.
    `chips=False` is the NFL's week board, which has no day strip."""

    def __init__(self, weeks, week, day, chips=True):
        self.weeks, self.week, self.day, self.chips = weeks, week, day, chips
        self.opened = [(week, day)]

    async def evaluate(self, script, sport):
        if script == cbp.CHIP_DAYS:
            return list(self.weeks[self.week]) if self.chips else []
        return self.weeks[self.week].get(self.day, [])

    async def wait_for_timeout(self, ms):
        return None

    def locator(self, selector):
        return Button(self, selector)


class Button:
    def __init__(self, board, selector):
        self.board, self.selector = board, selector

    async def count(self):
        return 1

    async def is_disabled(self):
        return self.selector == '#week-prev' and self.board.week == 0

    async def click(self):
        b = self.board
        if self.selector == '#week-prev':
            b.week -= 1
            b.day = sorted(b.weeks[b.week])[0]  # day_board.js defaultDay: the week's first day with games
        else:
            b.day = self.selector.split('data-day="')[1].split('"')[0]
        b.opened.append((b.week, b.day))


def saved(tmp_path, *ids):
    folder = tmp_path / 'nhl' / '2026'
    folder.mkdir(parents=True, exist_ok=True)
    for gid in ids:
        (folder / f'{gid}.json').write_text(json.dumps({'game_id': gid, 'home': 'BOS', 'away': 'TOR', 'pick': 'BOS',
                                                        'pick_model': 'model_a', 'model_a': 0.61}))
    return tmp_path


def row(gid, pick='BOS 61%'):
    return {'id': gid, 'pick': pick}


def run(board, pred):
    return asyncio.run(cbp.find_compared(board, 'nhl', pred))


def test_the_latest_day_first():
    assert cbp.days_back(['2026-11-16', '2026-11-22', '2026-11-18', '2026-11-22']) == [
        '2026-11-22', '2026-11-18', '2026-11-16']


def test_a_monday_just_after_midnight_finds_the_sunday_before(tmp_path):
    """2026-11-23 00:30 ET: the new week's Monday has no pick yet, and the week before opens on its Monday,
    whose games went unpicked (#769). The check compares Sunday's."""
    weeks = [{'2026-11-16': [row('m1', '—'), row('m2', '—')], '2026-11-22': [row('s1'), row('s2')]},
             {'2026-11-23': [row('n1', '—')]}]
    board = Board(weeks, 1, '2026-11-23')
    report, compared = run(board, saved(tmp_path, 's1', 's2'))
    assert (report, compared) == ([], ['s1', 's2'])


def test_an_earlier_day_this_week_comes_before_a_week_back(tmp_path):
    weeks = [{'2026-11-16': [row('old')]}, {'2026-11-23': [row('a')], '2026-11-24': [row('b', '—')]}]
    board = Board(weeks, 1, '2026-11-24')
    assert run(board, saved(tmp_path, 'a', 'old'))[1] == ['a']
    assert all(week == 1 for week, _ in board.opened)


def test_the_latest_day_with_a_pick_wins_over_an_older_one(tmp_path):
    weeks = [{'2026-11-16': [row('mon')], '2026-11-22': [row('sun')]}, {'2026-11-23': []}]
    assert run(Board(weeks, 1, '2026-11-23'), saved(tmp_path, 'mon', 'sun'))[1] == ['sun']


def test_a_week_board_steps_back_a_week(tmp_path):
    """The NFL's board has no day strip: a week back, as before."""
    weeks = [{'w10': [row('w10g')]}, {'w11': [row('w11g', '—')]}]
    board = Board(weeks, 1, 'w11', chips=False)
    assert run(board, saved(tmp_path, 'w10g'))[1] == ['w10g'] and board.week == 0


def test_every_view_it_opens_is_checked(tmp_path):
    """A row on the way that shows a pick no file holds is still reported."""
    weeks = [{'2026-11-22': [row('ok')]}, {'2026-11-23': [row('ghost')], '2026-11-24': [row('later', '—')]}]
    report, compared = run(Board(weeks, 1, '2026-11-24'), saved(tmp_path, 'ok'))
    assert compared == ['ok'] and report == ['nhl ghost: the row shows "BOS 61%" and no pick was saved']


def test_it_stops_at_the_first_week_and_after_weeks_back(tmp_path):
    weeks = [{'d1': [row('x', '—')]}, {'d2': [row('y', '—')]}]
    board = Board(weeks, 1, 'd2')
    assert run(board, saved(tmp_path)) == ([], [])
    assert board.week == 0
