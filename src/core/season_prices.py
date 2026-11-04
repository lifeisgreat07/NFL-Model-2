"""This season's market prices for the live models' training rows (Stage 85
item 5, the 2026-11-02 review).

Model B is fitted on every final game that has a market price. Earlier
seasons' games carry the backtest's price; this season's games carried none
in the daily runs, so live Model B was fitted without a single game of the
season it is picking. Each run records the prices it reads in
data/<sport>/lines/<season>.json, and this turns that file into one home-win
probability per game: the last read before the game started, the nearest
the record holds to the backtest's pre-game line. A read at or after the
start is never used. Standard library only.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


def pre_game(lines: Iterable[Mapping[str, Any]]) -> dict[str, float]:
    """game_id -> home probability from the game's last read before its start.
    Times are the files' '%Y-%m-%dT%H:%M:%SZ' strings, which order as times."""
    best: dict[str, tuple[str, float]] = {}
    for r in lines:
        prob, read, start = r.get('home_prob'), r.get('read_utc'), r.get('start_utc')
        if prob is None or not read or not start or read >= start:
            continue
        gid = str(r['game_id'])
        if gid not in best or read > best[gid][0]:
            best[gid] = (str(read), float(prob))
    return {gid: p for gid, (_, p) in best.items()}


def read(path: Path) -> dict[str, float]:
    """pre_game over a season's lines file; no file, no prices."""
    return pre_game(json.loads(path.read_text(encoding='utf-8'))) if path.exists() else {}
