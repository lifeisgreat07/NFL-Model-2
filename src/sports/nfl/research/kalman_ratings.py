"""
State-space team ratings (Stage 5, hypothesis H7).

The incumbent ratings are a ridge fit re-run every week with exponential
recency weights: a good estimator with two hand-set knobs (RIDGE_ALPHA and a
16-week half-life) and no notion of how sure it is. This replaces both knobs
with a model of how team strength actually moves:

  * every team has an offence and a defence strength, in the same EPA-per-play
    units and sign convention as the ridge ratings (offence: EPA gained,
    defence: EPA allowed -- higher is worse);
  * within a season each strength takes a random-walk step every week
    (variance q);
  * between seasons it is pulled toward league average and loosened:
    theta <- rho * theta, variance rho^2 * P + s. That transition IS the
    preseason prior: how much of last season carries over is a fitted number
    rather than whatever a 16-week half-life happens to imply in September;
  * each team-game gives one observation per side: the offence's mean EPA per
    play against that defence, with noise variance sigma^2 / plays.

The filter runs week by week, and the ratings for week k are the state BEFORE
week k's games are absorbed -- the same "strictly earlier plays" rule as the
production ratings, so nothing leaks.

Hyperparameters are fitted by maximising the filter's own marginal likelihood
of the EPA observations in the fit seasons (2020-2021 as registered). That
uses EPA, never a game outcome, and never a validation or confirmation
season, so fitting it cannot tune toward the test.
"""
import numpy as np
from scipy.optimize import minimize

MU_Q = 1e-5  # weekly drift of the league-mean state; registered, not fitted


def team_game_observations(plays):
    """(gwidx, season, off_team, def_team, mean_epa, n_plays) per team-game."""
    g = (plays.groupby(['gwidx', 'season', 'game_id', 'posteam', 'defteam'])['epa']
              .agg(['mean', 'count']).reset_index())
    return g


class KalmanRatings:
    def __init__(self, teams, sigma2):
        self.teams = list(teams)
        self.ti = {t: i for i, t in enumerate(self.teams)}
        self.nt = len(self.teams)
        self.dim = 2 * self.nt + 1  # offences, defences, league mean
        self.sigma2 = sigma2

    def run(self, obs, week_keys, params, stop_after_season=None, record=True):
        """Filter over week_keys. Returns (loglik, {week_key: ratings}) ."""
        q, s, rho, p0 = params
        nt, dim = self.nt, self.dim
        x = np.zeros(dim)
        P = np.eye(dim) * p0
        P[-1, -1] = 0.01
        by_week = {k: v for k, v in obs.groupby('gwidx')}
        loglik = 0.0
        out = {}
        prev_season = None
        teams_slice = slice(0, 2 * nt)
        for gi, (season, week) in enumerate(week_keys):
            if stop_after_season is not None and season > stop_after_season:
                break
            if prev_season is not None:
                if season != prev_season:
                    x[teams_slice] *= rho
                    P[teams_slice, :] *= rho
                    P[:, teams_slice] *= rho
                    P[teams_slice, teams_slice] += np.eye(2 * nt) * s
                else:
                    P[teams_slice, teams_slice] += np.eye(2 * nt) * q
                P[-1, -1] += MU_Q
            prev_season = season
            if record:
                out[(season, week)] = {t: (x[i], x[nt + i]) for t, i in self.ti.items()}
            wk = by_week.get(gi)
            if wk is None or len(wk) == 0:
                continue
            m = len(wk)
            H = np.zeros((m, dim))
            r = np.arange(m)
            H[r, wk['posteam'].map(self.ti).values] = 1.0
            H[r, nt + wk['defteam'].map(self.ti).values] = 1.0
            H[:, -1] = 1.0
            y = wk['mean'].values
            R = np.diag(self.sigma2 / wk['count'].values)
            resid = y - H @ x
            S = H @ P @ H.T + R
            L = np.linalg.cholesky(S)
            alpha = np.linalg.solve(L, resid)
            loglik += -0.5 * (alpha @ alpha) - np.log(np.diag(L)).sum() - 0.5 * m * np.log(2 * np.pi)
            K = np.linalg.solve(S, H @ P).T
            x = x + K @ resid
            P = P - K @ H @ P
            P = 0.5 * (P + P.T)
        return loglik, out


def fit_and_run(plays, week_keys, fit_through_season):
    """Fit (q, s, rho, p0) on seasons <= fit_through_season, then filter everything."""
    teams = sorted(set(plays['posteam'].dropna()) | set(plays['defteam'].dropna()))
    first_season = week_keys[0][0]
    sigma2 = float(plays.loc[plays['season'] == first_season, 'epa'].var())
    obs = team_game_observations(plays)
    kr = KalmanRatings(teams, sigma2)

    def unpack(z):
        return (np.exp(z[0]), np.exp(z[1]), 1 / (1 + np.exp(-z[2])), np.exp(z[3]))

    def nll(z):
        ll, _ = kr.run(obs, week_keys, unpack(z), stop_after_season=fit_through_season, record=False)
        return -ll

    z0 = np.array([np.log(1e-4), np.log(1e-3), 0.0, np.log(0.01)])
    res = minimize(nll, z0, method='L-BFGS-B',
                   bounds=[(np.log(1e-7), np.log(1e-1)), (np.log(1e-6), np.log(1.0)),
                           (-6, 6), (np.log(1e-5), np.log(1.0))])
    params = unpack(res.x)
    _, ratings = kr.run(obs, week_keys, params)
    info = {'q': params[0], 's': params[1], 'rho': params[2], 'p0': params[3],
            'sigma2': sigma2, 'fit_through_season': fit_through_season,
            'converged': bool(res.success), 'neg_loglik': float(res.fun)}
    return ratings, info
