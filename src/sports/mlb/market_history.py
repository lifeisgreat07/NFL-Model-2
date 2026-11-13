"""MLB's market history for Model B (Stage 99 item 2), as experiments/mlb/stage98/registry.json's data.market says:
the two-way home-win probability, the margin taken out evenly, from ESPN's pre-game moneyline, the closing price
where ESPN gives one and the single listed price before that. A price from a provider marked live is never used.

ESPN's games are matched to the Stats API's finals by day: ESPN's scoreboard for each official date lists its
events with their clubs and scores. ESPN's club codes are mapped to Stats API ids from the season's own games (the
same date and the same two scores, the only such pair that day), never typed by hand. Where ESPN's home and away
are the Stats API's swapped (a relocated game), the prices are swapped back, so `home_prob` is always the Stats
API's home club's, and the row says so. A final ESPN does not list, or lists twice, is left unpriced and named.

One file a season, `data/mlb/history/market_<season>.csv` (`MARKET_FIELDS`).

Run by hand: python -m src.sports.mlb.market_history 2010 2026
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from collections import Counter
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.sport import GameStatus
from src.sports.mlb import schedule
from src.sports.mlb.history import HISTORY, fetch

SITE = 'https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={day}&limit=100'
ODDS = ('https://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/events/{e}/competitions/{e}/odds')
#: ESPN's own projections are not a market.
PROJECTIONS = {'espn bet - projections', 'numberfire', 'teamrankings'}
MARKET_FIELDS = ('game_id', 'season', 'espn_id', 'provider', 'home_price', 'away_price', 'closing', 'swapped',
                 'home_prob')

Json = Any


def implied(price: float) -> float:
    """An American price's implied probability, margin included."""
    return 100.0 / (price + 100.0) if price > 0 else -price / (-price + 100.0)


