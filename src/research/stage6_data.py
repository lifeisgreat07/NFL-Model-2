"""
The inputs Stage 6's Next Gen Stats questions are answered on.

Everything here follows experiments/stage6/registry.json's "definitions"
block, and the names below are that block's names:

  trailing      a recency-weighted, volume-weighted mean of a player's
                earlier regular-season weeks, shrunk toward the league mean
                as of the same cutoff with a pseudo-count of QB_SHRINK_K.
                The same shape as ratings_engine.build_qb_ratings'
                trailing_rating, computed from weekly aggregates instead of
                plays. Within one week every play carries the same recency
                weight, so the two are equal; the test suite checks that on
                synthetic plays against the production function itself.
  qb_game       a passer's regular-season game with at least MIN_DROPBACKS
                dropbacks; the target is his mean qb_epa per dropback.
  trailing_epa  the production QB rating, called, not re-derived.
  trailing_cpoe play-by-play cpoe, per attempt where present.
  trailing_ngs  four Next Gen Stats passing columns, weekly REG rows only.

The week index is the one build_qb_ratings builds over play-by-play from
PBP_FROM: every regular-season week with a dropback. A week's trailing value
uses only weeks strictly before it, so nothing a game produces can reach its
own inputs.
"""

import numpy as np
import pandas as pd

from src.pipeline.config import QB_SHRINK_K, RECENCY_HALF_LIFE  # noqa: E402

PBP_FROM = 2016                 # registry: "weeks counted ... from 2016 on"
MIN_DROPBACKS = 15              # registry: qb_game
NGS_COLUMNS = ['completion_percentage_above_expectation', 'avg_time_to_throw',
               'aggressiveness', 'avg_intended_air_yards']
PBP_COLUMNS = ['season', 'week', 'season_type', 'posteam', 'defteam', 'epa', 'pass', 'rush',
               'qb_dropback', 'qb_epa', 'passer_player_id', 'passer_player_name',
               'pass_attempt', 'cpoe']


# ------------------------------------------------------------------ loading

def load_pbp(seasons, columns=PBP_COLUMNS):
    """Play-by-play for many seasons, only the columns a Stage 6 question reads.

    One season at a time, so ten seasons of all 370-odd columns are never
    held in memory at once. Uses data_loader's cache when NFL_PBP_CACHE is set.
    """
    import nflreadpy as nfl

    from src.pipeline.data_loader import pbp_cache_dir
    cache = pbp_cache_dir()
    frames = []
    for s in seasons:
        path = cache / f'pbp_{s}.parquet' if cache else None
        if path is not None and path.is_file():
            import polars as pl
            df = pl.read_parquet(path)
        else:
            df = nfl.load_pbp([s])
            if path is not None and s < nfl.get_current_season():
                cache.mkdir(parents=True, exist_ok=True)
                df.write_parquet(path)
        frames.append(df.select([c for c in columns if c in df.columns]).to_pandas())
    return pd.concat(frames, ignore_index=True)


def load_ngs(seasons, column_map=None):
    """Weekly regular-season Next Gen Stats passing rows.

    Drops the season-total rows (week 0) and anything that is not REG.
    column_map renames a column whose loaded name differs from the data
    dictionary's; the result file records it.
    """
    import nflreadpy as nfl
    df = nfl.load_nextgen_stats(seasons, stat_type='passing').to_pandas()
    if column_map:
        df = df.rename(columns=column_map)
    missing = [c for c in NGS_COLUMNS + ['player_gsis_id', 'attempts', 'season', 'week', 'season_type']
               if c not in df.columns]
    if missing:
        raise SystemExit(f"Next Gen Stats is missing {missing}; columns are {sorted(df.columns)}")
    return df[(df['season_type'] == 'REG') & (df['week'] > 0)].reset_index(drop=True)


# ------------------------------------------------------------------ trailing

class Trailing:
    """Trailing values of one weekly statistic, for any player and cutoff.

    weekly: DataFrame with player, gwidx, volume, value (the week's mean).
    Construction precomputes per-player arrays and the league's cumulative
    sums, so a lookup is one small vector operation.
    """

    def __init__(self, weekly, n_weeks, k=QB_SHRINK_K, half_life=RECENCY_HALF_LIFE):
        weekly = weekly[(weekly['volume'] > 0) & weekly['value'].notna()]
        self.k, self.half_life = k, half_life
        self.by_player = {p: (g['gwidx'].to_numpy(), g['volume'].to_numpy(float), g['value'].to_numpy(float))
                          for p, g in weekly.groupby('player')}
        s = np.zeros(n_weeks)
        c = np.zeros(n_weeks)
        agg = (weekly.assign(sv=weekly['volume'] * weekly['value'])
               .groupby('gwidx')[['sv', 'volume']].sum())
        s[agg.index.to_numpy()] = agg['sv'].to_numpy()
        c[agg.index.to_numpy()] = agg['volume'].to_numpy()
        self.cum_s, self.cum_c = np.cumsum(s), np.cumsum(c)
        self.n_weeks = n_weeks

    def league_as_of(self, cutoff):
        i = min(cutoff, self.n_weeks) - 1
        if i < 0 or self.cum_c[i] == 0:
            return 0.0
        return self.cum_s[i] / self.cum_c[i]

    def value(self, player, cutoff):
        league = self.league_as_of(cutoff)
        arr = self.by_player.get(player)
        if arr is None:
            return league
        g, vol, val = arr
        m = g < cutoff
        if not m.any():
            return league
        w = 0.5 ** ((cutoff - g[m]) / self.half_life) * vol[m]
        n_eff = w.sum()
        avg = (w * val[m]).sum() / n_eff
        return (n_eff * avg + self.k * league) / (n_eff + self.k)


