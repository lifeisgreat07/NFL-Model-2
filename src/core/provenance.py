"""What a day sport's pick was trained on, saved with the pick (Stage 68 item 27).

The NFL's picks carry `data_provenance` (src/sports/nfl/weekly_update.py);
the NHL's and NBA's said nothing about the data behind their models, so a
pick could not show which games it had learned from (the 2026-10-09
audit, E26). The models are refitted each run on every completed game
from the registered first season, so the record is the first season, the
games, how many of them had a price, and the last day among them.
"""
from __future__ import annotations

from typing import Any

import pandas as pd


def training(table: pd.DataFrame, first_season: int) -> dict[str, Any]:
    """`training_through` and `data_provenance` for a pick, from the table its models were fitted on."""
    days = pd.to_datetime(table['day'])
    priced = int(table['home_prob'].notna().sum()) if 'home_prob' in table else 0
    return {
        'training_through': str(days.max().date()) if len(days) else None,
        'data_provenance': {
            'training_from_season': int(first_season),
            'training_games': int(len(table)),
            'training_games_priced': priced,
        },
    }
