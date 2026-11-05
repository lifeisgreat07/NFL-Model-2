"""The cross-sport track record (Stage 90 item 1, the 2026-11-02 review).

For each sport, three forecasters side by side, live this season beside the
backtest each was chosen on: Model B (the pick), the betting market, and the
base rate (the home side's long-run win rate, the forecast that knows nothing
about the game). Log loss for both, and the live Brier score; lower is better
for both, and a win-loss record means little until it is set against these.

Every figure is read from a committed file, nothing is fitted here:

- NHL and NBA, live: results/<sport>/forward_<season>.json, written by the
  daily run (src/core/forward_test.py), with its calibration slope for Model B.
- NHL and NBA, backtest: the confirmation seasons each sport's registry names
  (experiments/nhl/stage56, experiments/nba/stage61).
- NFL, live: every graded week of the season (results/nfl/*_graded.json),
  scored here, games with no market price left out of the market's row only.
- NFL, backtest: data/nfl/calibration.json (the 2022-2025 seasons), whose
  base rate is the home side's win rate there, used as the live base-rate
  forecast too. Its model is v2.4; this season's picks are v2.5 and v2.6
  (the page says so).
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EPS = 1e-15
FORECASTERS = (('model_b', 'Model B'), ('market', 'Market'), ('base_rate', 'Base rate'))
#: Each day sport's backtest: the confirmation seasons its registry names.
CONFIRMATION = {'nhl': 'experiments/nhl/stage56/results/confirmation.json',
                'nba': 'experiments/nba/stage61/results/confirmation.json'}


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def log_loss(p: float, y: int) -> float:
    q = min(max(p, EPS), 1 - EPS)
    return -math.log(q if y == 1 else 1 - q)


def _row(log: float | None, brier: float | None, games: int) -> dict[str, Any]:
    return {'log_loss': None if log is None else round(log, 4),
            'brier': None if brier is None else round(brier, 4), 'games': games}


def day_sport(sport: str, root: Path = ROOT) -> dict[str, Any] | None:
    """The NHL's or the NBA's live and backtest figures, or None before a forward-test file exists."""
    folder = root / 'results' / sport
    files = sorted(folder.glob('forward_*.json'), key=lambda p: p.stem) if folder.is_dir() else []
    files = [p for p in files if re.fullmatch(r'forward_\d{4}', p.stem)]
    if not files:
        return None
    fwd = json.loads(files[-1].read_text(encoding='utf-8'))
    back = (_read(root / CONFIRMATION[sport]) or {}).get('scores', {})
    rows = []
    for key, label in FORECASTERS:
        live = fwd['scores'].get(key) or {}
        bt = back.get(key) or {}
        rows.append({'key': key, 'label': label,
                     'live': _row(live.get('log_loss'), live.get('brier'), int(live.get('games') or 0)),
                     'backtest': _row(bt.get('log_loss'), bt.get('brier'), int(bt.get('games') or 0))})
    slope = ((fwd.get('calibration') or {}).get('model_b') or {}).get('slope')
    return {'season': fwd['season'], 'through': fwd.get('through'), 'rows': rows,
            'calibration': None if not slope else {k: round(slope[k], 2) for k in ('value', 'low', 'high')},
            'backtest_label': 'the 2024-25 and 2025-26 confirmation seasons', 'note': None}


def nfl(root: Path = ROOT) -> dict[str, Any] | None:
    """The NFL's: live from the graded weeks of the latest season, backtest from data/nfl/calibration.json."""
    cal = _read(root / 'data' / 'nfl' / 'calibration.json')
    weeks = sorted((int(m.group(1)), int(m.group(2)), p) for p in (root / 'results' / 'nfl').glob('*_graded.json')
                   if (m := re.fullmatch(r'(\d{4})_week(\d+)_graded', p.stem)))
    if cal is None or not weeks:
        return None
    season = weeks[-1][0]
    base = float(cal['models']['model_a']['decomposition']['base_rate'])
    scored: dict[str, list[tuple[float, int]]] = {k: [] for k, _ in FORECASTERS}
    # The lock writes a week's graded file before its games are played, so the record runs through the
    # latest week with a result, not the latest file.
    graded_weeks: set[int] = set()
    for s, w, path in weeks:
        if s != season:
            continue
        for g in json.loads(path.read_text(encoding='utf-8')):
            y = g.get('actual_home_win')
            if y not in (0, 1):
                continue
            if g.get('model_b_home_win_prob') is not None:
                scored['model_b'].append((float(g['model_b_home_win_prob']), int(y)))
            if g.get('market_prob_home') is not None:
                scored['market'].append((float(g['market_prob_home']), int(y)))
            scored['base_rate'].append((base, int(y)))
            graded_weeks.add(w)
    rows = []
    for key, label in FORECASTERS:
        pairs = scored[key]
        live = _row(sum(log_loss(p, y) for p, y in pairs) / len(pairs) if pairs else None,
                    sum((p - y) ** 2 for p, y in pairs) / len(pairs) if pairs else None, len(pairs))
        if key == 'base_rate':
            n = int(cal['models']['model_a']['metrics']['n'])
            bt = _row(-(base * math.log(base) + (1 - base) * math.log(1 - base)), base * (1 - base), n)
        else:
            m = cal['models'][key]['metrics']
            bt = _row(m['log_loss'], m['brier'], int(m['n']))
        rows.append({'key': key, 'label': label, 'live': live, 'backtest': bt})
    seasons = cal.get('backtest_seasons') or []
    if not graded_weeks:
        return None
    return {'season': season, 'through': f'week {max(graded_weeks)}', 'rows': rows,
            'calibration': None,
            'backtest_label': f'the {seasons[0]}-{seasons[-1]} seasons' if seasons else 'the backtest',
            'note': (f"The backtest is model v{cal.get('model_version')}; this season's picks are later "
                     'versions, which use the listed starting quarterback.')}


def track_record(root: Path = ROOT) -> dict[str, Any]:
    return {'nfl': nfl(root), 'nhl': day_sport('nhl', root), 'nba': day_sport('nba', root)}
