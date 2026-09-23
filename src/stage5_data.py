"""
The game table Stage 5 experiments are run on: one row per regular-season
game, the incumbent features, and every registered variant of them.

The incumbent columns are built by the PRODUCTION functions
(ratings_engine.build_team_ratings, build_qb_ratings' trailing_rating), and
stage5_run.py's parity check asserts that the oracle-starter spec below
reproduces weekly_update.build_historical_features exactly. A harness that
re-derived the incumbent its own way could beat a slightly different model
from the one that ships.

Three definitions of "this team's quarterback for this game", because the
difference between them is Stage 5's first finding:

  oracle  -- most dropbacks IN THIS GAME. What build_historical_features uses,
             so what every published backtest figure rests on. Not knowable
             before kickoff: a starter hurt in the first quarter is replaced,
             in the features, by the backup who finished the game.
  sched   -- the starting QB nflverse records for the game (home_qb_id /
             away_qb_id on the schedule). Agrees with the first dropback of
             the game on 98.3% of team-games 2020-2025 (probe run before
             registration; no outcome was looked at). This is the pregame-
             knowable version, and for upcoming games nflverse publishes it
             before kickoff.
  lagged  -- most dropbacks in the team's PREVIOUS game. What
             weekly_update.main() actually uses live, via
             identify_starters(season) and "the most recent known start".

qb_change follows the same split. The oracle flag is "this game's starter
differs from last game's" (build_qb_change_lookup). The live flag is "the
last two known starts differ", i.e. whether a change happened LAST week.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import MIN_PLAYS_FOR_RATING, RECENCY_HALF_LIFE, RIDGE_ALPHA, TRAIN_SEASONS  # noqa: E402
from data_loader import load_plays, load_schedule  # noqa: E402
from ratings_engine import build_qb_ratings, build_team_ratings, prep_plays  # noqa: E402

REST_CAP = 7          # registered with H8
WP_BAND = (0.10, 0.90)  # registered with H4
WP_OUTSIDE_WEIGHT = 0.25


def load_inputs(seasons=TRAIN_SEASONS):
    raw = load_plays(seasons)
    sched = pd.concat([load_schedule(s) for s in seasons], ignore_index=True)
    sched = sched[sched['game_type'] == 'REG'].dropna(subset=['home_score', 'away_score'])
    return raw, sched.reset_index(drop=True)


def fit_ratings(plays, week_keys, y, weights=None, mask=None):
    """build_team_ratings generalised to any per-play target, weight and filter.

    With y = plays['epa'], weights None and mask None this is the production
    fit exactly (same design matrix, same recency weights, same ridge); the
    parity test asserts it. Returns {(season, week): {team: (off, def)}}.
    """
    teams = sorted(set(plays['posteam'].dropna()) | set(plays['defteam'].dropna()))
    ti = {t: i for i, t in enumerate(teams)}
    nt = len(teams)
    off = plays['posteam'].map(ti).values
    dfn = plays['defteam'].map(ti).values
    y = np.asarray(y, dtype=float)
    g = plays['gwidx'].values
    base_w = np.ones(len(plays)) if weights is None else np.asarray(weights, dtype=float)
    keep = np.ones(len(plays), dtype=bool) if mask is None else np.asarray(mask, dtype=bool)
    out = {}
    for cutoff, wk in enumerate(week_keys):
        m = (g < cutoff) & keep
        n = int(m.sum())
        if n < MIN_PLAYS_FOR_RATING:
            continue
        idx = np.where(m)[0]
        w = 0.5 ** ((cutoff - g[idx]) / RECENCY_HALF_LIFE) * base_w[idx]
        X = np.zeros((n, 2 * nt))
        r = np.arange(n)
        X[r, off[idx]] = 1.0
        X[r, nt + dfn[idx]] = 1.0
        model = Ridge(alpha=RIDGE_ALPHA, fit_intercept=True)
        model.fit(X, y[idx], sample_weight=w)
        c = model.coef_
        out[wk] = {teams[t]: (c[t], c[nt + t]) for t in range(nt)}
    return out


def rating_variants(plays, week_keys):
    """Every registered team-rating variant. Keys become column prefixes."""
    epa = plays['epa'].values
    variants = {'base': build_team_ratings(plays, week_keys)}
    # H3: success rate, as an ADDITIONAL pair of features.
    variants['sr'] = fit_ratings(plays, week_keys, plays['success'].fillna(0).values)
    # H4: plays outside the win-probability band down-weighted.
    wp = plays['wp'].values
    outside = (wp < WP_BAND[0]) | (wp > WP_BAND[1])
    variants['gt'] = fit_ratings(plays, week_keys, epa,
                                 weights=np.where(outside, WP_OUTSIDE_WEIGHT, 1.0))
    # H5: pass and rush fitted separately.
    is_pass = (plays['pass'] == 1).values
    variants['pass'] = fit_ratings(plays, week_keys, epa, mask=is_pass)
    variants['rush'] = fit_ratings(plays, week_keys, epa, mask=~is_pass)
    # H6: early downs only.
    variants['ed'] = fit_ratings(plays, week_keys, epa, mask=plays['down'].isin([1, 2]).values)
    return variants


def team_games(sched):
    """One row per (team, game) in date order, with the team's previous games."""
    h = sched[['game_id', 'season', 'week', 'home_team', 'home_qb_id']].rename(
        columns={'home_team': 'team', 'home_qb_id': 'sched_qb'})
    a = sched[['game_id', 'season', 'week', 'away_team', 'away_qb_id']].rename(
        columns={'away_team': 'team', 'away_qb_id': 'sched_qb'})
    tg = pd.concat([h, a], ignore_index=True).sort_values(['team', 'season', 'week'])
    return tg.reset_index(drop=True)


