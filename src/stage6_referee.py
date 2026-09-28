"""
Stage 6's referee screen, R1, as experiments/stage6/registry.json words it.

  games         every regular-season game from 2016 to 2023 whose schedule row
                names a referee (and whose play-by-play was loaded).
  differential  per game, the penalty yards recorded against the away team
                minus those against the home team, from play-by-play rows with
                penalty == 1 (penalty_team, penalty_yards). Positive means the
                away team was flagged for more.
  windows       a referee's mean differential over 2016-2020 and over
                2021-2023; he counts only with at least MIN_EARLY and MIN_LATE
                games in them.
  persistence   the correlation of the two means across those referees, each
                weighted by the smaller of his two game counts, with a
                bootstrap interval that resamples referees.

PASS only if the interval's lower end is above zero. Nothing here reads a
season after 2023.
"""
import numpy as np
import pandas as pd

R1_SEASONS = list(range(2016, 2024))    # registry: "from 2016 to 2023"
EARLY = (2016, 2020)
LATE = (2021, 2023)
MIN_EARLY = 40                          # registry: "at least 40 such games in 2016-2020"
MIN_LATE = 24                           # registry: "at least 24 in 2021-2023"
PBP_COLUMNS = ['game_id', 'season', 'season_type', 'penalty', 'penalty_team', 'penalty_yards']


def named_referee_games(sched):
    """Regular-season schedule rows that name a referee, one per game."""
    s = sched[sched['game_type'] == 'REG']
    s = s[s['season'].between(R1_SEASONS[0], R1_SEASONS[-1])]
    ref = s['referee'].astype('string').str.split().str.join(' ')
    s = s.assign(referee=ref)
    s = s[s['referee'].notna() & (s['referee'] != '')]
    return s[['game_id', 'season', 'home_team', 'away_team', 'referee']].reset_index(drop=True)


def penalty_differential(pbp, games):
    """(games with a 'differential' column, counts worth recording).

    A game whose play-by-play was not loaded is dropped rather than scored
    zero; a loaded game with no penalty rows is a real zero.
    """
    loaded = set(pbp['game_id'])
    kept = games[games['game_id'].isin(loaded)].copy()
    p = pbp[pbp['penalty'] == 1].merge(kept[['game_id', 'home_team', 'away_team']], on='game_id')
    yards = p['penalty_yards'].astype(float)
    missing_yards = int(yards.isna().sum())
    yards = yards.fillna(0.0)
    against_away = p['penalty_team'] == p['away_team']
    against_home = p['penalty_team'] == p['home_team']
    d = yards.where(against_away, 0.0) - yards.where(against_home, 0.0)
    per_game = d.groupby(p['game_id']).sum()
    kept['differential'] = kept['game_id'].map(per_game).fillna(0.0)
    counts = {
        'games_naming_a_referee': int(len(games)),
        'games_without_play_by_play': int(len(games) - len(kept)),
        'penalty_rows': int(len(p)),
        'penalty_rows_missing_yards': missing_yards,
        'penalty_rows_on_neither_team': int((~against_away & ~against_home).sum()),
    }
    return kept.reset_index(drop=True), counts


def window_means(games):
    """One row per qualifying referee: mean and count in each window, and his weight."""
    def agg(lo, hi):
        g = games[games['season'].between(lo, hi)]
        return g.groupby('referee')['differential'].agg(['mean', 'count'])
    t = agg(*EARLY).join(agg(*LATE), how='inner', lsuffix='_early', rsuffix='_late')
    t = t[(t['count_early'] >= MIN_EARLY) & (t['count_late'] >= MIN_LATE)].copy()
    t['weight'] = np.minimum(t['count_early'], t['count_late'])
    return t.sort_index()


def weighted_corr(x, y, w):
    """Weighted Pearson correlation of one sample or, row-wise, of a 2-D stack.

    NaN where either side has no spread (the correlation is undefined).
    """
    x, y, w = (np.asarray(v, float) for v in (x, y, w))
    w = w / w.sum(axis=-1, keepdims=True)
    mx = (w * x).sum(axis=-1, keepdims=True)
    my = (w * y).sum(axis=-1, keepdims=True)
    cov = (w * (x - mx) * (y - my)).sum(axis=-1)
    vx = (w * (x - mx) ** 2).sum(axis=-1)
    vy = (w * (y - my) ** 2).sum(axis=-1)
    with np.errstate(invalid='ignore', divide='ignore'):
        r = cov / np.sqrt(vx * vy)
    return np.where((vx > 0) & (vy > 0), r, np.nan)


def bootstrap_corr(x, y, w, n_resamples, seed):
    """The weighted correlation over resamples of whole referees."""
    x, y, w = (np.asarray(v, float) for v in (x, y, w))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n_resamples, len(x)))
    return weighted_corr(x[idx], y[idx], w[idx])


def r1_label(ci_95):
    """The registered R1 rule: PASS only if the interval's lower end is above zero."""
    return 'PASS' if ci_95[0] > 0 else 'FAIL'
