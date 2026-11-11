"""The NBA's drift check: is live Model A doing worse than its backtest said?

The NHL's rule (`src/sports/nhl/drift.py`, itself the NFL's Stage 33 R4),
registered for the NBA in `experiments/nba/stage65/registry.json`: once
`min_games` picks are graded, flag when the lower end of a one-sided 95%
bootstrap interval of mean per-game log loss is above the baseline in
`data/nba/drift_baseline.json`, Model A's log loss on Stage 61's
confirmation seasons. Each sport keeps its own copy, so neither reads the
other's files.

A flag is a reason to look, not proof that something broke: the backtest
knew who played, and a live pick knows only the injury report.

Amended 2026-11-04 (Stage 85 item 1, `drift.amended_2026_11_04` in the
registry): the rule above was tested at every daily run once 100 picks were
graded. It now looks only at the checkpoints in the baseline file's rule,
each at the per-look level that shares the 5% false-flag rate among them.

Amended 2026-11-05 (Stage 85 item 2, `drift.amended_2026_11_05`): a pick
made without the injury report is held to Model A's backtest without
availability, not with it (`pick_baselines`).
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from src.core.day_drift import look_value as look_value
from src.core.day_drift import lower_bound as lower_bound
from src.core.day_drift import next_look as next_look
from src.core.day_drift import per_game_log_loss as per_game_log_loss
from src.core.sport import sport_paths

BASELINE = sport_paths('nba').data / 'drift_baseline.json'
EPS = 1e-15


def baseline(path: Path = BASELINE) -> dict[str, Any]:
    spec: dict[str, Any] = json.loads(path.read_text(encoding='utf-8'))
    for key in ('baseline', 'baseline_no_availability', 'rule'):
        spec[key]  # a KeyError here is the "incomplete" case
    return spec


def pick_baselines(reads: Iterable[bool], spec: dict[str, Any]) -> list[float]:
    """Each graded pick's own baseline (Stage 85 item 2, `drift.amended_2026_11_05`).

    A pick made with the injury report is held to Model A's backtest with
    availability; a pick made without it ran the model without the
    availability term and is held to that model's backtest
    (`baseline_no_availability`, the same confirmation seasons). Holding it
    to the first would count the missing report as drift."""
    with_it, without = spec['baseline']['value'], spec['baseline_no_availability']['value']
    return [float(with_it if read else without) for read in reads]


def per_game(rows: Iterable[tuple[float | None, int | None, bool]],
             spec: dict[str, Any]) -> tuple[list[float], list[float]]:
    """(per-game log loss, each game's own baseline) from (Model A's home
    probability, home won, availability read) rows, in their order. A game
    without both a probability and a result decides nothing, as in
    `per_game_log_loss`, and its baseline is dropped with it."""
    kept = [(p, y, read) for p, y, read in rows if p is not None and y in (0, 1)]
    return per_game_log_loss((p, y) for p, y, _ in kept), pick_baselines((read for *_, read in kept), spec)


def look_baseline(spec: dict[str, Any], baselines: list[float] | None, n: int) -> float:
    """The baseline a look at n picks is held to: the mean of those n picks'
    own baselines, or the registered baseline when none are given. Since
    Stage 95 item 31 each is its model's figure over a season's first n games
    (`look_value`); a pick's whole-season figure says which model it ran."""
    if baselines is None:
        return look_value(spec, 'baseline', n)
    by = {float(spec['baseline']['value']): look_value(spec, 'baseline', n),
          float(spec['baseline_no_availability']['value']): look_value(spec, 'baseline_no_availability', n)}
    return float(sum(by[b] for b in baselines[:n]) / n)


def looks(losses: list[float], spec: dict[str, Any], baselines: list[float] | None = None) -> list[dict[str, Any]]:
    """Every registered look the graded picks have reached (Stage 85 item 1).

    The check looks only at the registered checkpoints, each on the first n
    graded picks in the order their games started, at the per-look level:
    the family's one-sided 95% shared over the looks (Bonferroni). A daily
    look at 95% has a 5% false-flag chance each day, and every extra look
    can only add to the season's. Each look is held to its own picks'
    baselines (Stage 85 item 2, `pick_baselines`)."""
    rule = spec['rule']
    out = []
    for n in rule['checkpoints']:
        if len(losses) < n:
            break
        bound = lower_bound(losses[:n], rule, rule['per_look_level'])
        base = look_baseline(spec, baselines, n)
        out.append({'games': n, 'lower_bound': bound, 'baseline': base, 'flagged': bool(bound > base)})
    return out


def flags(losses: list[float], spec: dict[str, Any], baselines: list[float] | None = None) -> bool:
    """True when any look so far has flagged: a flag stands for the season."""
    return any(look['flagged'] for look in looks(losses, spec, baselines))
