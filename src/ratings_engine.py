"""
Core rating engine: opponent-adjusted team ratings + per-QB ratings.
Both are leak-free (any "as of" cutoff only uses strictly earlier plays)
and recency-weighted. This is the same method validated in the project's
backtest -- see METHODOLOGY.md for the real, run numbers.
"""
import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from config import RIDGE_ALPHA, RECENCY_HALF_LIFE, QB_SHRINK_K, MIN_PLAYS_FOR_RATING


def prep_plays(raw_pbp):
    """Filter to regular-season pass/rush plays with valid EPA, and assign
    a sequential global-week index used for recency weighting."""
    reg = raw_pbp[raw_pbp['season_type'] == 'REG'].copy()
    plays = reg[(reg['pass'] == 1) | (reg['rush'] == 1)].copy()
    plays = plays[plays['epa'].notna()].reset_index(drop=True)

    week_keys = sorted(plays[['season', 'week']].drop_duplicates().itertuples(index=False, name=None))
    week_to_idx = {wk: i for i, wk in enumerate(week_keys)}
    plays['gwidx'] = list(zip(plays['season'], plays['week']))
    plays['gwidx'] = plays['gwidx'].map(week_to_idx)
    return plays, week_keys, week_to_idx


def build_team_ratings(plays, week_keys, upto_cutoff_i=None):
    """Two-way fixed-effects ridge regression of play EPA on offense/defense
    team dummies, recency-weighted. If upto_cutoff_i is None, computes a
    rating for every historical week (for backtesting); otherwise computes
    ONLY the single "as of right now" rating at that cutoff (for live use --
    much faster, since it's one fit instead of ~100).
    """
    teams = sorted(set(plays['posteam'].dropna().unique()) | set(plays['defteam'].dropna().unique()))
    team_idx = {t: i for i, t in enumerate(teams)}
    n_teams = len(teams)
    off_col = plays['posteam'].map(team_idx).values
    def_col = plays['defteam'].map(team_idx).values
    y = plays['epa'].values
    gwidx = plays['gwidx'].values

    def fit_at(cutoff_i):
        mask = gwidx < cutoff_i
        n = mask.sum()
        if n < MIN_PLAYS_FOR_RATING:
            return None
        idx = np.where(mask)[0]
        distance = cutoff_i - gwidx[idx]
        w = 0.5 ** (distance / RECENCY_HALF_LIFE)
        X = np.zeros((n, 2 * n_teams))
        rows = np.arange(n)
        X[rows, off_col[idx]] = 1.0
        X[rows, n_teams + def_col[idx]] = 1.0
        model = Ridge(alpha=RIDGE_ALPHA, fit_intercept=True)
        model.fit(X, y[idx], sample_weight=w)
        c = model.coef_
        return {teams[t]: (c[t], c[n_teams + t]) for t in range(n_teams)}

    if upto_cutoff_i is not None:
        return fit_at(upto_cutoff_i)

    ratings_by_week = {}
    for cutoff_i, wk in enumerate(week_keys):
        r = fit_at(cutoff_i)
        if r is not None:
            ratings_by_week[wk] = r
    return ratings_by_week


def build_qb_ratings(raw_pbp):
    """Per-player trailing EPA/dropback, leak-free, recency-weighted,
    shrunk toward league average for small samples. Returns
    (qb_plays_df, week_to_idx, league_avg_qb_epa) plus a helper function."""
    usecols = ['season', 'week', 'season_type', 'posteam', 'qb_dropback',
               'qb_epa', 'passer_player_id', 'passer_player_name']
    df = raw_pbp[[c for c in usecols if c in raw_pbp.columns]].copy()
    df = df[df['season_type'] == 'REG']
    df = df[df['qb_dropback'] == 1]
    df = df[df['qb_epa'].notna() & df['passer_player_id'].notna()]

    week_keys = sorted(df[['season', 'week']].drop_duplicates().itertuples(index=False, name=None))
    week_to_idx = {wk: i for i, wk in enumerate(week_keys)}
    df['gwidx'] = list(zip(df['season'], df['week']))
    df['gwidx'] = df['gwidx'].map(week_to_idx)
    league_avg = df['qb_epa'].mean()

    def trailing_rating(player_id, cutoff_gwidx):
        prior = df[(df['passer_player_id'] == player_id) & (df['gwidx'] < cutoff_gwidx)]
        if len(prior) == 0:
            return league_avg
        distance = cutoff_gwidx - prior['gwidx'].values
        w = 0.5 ** (distance / RECENCY_HALF_LIFE)
        weighted_avg = np.average(prior['qb_epa'].values, weights=w)
        n_eff = w.sum()
        return (n_eff * weighted_avg + QB_SHRINK_K * league_avg) / (n_eff + QB_SHRINK_K)

    def identify_starters(season, week=None):
        """Most-dropbacks passer per team for a given season (optionally week)."""
        sub = df[df['season'] == season] if week is None else df[(df['season'] == season) & (df['week'] == week)]
        counts = sub.groupby(['season', 'week', 'posteam', 'passer_player_id', 'passer_player_name']).size().reset_index(name='n')
        return counts.sort_values('n', ascending=False).drop_duplicates(subset=['season', 'week', 'posteam'])

    return {
        'plays': df, 'week_keys': week_keys, 'week_to_idx': week_to_idx,
        'league_avg': league_avg, 'trailing_rating': trailing_rating,
        'identify_starters': identify_starters,
    }