def _num(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def events(board: Json) -> list[dict[str, Any]]:
    """Each final event on one ESPN scoreboard: its id, and each side's code and score."""
    out = []
    for e in board.get('events') or []:
        comp = (e.get('competitions') or [{}])[0]
        if not ((comp.get('status') or {}).get('type') or {}).get('completed'):
            continue
        sides = {c.get('homeAway'): c for c in comp.get('competitors') or []}
        if set(sides) != {'home', 'away'}:
            continue
        out.append({'espn_id': str(e['id']),
                    'home': str((sides['home'].get('team') or {}).get('abbreviation')),
                    'away': str((sides['away'].get('team') or {}).get('abbreviation')),
                    'home_score': int(_num(sides['home'].get('score')) or 0),
                    'away_score': int(_num(sides['away'].get('score')) or 0)})
    return out


def code_map(espn: pd.DataFrame, finals: pd.DataFrame) -> dict[str, str]:
    """ESPN code -> Stats API id, learned from games with the same date and two scores, the only such pair that day."""
    votes: dict[str, Counter[str]] = {}
    keyed = {k: v for k, v in finals.groupby([finals['slate'], finals.apply(
        lambda g: frozenset((g['home_score'], g['away_score'])), axis=1)])}
    for e in espn.itertuples():
        m = keyed.get((e.slate, frozenset((e.home_score, e.away_score))))
        if m is None or len(m) != 1 or e.home_score == e.away_score:
            continue
        g = m.iloc[0]
        if (g['home_score'], g['away_score']) == (e.home_score, e.away_score):
            pairs = ((e.home, g['home']), (e.away, g['away']))
        else:
            pairs = ((e.home, g['away']), (e.away, g['home']))
        for code, club in pairs:
            votes.setdefault(code, Counter())[str(club)] += 1
    return {code: c.most_common(1)[0][0] for code, c in votes.items()}


def match(espn: pd.DataFrame, finals: pd.DataFrame, codes: dict[str, str]) -> tuple[dict[str, tuple[str, bool]],
                                                                                    list[str]]:
    """Each final's ESPN event and whether ESPN's home is the Stats API's away; and the finals left unmatched."""
    by_day: dict[tuple[str, frozenset[str]], list[Any]] = {}
    for e in espn.itertuples():
        h, a = codes.get(e.home), codes.get(e.away)
        if h and a:
            by_day.setdefault((e.slate, frozenset((h, a))), []).append(e)
    out: dict[str, tuple[str, bool]] = {}
    missing = []
    for g in finals.itertuples():
        cands = by_day.get((g.slate, frozenset((str(g.home), str(g.away)))), [])
        if len(cands) > 1:
            cands = [e for e in cands if {e.home_score, e.away_score} == {g.home_score, g.away_score}]
        if len(cands) != 1:
            missing.append(f'game {g.game_id} ({g.slate}): {len(cands)} ESPN events')
            continue
        e = cands[0]
        out[str(g.game_id)] = (e.espn_id, codes[e.home] != str(g.home))
    return out, missing


def market_row(odds: Json, game_id: str, season: int, espn_id: str, swapped: bool) -> dict[str, Any] | None:
    """The Stats API home club's two-way probability from ESPN's odds, or None when ESPN has no usable price."""
    for it in odds.get('items') or []:
        provider = str((it.get('provider') or {}).get('name') or '')
        if 'live' in provider.lower() or provider.lower() in PROJECTIONS:
            continue
        h, a = it.get('homeTeamOdds') or {}, it.get('awayTeamOdds') or {}
        close_h = _num(((h.get('close') or {}).get('moneyLine') or {}).get('american'))
        close_a = _num(((a.get('close') or {}).get('moneyLine') or {}).get('american'))
        closing = close_h is not None and close_a is not None
        hp, ap = (close_h, close_a) if closing else (_num(h.get('moneyLine')), _num(a.get('moneyLine')))
        if hp is None or ap is None or abs(hp) < 100 or abs(ap) < 100:
            continue
        if swapped:
            hp, ap = ap, hp
        ih, ia = implied(hp), implied(ap)
        return {'game_id': game_id, 'season': season, 'espn_id': espn_id, 'provider': provider,
                'home_price': hp, 'away_price': ap, 'closing': closing, 'swapped': swapped,
                'home_prob': round(ih / (ih + ia), 6)}
    return None


def season_market(season: int, sched: pd.DataFrame, get: Callable[[str], bytes] = fetch,
                  pause: float = 0.05) -> tuple[pd.DataFrame, list[str]]:
    finals = sched[sched['status'] == GameStatus.FINAL.value].copy()
    rows = []
    for day in sorted(finals['slate'].unique()):
        for e in events(json.loads(get(SITE.format(day=str(day).replace('-', ''))))):
            rows.append({'slate': day, **e})
        if pause:
            time.sleep(pause)
    espn = pd.DataFrame(rows, columns=['slate', 'espn_id', 'home', 'away', 'home_score', 'away_score'])
    matched, missing = match(espn, finals, code_map(espn, finals))
    out = []
    for gid, (eid, swapped) in matched.items():
        try:
            row = market_row(json.loads(get(ODDS.format(e=eid))), gid, season, eid, swapped)
        except OSError:
            row = None
        if row is not None:
            out.append(row)
        if pause:
            time.sleep(pause)
    return pd.DataFrame(out, columns=list(MARKET_FIELDS)), missing


def write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    df.to_csv(tmp, index=False, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
    tmp.replace(path)


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    ap.add_argument('first', type=int)
    ap.add_argument('last', type=int)
    args = ap.parse_args(list(argv) if argv is not None else None)
    for season in range(args.first, args.last + 1):
        path = HISTORY / f'market_{season}.csv'
        if path.exists():
            continue
        sched = schedule.load_schedule(season)
        m, missing = season_market(season, sched)
        write(m, path)
        finals = int((sched['status'] == GameStatus.FINAL.value).sum())
        print(f'{season}: {len(m)} of {finals} finals priced ({int(m["swapped"].sum())} with ESPN home and away '
              f'swapped); {len(missing)} not matched to an ESPN event', flush=True)
        for line in missing[:20]:
            print(f'  {line}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
