"""
Monte Carlo season simulation -- projects the rest of the season forward
from current team ratings to produce playoff-probability estimates.

Design choices, stated explicitly rather than buried:
  - Uses a 2-feature model (off_matchup, def_matchup only), NOT the full
    4-feature Model A. Future games have no knowable starting QB, so
    qb_matchup/qb_change_diff can't be computed for them -- this is a
    real, deliberate simplification, not an oversight.
  - Team ratings are held STATIC for the whole remaining season. Real
    teams improve or decline (injuries, in-season trades, player
    development) -- this simulation can't capture that. Accuracy will
    degrade the further out from "now" a projection reaches.
  - Tiebreakers implement the three most common/impactful real NFL rules
    (head-to-head via division record proxy, division record, conference
    record) and fall back to random for anything beyond that. This is
    NOT the NFL's full multi-step tiebreaker procedure -- edge cases will
    occasionally resolve differently than they would in reality.
  - Already-played games use their REAL result, not a simulated one --
    only genuinely remaining games are randomized each iteration.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

DIVISIONS = {
    'AFC East': ['BUF', 'MIA', 'NE', 'NYJ'], 'AFC North': ['BAL', 'CIN', 'CLE', 'PIT'],
    'AFC South': ['HOU', 'IND', 'JAX', 'TEN'], 'AFC West': ['DEN', 'KC', 'LV', 'LAC'],
    'NFC East': ['DAL', 'NYG', 'PHI', 'WAS'], 'NFC North': ['CHI', 'DET', 'GB', 'MIN'],
    'NFC South': ['ATL', 'CAR', 'NO', 'TB'], 'NFC West': ['ARI', 'LA', 'SF', 'SEA'],
}
TEAM_DIV = {t: d for d, teams in DIVISIONS.items() for t in teams}
TEAM_CONF = {t: d.split(' ')[0] for t, d in TEAM_DIV.items()}
CONF_DIVS = {'AFC': [d for d in DIVISIONS if d.startswith('AFC')],
             'NFC': [d for d in DIVISIONS if d.startswith('NFC')]}


def fit_simple_win_model(hist):
    """Fits the 2-feature (off/def only) model used for future, QB-unknown
    games, from the same real historical data the rest of the pipeline
    already computed -- not a separately-hardcoded set of coefficients."""
    d2 = hist.dropna(subset=['off_matchup', 'def_matchup', 'home_win'])
    model = LogisticRegression(max_iter=1000)
    model.fit(d2[['off_matchup', 'def_matchup']].values, d2['home_win'].values)
    return model


def simulate_season(current_team_ratings, season_schedule, simple_model, n_sim=10000, seed=42):
    """
    current_team_ratings: dict {team: (off, def)} -- the CURRENT ratings.
    season_schedule: dataframe with season, week, home_team, away_team,
        home_score, away_score for the season being simulated. Games with
        a real (non-null) score are treated as already decided; all
        others are simulated.
    simple_model: fitted 2-feature LogisticRegression from fit_simple_win_model.
    Returns a dataframe: team, division, playoff_pct, division_win_pct.
    """
    coef_off, coef_def = simple_model.coef_[0]
    intercept = simple_model.intercept_[0]

    def win_prob(home, away):
        if home not in current_team_ratings or away not in current_team_ratings:
            return 0.5
        off_matchup = current_team_ratings[home][0] - current_team_ratings[away][1]
        def_matchup = current_team_ratings[away][0] - current_team_ratings[home][1]
        z = intercept + coef_off * off_matchup + coef_def * def_matchup
        return 1 / (1 + np.exp(-z))

    teams = sorted(TEAM_DIV.keys())
    team_idx = {t: i for i, t in enumerate(teams)}
    n_teams = len(teams)

    played = season_schedule.dropna(subset=['home_score', 'away_score'])
    remaining = season_schedule[season_schedule['home_score'].isna()]

    played_games = played[['home_team', 'away_team']].values
    played_home_win = (played['home_score'] > played['away_score']).values.astype(bool)

    remaining_games = remaining[['home_team', 'away_team']].values
    remaining_probs = np.array([win_prob(h, a) for h, a in remaining_games]) if len(remaining_games) else np.array([])

    np.random.seed(seed)
    n_remaining = len(remaining_games)
    rand = np.random.random((n_sim, n_remaining)) if n_remaining else np.zeros((n_sim, 0))
    sim_home_wins = rand < remaining_probs[np.newaxis, :] if n_remaining else np.zeros((n_sim, 0), dtype=bool)

    playoff_count = np.zeros(n_teams)
    division_win_count = np.zeros(n_teams)

    for sim in range(n_sim):
        wins = np.zeros(n_teams, dtype=int)
        div_record = {t: [0, 0] for t in teams}
        conf_record = {t: [0, 0] for t in teams}

        def record_game(h, a, home_won):
            if home_won:
                wins[team_idx[h]] += 1
                if TEAM_DIV.get(h) == TEAM_DIV.get(a): div_record[h][0] += 1; div_record[a][1] += 1
                if TEAM_CONF.get(h) == TEAM_CONF.get(a): conf_record[h][0] += 1; conf_record[a][1] += 1
            else:
                wins[team_idx[a]] += 1
                if TEAM_DIV.get(h) == TEAM_DIV.get(a): div_record[a][0] += 1; div_record[h][1] += 1
                if TEAM_CONF.get(h) == TEAM_CONF.get(a): conf_record[a][0] += 1; conf_record[h][1] += 1

        for g in range(len(played_games)):
            h, a = played_games[g]
            record_game(h, a, played_home_win[g])
        for g in range(n_remaining):
            h, a = remaining_games[g]
            record_game(h, a, sim_home_wins[sim, g])

        def tiebreak_key(t):
            dr = div_record[t]; cr = conf_record[t]
            dr_pct = dr[0] / (dr[0] + dr[1]) if (dr[0] + dr[1]) > 0 else 0
            cr_pct = cr[0] / (cr[0] + cr[1]) if (cr[0] + cr[1]) > 0 else 0
            return (wins[team_idx[t]], dr_pct, cr_pct, np.random.random())

        for conf in ['AFC', 'NFC']:
            div_winners = []
            for div in CONF_DIVS[conf]:
                best = max(DIVISIONS[div], key=tiebreak_key)
                div_winners.append(best)
                division_win_count[team_idx[best]] += 1
            conf_teams = [t for t in teams if TEAM_CONF[t] == conf]
            wildcard_pool = [t for t in conf_teams if t not in div_winners]
            wildcards = sorted(wildcard_pool, key=tiebreak_key, reverse=True)[:3]
            for t in div_winners + wildcards:
                playoff_count[team_idx[t]] += 1

    results = pd.DataFrame({
        'team': teams,
        'division': [TEAM_DIV[t] for t in teams],
        'playoff_pct': (playoff_count / n_sim * 100).round(1),
        'division_win_pct': (division_win_count / n_sim * 100).round(1),
    })
    return results.sort_values('playoff_pct', ascending=False).reset_index(drop=True)
