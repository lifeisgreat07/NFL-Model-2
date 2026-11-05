"""
README's "Results at a glance": one table, each sport's backtest and live
record, Model B against the market and the base rate (Stage 89 item 1, the
2026-11-02 review).

Every cell is computed from committed files, never typed:

- the NFL's backtest from `data/nfl/calibration.json`, and its live season
  from the graded week files through the week the table names;
- the NHL's and NBA's backtests from their registered confirmation results,
  and their live seasons by the registered forward test's own functions
  (`src/core/forward_test.py`) on the saved picks whose games were final by
  the day the table names.

A pick is never rewritten and a final score does not change, so a live row
recomputed for its stated week or day gives the same figures however much
later it is checked; `tests/test_results_glance.py` does that. The NFL
publishes no base rate, so its row says so rather than inventing one.

    python -m src.site.glance            # print the table for the latest graded data
    python -m src.site.glance --write    # and put it in README.md between the markers

Only src/site sees more than one sport (src/core/isolation.py).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.core import forward_test

ROOT = Path(__file__).resolve().parents[2]
SEASON = 2026
START, END = '<!-- glance:start -->', '<!-- glance:end -->'
NOT_PUBLISHED = 'not published'

Cell = dict[str, Any] | None


def _score(p: pd.Series, y: pd.Series) -> dict[str, Any]:
    return forward_test.score(p.to_numpy(float), y.to_numpy(float))


# --- the NFL --------------------------------------------------------------------------------

def nfl_backtest(root: Path = ROOT) -> dict[str, Any]:
    cal = json.loads((root / 'data' / 'nfl' / 'calibration.json').read_text(encoding='utf-8'))
    seasons = cal['backtest_seasons']
    m = cal['models']
    return {'label': f'Backtest, {seasons[0]}-{seasons[-1]} seasons',
            'model_b': {'log_loss': m['model_b']['metrics']['log_loss'], 'games': m['model_b']['metrics']['n']},
            'market': {'log_loss': m['market']['metrics']['log_loss'], 'games': m['market']['metrics']['n']},
            'base_rate': None}


def nfl_weeks(root: Path = ROOT) -> list[int]:
    return sorted(int(p.stem.split('_week')[1].split('_')[0])
                  for p in (root / 'results' / 'nfl').glob(f'{SEASON}_week*_graded.json'))


def nfl_live(through_week: int, root: Path = ROOT) -> dict[str, Any]:
    rows = []
    for week in range(1, through_week + 1):
        path = root / 'results' / 'nfl' / f'{SEASON}_week{week}_graded.json'
        if path.exists():
            rows.extend(json.loads(path.read_text(encoding='utf-8')))
    frame = pd.DataFrame(rows)
    frame = frame[frame['actual_home_win'].isin([0, 1])]
    out: dict[str, Any] = {'label': f'Live {SEASON}, weeks 1-{through_week}', 'base_rate': None}
    for name, col in (('model_b', 'model_b_home_win_prob'), ('market', 'market_prob_home')):
        have = frame[frame[col].notna()]
        out[name] = _score(have[col], have['actual_home_win'])
    return out


# --- the NHL and the NBA ------------------------------------------------------------------------

STAGES = {'nhl': ('stage56', 'stage58'), 'nba': ('stage61', 'stage65')}


def day_backtest(sport: str, root: Path = ROOT) -> dict[str, Any]:
    stage = STAGES[sport][0]
    conf = json.loads((root / 'experiments' / sport / stage / 'results' / 'confirmation.json').read_text(encoding='utf-8'))
    s = conf['seasons']
    label = ' and '.join(f'{y}-{(y + 1) % 100:02d}' for y in s)
    return {'label': f'Backtest, {label}',
            **{k: {'log_loss': conf['scores'][k]['log_loss'], 'games': conf['scores'][k]['games']}
               for k in ('model_b', 'market', 'base_rate')}}


def played(sport: str, root: Path = ROOT) -> pd.DataFrame:
    """Every game the daily run knows (day, home_score, away_score): the
    backtest's history from its first training season, and this season's."""
    hist = root / 'data' / sport / 'history'
    if sport == 'nhl':
        from src.sports.nhl import backtest as nhl
        first = nhl.registry()['protocol']['training_from_season']
        past = nhl.load_history(first, SEASON - 1)
        cur = pd.read_csv(hist / f'boxscores_{SEASON}.csv', dtype={'game_id': str})
        games = pd.concat([past, cur], ignore_index=True)
        return games.assign(day=pd.to_datetime(games['game_date']))[['day', 'home_score', 'away_score']]
    from src.sports.nba import backtest as nba
    first = nba.registry()['protocol']['training_from_season']
    past_games, _ = nba.load_history(first, SEASON - 1)
    cur = pd.read_csv(hist / f'games_{SEASON}.csv', dtype={'game_id': str})
    games = pd.concat([past_games, cur], ignore_index=True)
    return games.assign(day=pd.to_datetime(games['slate']))[['day', 'home_score', 'away_score']]


def finals(sport: str, through_day: str, root: Path = ROOT) -> pd.DataFrame:
    sched = pd.DataFrame(json.loads((root / 'results' / sport / f'schedule_{SEASON}.json')
                                    .read_text(encoding='utf-8'))['games'])
    done = sched[(sched['status'] == 'final') & (sched['slate'] <= through_day)].copy()
    done['home_win'] = np.where(done['home_score'] > done['away_score'], 1.0, 0.0)
    return done.assign(game_id=done['game_id'].astype(str))[['game_id', 'slate', 'home_win']]


def day_live(sport: str, through_day: str, root: Path = ROOT, games: pd.DataFrame | None = None) -> dict[str, Any]:
    """The registered forward test's scores on the picks final by `through_day`."""
    done = finals(sport, through_day, root)
    rates = forward_test.base_rates([str(d) for d in done['slate']], played(sport, root) if games is None else games)
    frame = forward_test.rows(forward_test.read_picks(root / 'predictions' / sport / str(SEASON)), done, rates)
    scores = forward_test.scores(frame)
    return {'label': f'Live {SEASON}-{(SEASON + 1) % 100:02d}, through {through_day}',
            **{k: scores[k] for k in ('model_b', 'market', 'base_rate')}}