def starter_table(qb, sched):
    """oracle / sched / lagged starter and change flag for every team-game.

    The oracle columns come from the PRODUCTION calls, not a re-derivation:
    identify_starters(season, week) for the starter and
    weekly_update.build_qb_change_lookup for the flag. Those two calls sort
    different frames, so when two passers tie on dropbacks they can pick
    different players for the same game -- a first version that picked
    ties its own way matched production on 1592 of 1599 games, and matching
    1592 is not matching. The lagged spec uses the season-level
    identify_starters(season), which is the call weekly_update.main() makes.
    """
    from weekly_update import build_qb_change_lookup
    seasons = sorted(sched['season'].unique())
    per_game = pd.concat([qb['identify_starters'](s, w) for s, w in
                          sched[['season', 'week']].drop_duplicates().itertuples(index=False)],
                         ignore_index=True)
    per_game = per_game.rename(columns={'posteam': 'team', 'passer_player_id': 'oracle_qb'})
    season_level = pd.concat([qb['identify_starters'](s) for s in seasons], ignore_index=True)
    season_level = season_level.rename(columns={'posteam': 'team', 'passer_player_id': 'season_leader'})
    change = build_qb_change_lookup(qb, seasons)

    tg = team_games(sched)
    tg = tg.merge(per_game[['season', 'week', 'team', 'oracle_qb']], on=['season', 'week', 'team'], how='left')
    tg = tg.merge(season_level[['season', 'week', 'team', 'season_leader']], on=['season', 'week', 'team'], how='left')
    grp = tg.groupby('team')
    prev_season = grp['season'].shift(1)
    prev2_season = grp['season'].shift(2)
    prev_leader = grp['season_leader'].shift(1)
    prev2_leader = grp['season_leader'].shift(2)
    prev_sched = grp['sched_qb'].shift(1)
    same = prev_season == tg['season']

    tg['oracle_changed'] = [change.get((s, w, t), 0) for s, w, t in zip(tg['season'], tg['week'], tg['team'])]
    tg['sched_changed'] = (same & prev_sched.notna() & (tg['sched_qb'] != prev_sched)).astype(int)
    tg['lagged_qb'] = prev_leader
    tg['lagged_changed'] = ((prev_season == prev2_season) & prev2_leader.notna()
                            & (prev_leader != prev2_leader)).astype(int)
    return tg


def build_games(raw=None, sched=None, variants=None, extra_ratings=None):
    """The Stage 5 game table. extra_ratings: {prefix: ratings_by_week} (e.g. Kalman)."""
    if raw is None or sched is None:
        raw, sched = load_inputs()
    plays, week_keys, _ = prep_plays(raw)
    if variants is None:
        variants = rating_variants(plays, week_keys)
    if extra_ratings:
        variants = {**variants, **extra_ratings}
    qb = build_qb_ratings(raw)
    qb_idx = qb['week_to_idx']
    cache = {}

    def qb_rating(pid, cutoff):
        if not isinstance(pid, str):
            return np.nan
        k = (pid, cutoff)
        if k not in cache:
            cache[k] = qb['trailing_rating'](pid, cutoff)
        return cache[k]

    st = starter_table(qb, sched).set_index(['game_id', 'team'])
    rows = []
    for g in sched.itertuples(index=False):
        key = (g.season, g.week)
        row = {
            'game_id': g.game_id, 'season': int(g.season), 'week': int(g.week),
            'home_team': g.home_team, 'away_team': g.away_team,
            'home_win': int(g.home_score > g.away_score),
            'spread_line': g.spread_line,
            'home_moneyline': g.home_moneyline, 'away_moneyline': g.away_moneyline,
            'rest_diff': float(np.clip(g.home_rest - g.away_rest, -REST_CAP, REST_CAP)),
        }
        for prefix, rbw in variants.items():
            rt = rbw.get(key)
            if rt is None or g.home_team not in rt or g.away_team not in rt:
                continue
            h_off, h_def = rt[g.home_team]
            a_off, a_def = rt[g.away_team]
            row[f'{prefix}_off_matchup'] = h_off - a_def
            row[f'{prefix}_def_matchup'] = a_off - h_def
        cutoff = qb_idx.get(key)
        hs, as_ = st.loc[(g.game_id, g.home_team)], st.loc[(g.game_id, g.away_team)]
        for spec in ('oracle', 'sched', 'lagged'):
            if cutoff is not None:
                row[f'{spec}_qb_matchup'] = qb_rating(hs[f'{spec}_qb'], cutoff) - qb_rating(as_[f'{spec}_qb'], cutoff)
            row[f'{spec}_qb_change_diff'] = int(hs[f'{spec}_changed']) - int(as_[f'{spec}_changed'])
        rows.append(row)
    games = pd.DataFrame(rows)
    games['ml_logit'] = moneyline_logit(games['home_moneyline'], games['away_moneyline'])
    return games


def implied(ml):
    ml = np.asarray(ml, dtype=float)
    neg = -ml / (np.abs(ml) + 100.0)
    pos = 100.0 / (np.abs(ml) + 100.0)
    return np.where(ml < 0, neg, pos)


def moneyline_logit(home_ml, away_ml):
    """De-vigged home win probability from the two moneylines, as a logit (H2)."""
    ph, pa = implied(home_ml), implied(away_ml)
    p = ph / (ph + pa)
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def feature_set(spec='sched', ratings='base', extra=(), market=None):
    """Model A (market None) or Model B columns for a QB spec and rating variant."""
    cols = [f'{ratings}_off_matchup', f'{ratings}_def_matchup',
            f'{spec}_qb_matchup', f'{spec}_qb_change_diff', *extra]
    if market:
        cols.append(market)
    return cols
