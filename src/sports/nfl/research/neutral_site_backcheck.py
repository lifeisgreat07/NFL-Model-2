"""Stage 38's neutral-site rule N1, back-checked (Mark, 2026-10-09: no home
edge at a neutral site, adopted as a declared rule). Not a test: a
description of what the rule would have done to past neutral games.

Walk-forward exactly as published (weekly refit on every earlier game from
2020, MODEL_SPECS), seasons 2021-2025. For every game the schedule calls
neutral (`weekly_update.site_is_neutral`, on nflverse's `location`), each
model's probability is recomputed with its intercept (the home edge) taken
out of the logit, which is what N1 does live. Writes
experiments/nfl/stage38/results/n1_backcheck.json, which the rule's
registration (experiments/nfl/stage38/n1_registry.json) quotes.

`hist` keeps no team names, so a game is matched to its schedule row by
(season, week, home margin, spread line); a key two games share is left out
rather than guessed.

Run from the repo root: python -m src.sports.nfl.research.neutral_site_backcheck
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.core.model_specs import MODEL_SPECS
from src.sports.nfl import data_loader
from src.sports.nfl.research.calibration import build_hist
from src.sports.nfl.weekly_update import site_is_neutral

SEASONS = [2021, 2022, 2023, 2024, 2025]
OUT = Path(__file__).resolve().parents[4] / 'experiments' / 'nfl' / 'stage38' / 'results' / 'n1_backcheck.json'
SEED = 20261009


def without_home_edge(p: np.ndarray, intercept: float) -> np.ndarray:
    """N1: the probability with the model's intercept taken out of its logit."""
    logit = np.log(p / (1 - p))
    out: np.ndarray = 1 / (1 + np.exp(-(logit - intercept)))
    return out


def log_loss(p: float, y: int) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return -math.log(p if y else 1 - p)


def neutral_flags(seasons: range) -> tuple[pd.DataFrame, set]:
    rows, seen = {}, {}
    for s in seasons:
        sch = data_loader.load_schedule(s)
        for _, g in sch.iterrows():
            if pd.isna(g.get('result')) or pd.isna(g.get('spread_line')):
                continue
            k = (int(g['season']), int(g['week']), float(g['result']), float(g['spread_line']))
            seen[k] = seen.get(k, 0) + 1
            rows[k] = (site_is_neutral(g), g['home_team'], g['away_team'])
    return rows, {k for k, n in seen.items() if n > 1}


def main() -> int:
    hist = build_hist().sort_values(['season', 'week'])
    flags, dupes = neutral_flags(range(2020, 2026))
    keys = [None if pd.isna(r.spread_line) else (int(r.season), int(r.week), float(r.home_margin), float(r.spread_line))
            for r in hist.itertuples()]
    hist['neutral'] = [None if k is None or k in dupes else (flags.get(k) or (None,))[0] for k in keys]
    hist['home'] = [(flags.get(k) or (None, '?'))[1] if k else '?' for k in keys]
    hist['away'] = [(flags.get(k) or (None, '?', '?'))[2] if k else '?' for k in keys]
    rows: list[dict[str, Any]] = []
    for name in ('model_a', 'model_b'):
        spec = MODEL_SPECS[name]
        feats = list(spec.features)
        d2 = hist.dropna(subset=feats + ['home_win'])
        for season in SEASONS:
            for w in sorted(d2[d2['season'] == season]['week'].unique()):
                test = d2[(d2['season'] == season) & (d2['week'] == w)]
                neutral = test[test['neutral'] == True]
                if neutral.empty:
                    continue
                train = d2[(d2['season'] < season) | ((d2['season'] == season) & (d2['week'] < w))]
                m = spec.fit(train)
                est = m[-1] if hasattr(m, 'steps') else m
                p = m.predict_proba(neutral[feats].values)[:, 1]
                p0 = without_home_edge(p, float(est.intercept_[0]))
                for (_, r), a, b in zip(neutral.iterrows(), p, p0):
                    rows.append({'model': name, 'season': int(season), 'week': int(w), 'home': r['home'],
                                 'away': r['away'], 'home_win': int(r['home_win']), 'p_incumbent': float(a),
                                 'p_neutral_rule': float(b), 'intercept': float(est.intercept_[0])})
    out: dict[str, Any] = {'seasons': SEASONS, 'ambiguous_keys_left_out': len(dupes), 'games': rows, 'summary': {}}
    rng = np.random.default_rng(SEED)
    for name in ('model_a', 'model_b'):
        r = [x for x in rows if x['model'] == name]
        if not r:
            continue
        d = np.array([log_loss(x['p_neutral_rule'], x['home_win']) - log_loss(x['p_incumbent'], x['home_win'])
                      for x in r])
        boots = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(5000)]
        out['summary'][name] = {
            'n': len(r), 'home_won': sum(x['home_win'] for x in r),
            'log_loss_incumbent': round(float(np.mean([log_loss(x['p_incumbent'], x['home_win']) for x in r])), 4),
            'log_loss_neutral_rule': round(float(np.mean([log_loss(x['p_neutral_rule'], x['home_win']) for x in r])), 4),
            'diff_mean': round(float(d.mean()), 4),
            'diff_ci95': [round(float(np.percentile(boots, 2.5)), 4), round(float(np.percentile(boots, 97.5)), 4)],
            'mean_intercept': round(float(np.mean([x['intercept'] for x in r])), 4),
            'mean_shift_pp': round(float(np.mean([x['p_incumbent'] - x['p_neutral_rule'] for x in r])) * 100, 2),
        }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(out['summary'], indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