def forward_through(sport: str, root: Path = ROOT) -> str:
    return str(json.loads((root / 'results' / sport / f'forward_{SEASON}.json').read_text(encoding='utf-8'))['through'])


# --- the table --------------------------------------------------------------------------------

def cell(c: Cell) -> str:
    if c is None:
        return NOT_PUBLISHED
    return f"{c['log_loss']:.4f} ({c['games']:,})"


def table(rows: list[tuple[str, dict[str, Any]]]) -> str:
    out = ['| Sport | Record | Model B | Market | Base rate |', '|---|---|---|---|---|']
    for sport, r in rows:
        out.append(f"| {sport} | {r['label']} | {cell(r['model_b'])} | {cell(r['market'])} | {cell(r['base_rate'])} |")
    return '\n'.join(out)


def block(root: Path = ROOT) -> str:
    week = nfl_weeks(root)[-1]
    rows = [('NFL', nfl_backtest(root)), ('NFL', nfl_live(week, root))]
    for sport in ('nhl', 'nba'):
        rows += [(sport.upper(), day_backtest(sport, root)), (sport.upper(), day_live(sport, forward_through(sport, root), root))]
    return (f'{START}\n' + table(rows) + '\n\nLog loss, lower is better, with the games each forecaster was scored on in '
            'brackets: a model or the market is scored only on the games it had a number for. The base rate is the '
            'home side\'s share of wins in every earlier game of the sport\'s history; the NFL\'s backtest and live '
            'record publish none. '
            'The live rows are as of the week or day they name, and recomputed from the saved picks by '
            '`tests/test_results_glance.py`; each sport\'s page has today\'s.\n' + END)


def write(root: Path = ROOT) -> str:
    readme = root / 'README.md'
    text = readme.read_text(encoding='utf-8')
    new = text[:text.index(START)] + block(root) + text[text.index(END) + len(END):]
    readme.write_text(new, encoding='utf-8')
    return new


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='README\'s results at a glance')
    ap.add_argument('--write', action='store_true')
    args = ap.parse_args(argv)
    if args.write:
        write()
    print(block())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
