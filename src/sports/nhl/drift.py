"""The NHL's drift check: is live Model A doing worse than its backtest said?

The NFL's rule (Stage 33 R4, `src/sports/nfl/check_drift.py`), registered for
the NHL in `experiments/nhl/stage58/registry.json`: once `min_games` picks
are graded, flag when the lower end of a one-sided 95% bootstrap interval of
mean per-game log loss is above the baseline in `data/nhl/drift_baseline.json`,
Model A's log loss on Stage 56's confirmation seasons.

A flag is a reason to look, not proof that something broke: the backtest
knew each game's actual starter, and a live pick knows the projected one.

Amended 2026-11-04 (Stage 85 item 1, `drift.amended_2026_11_04` in the
registry): the rule above was tested at every daily run once 100 picks were
graded. It now looks only at the checkpoints in the baseline file's rule,
each at the per-look level that shares the 5% false-flag rate among them.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.core.day_drift import leak_direction as leak_direction
from src.core.day_drift import leak_lines as leak_lines
from src.core.day_drift import leaked_picks as leaked_picks
from src.core.day_drift import look_value as look_value
from src.core.day_drift import lower_bound as lower_bound
from src.core.day_drift import next_look as next_look
from src.core.day_drift import per_game_log_loss as per_game_log_loss
from src.core.sport import sport_paths

BASELINE = sport_paths('nhl').data / 'drift_baseline.json'
EPS = 1e-15


def baseline(path: Path = BASELINE) -> dict[str, Any]:
    spec: dict[str, Any] = json.loads(path.read_text(encoding='utf-8'))
    for key in ('baseline', 'rule'):
        spec[key]  # a KeyError here is the "incomplete" case
    return spec


def looks(losses: list[float], spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Every registered look the graded picks have reached (Stage 85 item 1).

    The check looks only at the registered checkpoints, each on the first n
    graded picks in the order their games started, at the per-look level:
    the family's one-sided 95% shared over the looks (Bonferroni). A daily
    look at 95% has a 5% false-flag chance each day, and every extra look
    can only add to the season's."""
    rule = spec['rule']
    out = []
    for n in rule['checkpoints']:
        if len(losses) < n:
            break
        bound = lower_bound(losses[:n], rule, rule['per_look_level'])
        # Stage 95 item 31: held to the backtest over a season's first n games.
        base = look_value(spec, 'baseline', n)
        out.append({'games': n, 'lower_bound': bound, 'baseline': base, 'flagged': bool(bound > base)})
    return out


def flags(losses: list[float], spec: dict[str, Any]) -> bool:
    """True when any look so far has flagged: a flag stands for the season."""
    return any(look['flagged'] for look in looks(losses, spec))


def spread_range() -> float | None:
    """Stage 95 item 33: how far Model A's backtest seasons differ from each other
    (experiments/nhl/stage56/results/model_a_by_season.json, `spread.range`)."""
    path = sport_paths('nhl').experiments / 'stage56' / 'results' / 'model_a_by_season.json'
    return float(json.loads(path.read_text(encoding='utf-8'))['spread']['range']) if path.exists() else None
