"""
A small synthetic league: enough play-by-play and schedule for the weekly
pipeline to run end to end with no network, in about a second.

Stage 33 item 20, from the 2026-09-29 re-audit. Until this file,
weekly_update.main() could only be checked by reading its source: it needs
six seasons of nflverse play-by-play, so every test of what it DOES was
structural (tests/test_weekly_pipeline.py and others say so in their
docstrings). This builds the inputs instead.

Eight real team abbreviations (data_quality rejects any it does not know),
two seasons:

  PRIOR  (2025): weeks 1-21, the round robin three times over, all played.
                 Three, because backtest.py will not fit on fewer than 50
                 games with ratings, and a week has none until 200 plays
                 precede it.
  TARGET (2026): weeks 1-4 played; week 5 is the one under test, its
                 kickoffs set by the caller relative to `now`; weeks 6-7
                 are in the future.

Each team has a fixed offence and defence strength. Every play's EPA is that
matchup plus seeded noise, so the fitted ratings have a real signal to find.
Each team has one quarterback, with a GSIS-shaped id. Scores come from the
same strengths plus noise, so both outcomes occur and the fits converge.
Nothing here is real data, and none of it is meant to look like a season's
numbers. It exercises the code paths, not the model's accuracy.
"""
import numpy as np
import pandas as pd

TEAMS = ['BUF', 'MIA', 'NE', 'NYJ', 'KC', 'DEN', 'LV', 'LAC']
PRIOR, TARGET = 2025, 2026
PRIOR_WEEKS, PLAYED_WEEKS, TARGET_WEEK, LAST_WEEK = 21, 4, 5, 7
PLAYS_PER_SIDE = 10
STRENGTH = {t: (0.25 - 0.07 * i, -0.15 + 0.04 * ((i * 3) % 8)) for i, t in enumerate(TEAMS)}
QB = {t: (f'00-00{i + 10:05d}', f'Q.Back{i}') for i, t in enumerate(TEAMS)}


def round_robin(week):
    """Circle method: week 1..7 of an 8-team single round robin."""
    rot = [TEAMS[0]] + [TEAMS[1:][(k + week - 1) % 7] for k in range(7)]
    pairs = [(rot[k], rot[7 - k]) for k in range(4)]
    # Alternate home and away so no team is always at home.
    return [(a, b) if (week + k) % 2 else (b, a) for k, (a, b) in enumerate(pairs)]


def _kickoff_fields(ts):
    """gameday / gametime (Eastern, as nflverse gives it) / weekday for a UTC time."""
    et = pd.Timestamp(ts).tz_convert('America/New_York')
    return et.strftime('%Y-%m-%d'), et.strftime('%H:%M'), et.strftime('%A')


def _plays(rng, season, week, home, away):
    rows = []
    for off, dfn in ((home, away), (away, home)):
        base = STRENGTH[off][0] - STRENGTH[dfn][1]
        for k in range(PLAYS_PER_SIDE):
            is_pass = k % 2 == 0
            epa = float(base + rng.normal(0, 0.8))
            rows.append({
                'season': season, 'week': week, 'season_type': 'REG',
                'posteam': off, 'defteam': dfn, 'epa': epa,
                'pass': int(is_pass), 'rush': int(not is_pass),
                'play_type': 'pass' if is_pass else 'run',
                'qb_dropback': int(is_pass), 'qb_epa': epa if is_pass else np.nan,
                'passer_player_id': QB[off][0] if is_pass else None,
                'passer_player_name': QB[off][1] if is_pass else None,
            })
    return rows


def build(now, target_offsets, seed=20260929):
    """(play-by-play, {season: schedule}) with week 5 of TARGET kicking off
    at now + each of `target_offsets` (four timedeltas, one per game)."""
    assert len(target_offsets) == 4, "week 5 has four games"
    now = pd.Timestamp(now).tz_convert('UTC')
    rng = np.random.default_rng(seed)
    plays, games = [], []

    def add_game(season, week, home, away, kickoff, played):
        day, time, weekday = _kickoff_fields(kickoff)
        diff = (STRENGTH[home][0] - STRENGTH[home][1]) - (STRENGTH[away][0] - STRENGTH[away][1])
        row = {
            'season': season, 'week': week, 'game_type': 'REG',
            'home_team': home, 'away_team': away,
            'home_score': np.nan, 'away_score': np.nan,
            'spread_line': round(float(diff * 20 + 1.5), 1),
            'gameday': day, 'gametime': time, 'weekday': weekday,
            'home_qb_id': QB[home][0], 'away_qb_id': QB[away][0],
            'home_qb_name': QB[home][1], 'away_qb_name': QB[away][1],
        }
        if played:
            margin = diff * 40 + 2 + rng.normal(0, 10)
            base = 20 + int(rng.integers(0, 8))
            row['home_score'] = float(base + max(int(round(margin)), -base))
            row['away_score'] = float(base)
            if row['home_score'] == row['away_score']:
                row['home_score'] += 3
            plays.extend(_plays(rng, season, week, home, away))
        games.append(row)

    for week in range(1, PRIOR_WEEKS + 1):
        kick = now - pd.Timedelta(weeks=60 - week)
        for home, away in round_robin((week - 1) % 7 + 1):
            add_game(PRIOR, week, home, away, kick, played=True)
    for week in range(1, LAST_WEEK + 1):
        for k, (home, away) in enumerate(round_robin(week)):
            if week <= PLAYED_WEEKS:
                add_game(TARGET, week, home, away,
                         now - pd.Timedelta(weeks=TARGET_WEEK - week), played=True)
            elif week == TARGET_WEEK:
                add_game(TARGET, week, home, away, now + target_offsets[k], played=False)
            else:
                add_game(TARGET, week, home, away,
                         now + pd.Timedelta(weeks=week - TARGET_WEEK, days=1), played=False)

    sched = pd.DataFrame(games)
    schedules = {s: sched[sched['season'] == s].reset_index(drop=True) for s in (PRIOR, TARGET)}
    return pd.DataFrame(plays), schedules


def play_week(schedules, week, scores):
    """A copy of `schedules` with TARGET `week` played: scores[k] is
    (home, away) for the k-th game of round_robin(week)."""
    sched = schedules[TARGET].copy()
    for (home, away), (hs, as_) in zip(round_robin(week), scores):
        at = (sched['week'] == week) & (sched['home_team'] == home) & (sched['away_team'] == away)
        assert at.sum() == 1, (week, home, away)
        sched.loc[at, ['home_score', 'away_score']] = [float(hs), float(as_)]
    return {**schedules, TARGET: sched}


def empty_schedule():
    """A season the fixture has no games for (the pipeline asks for six)."""
    cols = ['season', 'week', 'game_type', 'home_team', 'away_team', 'home_score',
            'away_score', 'spread_line', 'gameday', 'gametime', 'weekday',
            'home_qb_id', 'away_qb_id', 'home_qb_name', 'away_qb_name']
    return pd.DataFrame(columns=cols)
