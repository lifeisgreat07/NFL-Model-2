"""The day sports share one copy of their backtest, drift, pick and rating code (Stage 87 item 2).

The NHL's and NBA's backtest.py, drift.py, daily.py and ratings.py carried
functions byte for byte, so a fix to one sport could miss the other. Those
live in src/core/day_backtest.py, day_drift.py, day_picks.py and
day_ratings.py; each sport module re-exports them. ridge_ratings and grade
were not quite identical: the NHL's ridge took a default alpha, and the NBA's
rows carry market_source. Both are one copy now, with the NHL passing its
alpha and the NBA its extra field. looks, flags and drift_rows still differ
on purpose (the NBA holds each look to its own picks' baselines, Stage 85
item 2), so they stay in each sport.

Run with: pytest tests/test_core_python.py -v
"""
import ast
import builtins
import importlib
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULES = {'backtest': 'day_backtest', 'drift': 'day_drift', 'daily': 'day_picks', 'ratings': 'day_ratings'}
MOVED = {
    'day_backtest': ['base_rate', 'estimator', 'label', 'log_losses', 'scores', 'walk_forward'],
    'day_drift': ['per_game_log_loss', 'lower_bound', 'next_look'],
    'day_picks': ['save_once', 'missed', 'missed_line', 'grade'],
    'day_ratings': ['weights', 'ridge_ratings'],
}
BUILTIN = set(dir(builtins)) - {'__file__', '__name__'}


def tops(path):
    src = path.read_text(encoding='utf-8').replace('\r\n', '\n')
    defs, funcs = {}, {}
    for n in ast.parse(src).body:
        text = ast.get_source_segment(src, n)
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            defs[n.name] = (text, n)
            if isinstance(n, ast.FunctionDef):
                funcs[n.name] = (text, n)
        elif isinstance(n, (ast.Assign, ast.AnnAssign)):
            for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                for x in ast.walk(t):
                    if isinstance(x, ast.Name):
                        defs[x.id] = (text, n)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                defs[(a.asname or a.name).split('.')[0]] = (text, n)
    return defs, funcs


def reads(node):
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return set()
    local = set()
    if isinstance(node, ast.FunctionDef):
        local = {a.arg for a in ast.walk(node.args) if isinstance(a, ast.arg)}
        local |= {x.id for x in ast.walk(node) if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store)}
    return {x.id for x in ast.walk(node) if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load)} - local - BUILTIN


def same(name, a, b, seen):
    """A module-level name means the same in both modules: same text, and everything it reads the same."""
    if name in ('__file__', '__name__'):
        return False
    if name in seen:
        return True
    seen.add(name)
    na, nb = a.get(name), b.get(name)
    if na is None and nb is None:
        return True
    if na is None or nb is None or na[0] != nb[0]:
        return False
    return all(same(g, a, b, seen) for g in reads(na[1]))


def copies(module):
    """Functions the two sports' copies of `module` define identically, reading only the same names."""
    da, fa = tops(ROOT / 'src' / 'sports' / 'nhl' / f'{module}.py')
    db, fb = tops(ROOT / 'src' / 'sports' / 'nba' / f'{module}.py')
    return sorted(n for n in set(fa) & set(fb)
                  if fa[n][0] == fb[n][0] and all(same(g, da, db, set()) for g in reads(fa[n][1])))


@pytest.mark.parametrize('module', sorted(MODULES))
def test_no_function_is_copied_between_the_sports(module):
    assert copies(module) == [], f'move these to src/core/{MODULES[module]}.py: {copies(module)}'


def test_a_copy_is_found_when_there_is_one(tmp_path, monkeypatch):
    """The check above is not vacuous: two sport modules with one shared function are a copy, and one that
    reads a differing constant is not."""
    for sport, path in (('nhl', 'a'), ('nba', 'b')):
        d = tmp_path / 'src' / 'sports' / sport
        d.mkdir(parents=True)
        (d / 'm.py').write_text(f"P = '{path}'\nK = 2\n\n\ndef f(x):\n    return x * K\n\n\ndef g():\n    return P\n",
                                encoding='utf-8')
    monkeypatch.setattr(__import__(__name__), 'ROOT', tmp_path)
    assert copies('m') == ['f']


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_each_sport_uses_the_one_copy(sport):
    for module, core_name in MODULES.items():
        mod = importlib.import_module(f'src.sports.{sport}.{module}')
        core = importlib.import_module(f'src.core.{core_name}')
        for name in MOVED[core_name]:
            if (sport, name) == ('nba', 'grade'):
                continue  # a wrapper adding market_source, checked below
            assert getattr(mod, name) is getattr(core, name), f'{sport}.{module}.{name} is not src/core/{core_name}'


def test_each_sports_grade_rows_keep_their_fields(tmp_path):
    """The NHL's rows are what they were (no market_source); the NBA's carry it, in the same place."""
    from src.sports.nba import daily as nba
    from src.sports.nhl import daily as nhl
    (tmp_path / 'g1.json').write_text('{"game_id": "g1", "pick": "BOS", "market_source": "kalshi", '
                                      '"saved_utc": "2026-11-01T12:00:00Z"}', encoding='utf-8')
    sched = pd.DataFrame([{'game_id': 'g1', 'status': 'final', 'home': 'BOS', 'away': 'NYR', 'home_win': 1.0}])
    assert list(nhl.grade(tmp_path, sched)[0]) == ['game_id', 'pick', 'result', 'saved_utc']
    row = nba.grade(tmp_path, sched)[0]
    assert list(row) == ['game_id', 'pick', 'result', 'market_source', 'saved_utc']
    assert row['market_source'] == 'kalshi' and row['result'] == 'correct'


def test_the_nhl_ratings_pass_their_own_alpha():
    src = (ROOT / 'src' / 'sports' / 'nhl' / 'ratings.py').read_text(encoding='utf-8')
    assert "ridge_ratings(train, 'goal_margin', w, RIDGE)" in src
    assert "ridge_ratings(train, 'shot_margin', w, RIDGE)" in src