def weekly_cpoe(pbp, week_to_idx):
    """Per passer-week: attempts with a cpoe value, and their mean cpoe."""
    d = pbp[(pbp['season_type'] == 'REG') & (pbp['pass_attempt'] == 1)
            & pbp['cpoe'].notna() & pbp['passer_player_id'].notna()]
    g = d.groupby(['season', 'week', 'passer_player_id'])['cpoe'].agg(['mean', 'count']).reset_index()
    g['gwidx'] = [week_to_idx.get((s, w)) for s, w in zip(g['season'], g['week'])]
    g = g.dropna(subset=['gwidx'])
    return pd.DataFrame({'player': g['passer_player_id'], 'gwidx': g['gwidx'].astype(int),
                         'volume': g['count'], 'value': g['mean']})


def weekly_ngs(ngs, column, week_to_idx):
    """Per passer-week for one Next Gen Stats column, weighted by attempts.

    A week the play-by-play index does not know is reported, not silently
    dropped, by the caller (see unmatched_ngs_weeks).
    """
    d = ngs[ngs['player_gsis_id'].notna()]
    gw = [week_to_idx.get((int(s), int(w))) for s, w in zip(d['season'], d['week'])]
    out = pd.DataFrame({'player': d['player_gsis_id'].to_numpy(), 'gwidx': gw,
                        'volume': d['attempts'].to_numpy(float), 'value': d[column].to_numpy(float)})
    return out.dropna(subset=['gwidx']).astype({'gwidx': int})


def unmatched_ngs_weeks(ngs, week_to_idx):
    keys = {(int(s), int(w)) for s, w in zip(ngs['season'], ngs['week'])}
    return sorted(k for k in keys if k not in week_to_idx)


# ------------------------------------------------------------------ qb games

def qb_games(qb_df, min_dropbacks=MIN_DROPBACKS):
    """Every qb_game: passer, season, week, gwidx, dropbacks, target."""
    g = (qb_df.groupby(['season', 'week', 'gwidx', 'passer_player_id'])['qb_epa']
         .agg(['mean', 'count']).reset_index())
    g = g[g['count'] >= min_dropbacks]
    return g.rename(columns={'passer_player_id': 'player', 'count': 'dropbacks', 'mean': 'target'})


def predictor_table(games, trailing_epa, tables):
    """Add trailing_epa and every Trailing in `tables` as of each game's cutoff."""
    out = games.copy()
    out['trailing_epa'] = [trailing_epa(p, c) for p, c in zip(out['player'], out['gwidx'])]
    for name, t in tables.items():
        out[name] = [t.value(p, c) for p, c in zip(out['player'], out['gwidx'])]
    return out


FEATURES = {
    'base': ['trailing_epa'],
    'control': ['trailing_epa', 'trailing_cpoe'],
    'candidate': ['trailing_epa', 'trailing_cpoe'] + [f'trailing_{c}' for c in NGS_COLUMNS],
}


# ------------------------------------------------------------------ N1 maths

def wls(X, y, w):
    """Weighted least squares with an intercept. Returns [intercept, *coefs]."""
    A = np.column_stack([np.ones(len(y)), X])
    sw = np.sqrt(w)
    beta, *_ = np.linalg.lstsq(A * sw[:, None], y * sw, rcond=None)
    return beta


def predict(beta, X):
    return beta[0] + np.asarray(X, float) @ np.asarray(beta[1:], float)


def weighted_mse(y, p, w):
    return float(np.sum(w * (y - p) ** 2) / np.sum(w))


def cluster_bootstrap_mse_diff(y, p_a, p_b, w, clusters, n_resamples, seed):
    """Resampled weighted MSE(a) - MSE(b), resampling whole clusters."""
    y, p_a, p_b, w = (np.asarray(v, float) for v in (y, p_a, p_b, w))
    codes, _ = pd.factorize(pd.Series(clusters))
    k = codes.max() + 1
    num = np.bincount(codes, w * ((y - p_a) ** 2 - (y - p_b) ** 2), minlength=k)
    den = np.bincount(codes, w, minlength=k)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, k, size=(n_resamples, k))
    return num[idx].sum(axis=1) / den[idx].sum(axis=1)


def screen_label(mse_diff, ci_95):
    """The registered N1 rule: PASS only if the difference and its upper bound are below zero."""
    return 'PASS' if mse_diff < 0 and ci_95[1] < 0 else 'FAIL'
