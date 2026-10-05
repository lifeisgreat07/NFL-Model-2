"""
Weekly update orchestrator -- entrypoint for the Claude Code Routine.

v2: fixes the bug the routine caught on its first offseason run -- this
previously built matchup features but never actually fit or applied the
Model A / Model B logistic regressions, so saved predictions had no real
win probabilities in them. That's fixed here: both models are trained on
full historical data and actually applied to the target week's games.

What it does, in order:
  1. Pull fresh play-by-play + schedule data (nfl_data_py -- needs network)
  2. Build historical, leak-free team + QB ratings for every past week
  3. Construct the historical training feature set (off_matchup, def_matchup,
     qb_matchup, spread_line vs actual home_win)
  4. Fit Model A (football-only) and Model B (+ market) logistic regression
     on ALL available history (for live use we want every real game we
     have, not a holdout -- backtest.py is where holdout evaluation lives)
  5. Build this week's ratings "as of right now" and apply both models
  6. Save predictions to predictions/ BEFORE kickoff (never overwrite)
  7. Grade the previous week's saved predictions against actual results
  8. Regenerate dashboard.html (not yet implemented -- see README)

What it does NOT do (needs a human or a web-search-capable agent step,
not just this script):
  - Confirm which team's QB situations are uncertain/newsworthy this week.
    The QB rating reflects historical trailing performance for whoever
    had the most dropbacks last known appearance -- a lagging signal for
    a brand-new change (new starter, injury, benching). The routine
    prompt should web-search for this and flag any contradiction.
  - Coaching-change / narrative flags -- same reasoning.

Run manually: python weekly_update.py --season 2026 --week 2
"""
from __future__ import annotations

import argparse
import json
import re
from collections import namedtuple
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from src.pipeline.atomic_write import write_json_atomic
from src.pipeline.config import MIN_PLAYS_FOR_RATING, MODEL_VERSION, TRAIN_SEASONS
from src.pipeline.data_loader import load_plays, load_schedule
from src.pipeline.data_quality import enforce as enforce_data_quality
from src.pipeline.model_specs import MODEL_SPECS

# Only get_continuity is imported: build_historical_features still accepts an
# ol_lookup so backtest.py can run its "[reference only] + OL continuity"
# comparison. The live weekly path no longer builds one -- see load_inputs().
from src.pipeline.ol_continuity import get_continuity
from src.pipeline.ratings_engine import build_qb_ratings, build_team_ratings, prep_plays
from src.pipeline.simulate_season import (
    fit_simple_win_model,
    regular_season,
    simulate_season,
)

# Don't save (lock in) predictions more than this many days before the
# earliest game in the target week. Prevents exactly the failure mode we
# hit in testing: once week-autodetection and the offseason check both
# work correctly, nothing else was stopping a routine run from generating
# and permanently saving "Week 1" predictions weeks too early, using stale
# injury/line data. 7 days keeps predictions close to kickoff without
# being so tight that a routine running a day late misses the window.
LOCKIN_WINDOW_DAYS = 7

# WHEN a week locks, decided by Mark 2026-09-22: Thursday, before Thursday
# night's kickoff, not Tuesday morning. Tuesday locked before most injury
# news, so a sourced QB override (load_qb_overrides) only helped if it
# existed two days before anyone had practised -- which worked against v2.5,
# a change whose whole point is better QB information at lock time.
#
# The scheduled workflow runs on Tuesday (grading, ratings, line snapshot)
# and on Thursday. A run locks the week when the first game still to be
# played kicks off before the NEXT scheduled run plus LOCK_SLACK; otherwise
# it holds and leaves the lock to that run. So an ordinary week locks on
# Thursday, and a week with an earlier game locks on Tuesday by itself:
# Thanksgiving's 12:30 ET kickoff is six and a half hours after the Thursday
# run, inside the slack, and a Wednesday game is before it outright.
#
# (weekday with Monday = 0, hour, minute), UTC. These MUST match the `cron:`
# lines in .github/workflows/weekly-update.yml -- the decision is only right
# if it knows when the next run is -- and tests/test_pick_lock_time.py
# compares the two.
#
# Thursday moved from 16:00 to 11:00 on 2026-09-29 (Mark): from 2026-09-24
# every scheduled run in this repository started 3.5 to 6.5 hours late,
# off-the-hour minutes included (the 2026-09-24 Thursday run at 19:34, this
# Tuesday's at 16:41). At 16:00 a 6.5-hour delay leaves under two hours
# before a Thursday night kickoff; at 11:00 it leaves about seven.
SCHEDULED_RUNS_UTC = ((1, 11, 0), (3, 11, 0))  # Tuesday 11:00, Thursday 11:00
# The slack is how late a scheduled run is assumed it may start. Eight hours
# covers the worst delay seen (6h35m, 2026-09-28) and so sends Thanksgiving
# (17:30 UTC in EST, 6.5 hours after the Thursday run) to Tuesday, while an
# ordinary Thursday night game (13 to 14 hours after the Thursday run) still
# waits for Thursday.
LOCK_SLACK = pd.Timedelta(hours=8)

# The folders are defined once, in src/pipeline/paths.py (Stage 32 item 15); the
# reasons each exists stay here, beside the code that writes them.
from src.pipeline.paths import (
    DATA_DIR,
    PRED_DIR,
    PREVIEW_DIR,
    SKIPPED_DIR,
    TEAM_NAMES,
    parse_week,
)
from src.pipeline.runlog import get_logger

log = get_logger(__name__)

from src.pipeline.ratings_engine import (
    Ratings,
    WeekKey,
)

#: One saved pick, as written to predictions/<season>_week<N>.json.
Pick = dict[str, Any]
PRED_DIR.mkdir(exist_ok=True)
# A week that kicked off with nothing ever locked is recorded here, one small
# file per week, so determine_next_week() moves past it (Stage 24). A folder,
# not a new file shape in predictions/: every reader of saved picks globs
# predictions/*_week*.json without recursing, so none of them can mistake a
# skip for a week of picks. (SKIPPED_DIR)
# A run that HOLDS a week (Tuesday, usually) saves what the models would pick
# today here, as a preview (Mark, 2026-09-29: "an update both on Tuesday and
# Thursday"). A folder for the same reason as skipped/: grading, the season
# record and determine_next_week all glob predictions/*_week*.json without
# recursing, so a preview can never be graded, counted or taken for a lock.
# Unlike a locked week it is overwritten by every later holding run; the
# locked file that Thursday writes is what the page shows from then on.
# (PREVIEW_DIR)
DATA_DIR.mkdir(exist_ok=True)



def save_current_ratings(team_ratings: Ratings, season_schedule: pd.DataFrame | None = None) -> None:
    """Write the current team ratings snapshot to data/current_ratings.json
    so generate_dashboard.py can display them without recomputing (which
    would mean re-pulling all play-by-play data a second time).

    season_schedule (optional): this season's full schedule dataframe.
    When provided, also computes each team's strength of schedule -- the
    average CURRENT net rating of opponents actually played so far (using
    our best up-to-date read on each opponent, the standard convention for
    "how tough is this team's real slate," not their rating at the time
    they were played)."""
    rows: list[dict[str, Any]] = []
    for team, (off, deff) in team_ratings.items():
        rows.append({
            'team': team, 'name': TEAM_NAMES.get(team, team),
            'off': round(off, 4), 'def': round(deff, 4), 'net': round(off - deff, 4),
        })

    if season_schedule is not None:
        played = season_schedule.dropna(subset=['home_score', 'away_score'])
        opponents: dict[str, list[str]] = {}
        for _, g in played.iterrows():
            opponents.setdefault(g['home_team'], []).append(g['away_team'])
            opponents.setdefault(g['away_team'], []).append(g['home_team'])
        for row in rows:
            opps = opponents.get(row['team'], [])
            opp_nets = [team_ratings[o][0] - team_ratings[o][1] for o in opps if o in team_ratings]
            row['sos'] = round(sum(opp_nets) / len(opp_nets), 4) if opp_nets else None
            row['games_played'] = len(opps)

    rows.sort(key=lambda r: -r['net'])
    with open(DATA_DIR / 'current_ratings.json', 'w') as f:
        json.dump(rows, f, indent=2)
    log.info(f"Saved {len(rows)} team ratings to data/current_ratings.json")


def save_playoff_odds(current_team_ratings: Ratings, season_schedule: pd.DataFrame, hist: pd.DataFrame,
                      season: int, n_sim: int = 10000) -> None:
    """Runs the Monte Carlo season simulation and writes results to
    data/playoff_odds.json. See simulate_season.py for the real,
    explicitly-stated limitations of this projection (static ratings,
    simplified tiebreakers, no future news)."""
    try:
        model = fit_simple_win_model(hist)
        results = simulate_season(current_team_ratings, season_schedule, model, n_sim=n_sim)
        reg = regular_season(season_schedule)
        played_count = reg.dropna(subset=['home_score', 'away_score']).shape[0]
        payload = {
            'season': season,
            'games_played': int(played_count),
            'games_remaining': int(len(reg) - played_count),
            'n_simulations': n_sim,
            'teams': results.to_dict(orient='records'),
        }
        with open(DATA_DIR / 'playoff_odds.json', 'w') as f:
            json.dump(payload, f, indent=2)
        log.info(f"Saved playoff odds ({n_sim} simulations, {played_count} games already decided) to data/playoff_odds.json")
    except Exception as e:
        log.warning(f"  WARNING: playoff simulation failed ({e}) -- data/playoff_odds.json not updated this run.")


def append_live_history(team_ratings: Ratings, season: int, week: int) -> None:
    """Append this week's ratings to a running per-season file, building a
    real in-season trend for the Team Deep-Dive page as the season
    progresses. Unlike current_ratings.json (a snapshot, overwritten each
    run), this file accumulates -- one entry per team per week, never
    overwritten, same pattern as the line-movement archive."""
    path = DATA_DIR / f'team_history_{season}.json'
    existing = {}
    if path.exists():
        with open(path) as f:
            existing = json.load(f)
    for team, (off, deff) in team_ratings.items():
        existing.setdefault(team, [])
        if not any(e['week'] == week for e in existing[team]):
            existing[team].append({'week': week, 'net': round(off-deff, 4), 'off': round(off,4), 'def': round(deff,4)})
    with open(path, 'w') as f:
        json.dump(existing, f, indent=2)
    log.info(f"Appended week {week} to data/team_history_{season}.json")


def market_prob(home_spread: float) -> float:
    """Simple market-implied probability from a home spread (+ = home favored)."""
    return 1 / (1 + np.exp(-home_spread / 5.5))


def build_historical_features(plays: pd.DataFrame, week_keys: list[WeekKey],
                              week_to_idx: dict[WeekKey, int],
                              team_ratings_by_week: dict[WeekKey, Ratings], qb: dict[str, Any],
                              schedules_by_season: dict[int, pd.DataFrame],
                              ol_lookup: dict | None = None,
                              qb_change_lookup: dict[tuple[int, int, str], int] | None = None,
                              ) -> pd.DataFrame:
    """Construct the training dataset: one row per historical game with
    real, leak-free matchup features and the actual outcome. ol_lookup is
    optional (from ol_continuity.compute_ol_continuity_lookup) -- if not
    provided, ol_continuity_diff defaults to 0.0 (neutral) for every row."""
    rows = []
    for season, sched in schedules_by_season.items():
        played = sched.dropna(subset=['home_score', 'away_score'])
        for _, g in played.iterrows():
            key = (g['season'], g['week'])
            if key not in team_ratings_by_week or key not in week_to_idx:
                continue
            rt = team_ratings_by_week[key]
            if g['home_team'] not in rt or g['away_team'] not in rt:
                continue
            h_off, h_def = rt[g['home_team']]
            a_off, a_def = rt[g['away_team']]

            starters = qb['identify_starters'](g['season'], g['week'])
            starters_idx = starters.set_index(['season', 'week', 'posteam'])
            hk, ak = (g['season'], g['week'], g['home_team']), (g['season'], g['week'], g['away_team'])
            if hk not in starters_idx.index or ak not in starters_idx.index:
                continue
            qb_cutoff = qb['week_to_idx'].get(key)
            if qb_cutoff is None:
                continue
            home_qb_rating = qb['trailing_rating'](starters_idx.loc[hk, 'passer_player_id'], qb_cutoff)
            away_qb_rating = qb['trailing_rating'](starters_idx.loc[ak, 'passer_player_id'], qb_cutoff)

            home_ol = get_continuity(ol_lookup, g['home_team'], g['season'], g['week'], default=0.0) if ol_lookup else 0.0
            away_ol = get_continuity(ol_lookup, g['away_team'], g['season'], g['week'], default=0.0) if ol_lookup else 0.0
            home_ol = 0.0 if home_ol is None else home_ol
            away_ol = 0.0 if away_ol is None else away_ol

            if qb_change_lookup:
                home_changed = qb_change_lookup.get((g['season'], g['week'], g['home_team']), 0)
                away_changed = qb_change_lookup.get((g['season'], g['week'], g['away_team']), 0)
            else:
                home_changed, away_changed = 0, 0

            rows.append({
                'season': g['season'], 'week': g['week'],
                'home_win': int(g['home_score'] > g['away_score']),
                # Final margin from the home team's perspective. Added
                # 2026-09-05 for ATS evaluation (src/research/ats_evaluation.py), which
                # needs the score, not just who won. Purely additive: no model
                # trains on it, and every fitted model selects its columns by
                # an explicit feature list, so nothing downstream sees it
                # unless it asks. Guarded by tests/test_ats_evaluation.py.
                'home_margin': int(g['home_score'] - g['away_score']),
                'off_matchup': h_off - a_def,
                'def_matchup': a_off - h_def,
                'qb_matchup': home_qb_rating - away_qb_rating,
                'ol_continuity_diff': home_ol - away_ol,
                'qb_change_diff': home_changed - away_changed,
                'spread_line': g.get('spread_line', np.nan),
            })
    return pd.DataFrame(rows)


def _week_numbers(folder, season):
    """Week numbers of `<season>_week<N>.json` files directly in `folder`."""
    weeks = []
    for f in folder.glob(f'{season}_week*.json'):
        key = parse_week(f.stem)
        if key is not None:
            weeks.append(key[1])
    return weeks


def determine_next_week(season: int, pred_dir: Path | None = None, skipped_dir: Path | None = None) -> int:
    """If --week isn't given, figure out the right week automatically:
    one past whatever week was most recently saved for this season.
    Starts at week 1 if nothing's been saved yet. This is what lets the
    routine run unattended all season without a manually-edited week
    number in its prompt.

    A week recorded as skipped (every game kicked off with nothing locked,
    see record_skipped_week) counts as done. Before Stage 24 it did not, so
    one missed lock made every later run ask for that same week again, and
    refuse, for the rest of the season."""
    pred_dir = PRED_DIR if pred_dir is None else pred_dir
    skipped_dir = SKIPPED_DIR if skipped_dir is None else skipped_dir
    weeks_done = _week_numbers(pred_dir, season)
    skipped = _week_numbers(skipped_dir, season)
    if weeks_done or skipped:
        latest = max(weeks_done + skipped)
        next_week = latest + 1
        how = 'skipped' if latest not in weeks_done else 'saved'
        log.info(f"Most recent {how} week for {season}: {latest}. Using week {next_week}.")
        return next_week
    log.info(f"No predictions saved yet for {season}. Starting at week 1.")
    return 1
    # Playoff numbering note (resolved -- verified against real nflverse data
    # and official docs): weeks do NOT reset after the regular season. They
    # continue counting up (e.g. 2021+: reg season 1-18, wild card 19,
    # divisional 20, conf champ 21, Super Bowl 22). So max+1 naturally walks
    # straight through the playoffs with no special-casing needed. The one
    # real edge case -- running this again after the Super Bowl -- is
    # handled in plan_week() by exiting cleanly when a week has zero games.


def refuse_an_empty_week(predictions: list[Pick], season: int, week: int) -> None:
    """Fail the run rather than save a week with no picks (Stage 24).

    A saved week can never be overwritten, so an empty file -- every game
    skipped for a missing team rating, say -- would stand as that week's
    picks for good, and determine_next_week would move past it. Failing
    instead saves nothing, opens the run's issue (Stage 4), and leaves the
    week to the next run, which can still lock whatever has not kicked off.
    """
    if not predictions:
        raise SystemExit(
            f"ERROR: {season} week {week} produced no picks, so nothing is saved. "
            f"A saved week can never be replaced, and an empty one would stand "
            f"as the week's picks. The log above says why each game was skipped; "
            f"fix that and run again before kickoff.")


def record_skipped_week(season: int, week: int, reason: str, now: pd.Timestamp,
                        skipped_dir: Path | None = None) -> Path:
    """Write predictions/skipped/<season>_week<N>.json and return its path.

    Called only when every game of a week has kicked off with nothing ever
    locked: no pick for it can be a prediction any more, so the week is done,
    and saying so is what lets the next run move on. Write-once like a week
    of picks: an existing record is left exactly as it is."""
    skipped_dir = SKIPPED_DIR if skipped_dir is None else skipped_dir
    skipped_dir.mkdir(parents=True, exist_ok=True)
    path = skipped_dir / f'{season}_week{week}.json'
    if not path.exists():
        write_json_atomic(path, {'season': season, 'week': week, 'reason': reason,
                                 'recorded_utc': pd.Timestamp(now).tz_convert('UTC').isoformat()},
                          trailing_newline=True, indent=2)
    return path


def save_preview(predictions: list[Pick], season: int, week: int, now: pd.Timestamp,
                 preview_dir: Path | None = None) -> Path | None:
    """Write predictions/preview/<season>_week<N>.json and return its path,
    or None when there is nothing to show.

    What the models would pick if the week locked now. Each pick carries
    `preview: True` and the time it was made, so nothing that reads the file
    on its own can mistake it for a locked pick. Overwritten on purpose (a
    preview is only as good as its latest run) and written atomically, since
    the page reads it. An empty preview is skipped rather than failing the
    run: unlike a lock, nothing is lost -- the locking run still comes."""
    if not predictions:
        log.warning(f"WARNING: {season} week {week} produced no picks to preview; "
              f"no preview saved.")
        return None
    preview_dir = PREVIEW_DIR if preview_dir is None else preview_dir
    preview_dir.mkdir(parents=True, exist_ok=True)
    stamp = pd.Timestamp(now).tz_convert('UTC').isoformat()
    rows = [{**p, 'preview': True, 'previewed_utc': stamp} for p in predictions]
    path = preview_dir / f'{season}_week{week}.json'
    write_json_atomic(path, rows, indent=2)
    return path


LINE_HISTORY_DIR = Path(__file__).parents[2] / 'data' / 'line_history'
LINE_HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def log_line_snapshot(season: int, week: int, week_games: pd.DataFrame,
                      now: datetime | None = None) -> None:
    """Append each game's spread to a running archive WHEN IT HAS MOVED.

    Building this over the season is how we'll eventually have real
    line-movement data to backtest against, without needing to buy
    historical odds data we don't have access to.

    A row is written when the game's spread differs from the last one
    captured for it, or when none has been (Stage 37 item 4). Until then the
    rule was one row per game per day, which wrote the same line every day
    it did not move and missed a move that happened between two runs on the
    same day. Each row carries `captured_utc`, the moment it was read, as
    well as `captured_date` (kept so older rows and readers still line up).
    A line that moves back is a move, and is written.

    A GAME WITH NO SPREAD POSTED YET IS SKIPPED, NOT WRITTEN AS NULL, and the
    reason is not tidiness. Under the per-day rule a null row this morning
    made that game a duplicate for the rest of the day, so the afternoon run
    that would have captured the real line skipped it (reproduced 2026-09-21;
    2026 week 3's snapshot was 16 rows of nulls, PR #75, closed rather than
    merged). Under the per-move rule a null would be "a change" from every
    real spread and back again. Either way it carries no spread to compare,
    and "when did this line first appear" is still answerable from the
    earliest captured row for that game. The scheduled workflows write this
    archive straight to `main`, so nothing but this function stands between
    an early run and a week of dead rows."""
    path = LINE_HISTORY_DIR / f'{season}_week{week}_lines.json'
    existing = []
    if path.exists():
        with open(path) as f:
            existing = json.load(f)

    now = (now or datetime.now(UTC)).astimezone(UTC)
    today_str = now.date().isoformat()
    captured_utc = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    # The last spread captured for each game, in file order (appended in time order).
    last_spread = {(e['home'], e['away']): e.get('spread_line') for e in existing}

    added = 0
    no_line_yet = 0
    unchanged = 0
    for _, g in week_games.iterrows():
        key = (g['home_team'], g['away_team'])
        spread = g.get('spread_line', None)
        if pd.isna(spread):
            # Skipped, not written as null -- see the docstring.
            no_line_yet += 1
            continue
        if key in last_spread and last_spread[key] == float(spread):
            unchanged += 1
            continue  # the line has not moved since it was last captured
        existing.append({
            'captured_date': today_str,
            'captured_utc': captured_utc,
            'home': g['home_team'], 'away': g['away_team'],
            # float() is intent, not a fix: numpy.float64 subclasses float
            # and json.dump already handles it, so this changes nothing and
            # is deliberately not guarded. tests/test_line_snapshot.py says
            # so, because a test over it could not fail.
            'spread_line': float(spread),
        })
        last_spread[key] = float(spread)
        added += 1

    # Three outcomes, three messages. They used to collapse into two, so a run
    # that captured nothing because no line existed yet reported a duplicate
    # -- a cause that was not the cause, which this repository has now been
    # bitten by in four separate tools.
    if added:
        with open(path, 'w') as f:
            json.dump(existing, f, indent=2)
        msg = f"Logged {added} line snapshot(s) for {season} week {week} (captured {captured_utc})."
        if unchanged:
            msg += f" {unchanged} game(s) had not moved since their last capture."
        if no_line_yet:
            msg += f" {no_line_yet} game(s) had no spread posted yet and were skipped."
        log.info(msg)
    elif no_line_yet and not unchanged:
        log.info(f"No line snapshots written for {season} week {week}: "
              f"{no_line_yet} game(s) have no spread posted yet. Nothing was "
              f"recorded, so a later run can still capture them.")
    else:
        log.info(f"Line snapshots for {season} week {week}: no line has moved since its last capture -- "
                 f"skipped duplicate.")


def build_qb_change_lookup(qb: dict[str, Any], seasons: list[int]) -> dict[tuple[int, int, str], int]:
    """Leak-free 'did this team change starting QB since last week' flag.
    Validated via backtest (2026-08-19): a real, clean improvement --
    accuracy +0.46pt, log loss/Brier/AUC all meaningfully better too,
    apples-to-apples same-sample comparison. Directly captures a known gap
    in the trailing QB rating (a lagging indicator that doesn't reflect a
    change that JUST happened this week)."""
    all_starters = []
    for s in seasons:
        try:
            all_starters.append(qb['identify_starters'](s))
        except Exception:
            continue
    if not all_starters:
        return {}
    starters = pd.concat(all_starters, ignore_index=True).sort_values(['posteam', 'season', 'week'])
    starters['prev_qb'] = starters.groupby(['posteam', 'season'])['passer_player_id'].shift(1)
    starters['qb_changed'] = ((starters['prev_qb'].notna()) &
                                (starters['passer_player_id'] != starters['prev_qb'])).astype(int)
    return starters.set_index(['season', 'week', 'posteam'])['qb_changed'].to_dict()


QB_OVERRIDE_DIR = Path(__file__).parents[2] / 'data' / 'qb_overrides'
GSIS_ID = re.compile(r'^00-\d{7}$')


class QBOverrideError(ValueError):
    """A QB override file exists but cannot be trusted. Never raised for a missing file."""


def load_qb_overrides(season: int, week: int, directory: Path | str | None = None) -> dict[str, dict]:
    """Sourced starter corrections for one week, keyed by team.

    data/qb_overrides/<season>_week<week>.json, a list of
    {"team", "player_id", "player_name", "source"}. It exists for the case
    the schedule gets wrong: on 2026-09-22 nflverse still listed Jaxson Dart
    (NYG) and Jayden Daniels (WAS) for week 3 after both were ruled out. A
    person or the routine's research step writes it, with a link, before the
    run that locks the week.

    A missing file means no overrides. A malformed one FAILS the run: an
    override is a claim about who plays, and a claim with no source or no
    valid player id is not something to predict on quietly.
    """
    path = Path(directory or QB_OVERRIDE_DIR) / f'{season}_week{week}.json'
    if not path.exists():
        return {}
    with open(path, encoding='utf-8') as f:
        entries = json.load(f)
    if not isinstance(entries, list):
        raise QBOverrideError(f"{path.name}: expected a list of overrides")
    out = {}
    for e in entries:
        missing = [k for k in ('team', 'player_id', 'player_name', 'source') if not e.get(k)]
        if missing:
            raise QBOverrideError(f"{path.name}: override {e!r} is missing {missing}")
        if not GSIS_ID.match(e['player_id']):
            raise QBOverrideError(f"{path.name}: {e['player_id']!r} is not a GSIS id (00-0000000)")
        if not str(e['source']).startswith(('http://', 'https://')):
            raise QBOverrideError(f"{path.name}: {e['team']}'s source must be a link, got {e['source']!r}")
        if e['team'] in out:
            raise QBOverrideError(f"{path.name}: two overrides for {e['team']}")
        out[e['team']] = e
    return out


def resolve_starters(game: pd.Series, starters_idx: pd.DataFrame, last_changed: dict[str, int],
                     overrides: dict[str, dict] | None = None,
                     ) -> tuple[dict[str, tuple[str | None, int]], dict[str, Any], list[str]]:
    """Which quarterback each side is predicted with, and why.

    Precedence, decided 2026-09-22 after Stage 5's H1 (see
    experiments/stage5/README.md):

      1. a sourced override (load_qb_overrides) -- late injury news;
      2. the schedule's announced starter (home_qb_id / away_qb_id);
      3. the team's last starter (most dropbacks in its last game), which is
         what the live model used for everything before this change.

    The published backtest rates each game's own starter, which scores the
    same as the announced one (Stage 5 Q0). Rungs 1 and 2 are what make the
    live pick describe the model the page publishes; rung 3 is the old
    behaviour, kept only for when nothing better exists yet, and it says so.

    qb_change follows the same logic as the backtest's flag ("this game's
    starter differs from the last one"): chosen starter != last starter.
    On rung 3 there is no new information, so it keeps the old live flag.

    Returns (per_side, fields, notes). per_side[side] = (player_id, changed).
    """
    overrides = overrides or {}
    per_side, fields, notes = {}, {}, []
    for side in ('home', 'away'):
        team = game.get(f'{side}_team')
        ann_id, ann_name = _clean(game.get(f'{side}_qb_id')), _clean(game.get(f'{side}_qb_name'))
        if team in starters_idx.index:
            last_id = starters_idx.loc[team, 'passer_player_id']
            last_name = starters_idx.loc[team, 'passer_player_name']
        else:
            last_id, last_name = None, None

        if team in overrides:
            o = overrides[team]
            chosen_id, chosen_name, basis = o['player_id'], o['player_name'], 'override'
            notes.append(f"{team}: {chosen_name} is expected to start ({o['source']}), "
                         f"so the pick uses {chosen_name}.")
        elif ann_id:
            chosen_id, chosen_name, basis = ann_id, ann_name, 'announced'
            if last_id and ann_id != last_id:
                notes.append(f"{team}: the pick uses {ann_name}, the listed starter, "
                             f"not {last_name}, who started {team}'s last game.")
        else:
            chosen_id, chosen_name, basis = last_id, last_name, 'last_game'
            if last_id:
                notes.append(f"{team}: no starter has been listed yet, so the pick uses "
                             f"{last_name}, who started {team}'s last game.")

        if basis == 'last_game':
            changed = int(last_changed.get(team, 0))
        else:
            changed = int(bool(last_id) and chosen_id != last_id)
        per_side[side] = (chosen_id, changed)
        fields.update({
            f'{side}_qb_id': chosen_id, f'{side}_qb': chosen_name, f'{side}_qb_basis': basis,
            f'announced_{side}_qb_id': ann_id, f'announced_{side}_qb': ann_name,
            f'last_game_{side}_qb_id': last_id, f'last_game_{side}_qb': last_name,
        })
    return per_side, fields, notes


def _clean(value):
    return value if isinstance(value, str) and value else None


def starter_warning(week_games: pd.DataFrame, overrides: dict[str, dict], season: int,
                    week: int) -> str | None:
    """A WARNING line when a week about to be LOCKED has no announced starter
    and no override for any team, else None (Stage 25, after #184).

    Called only on the path that saves picks. #184 first put this in the
    data-quality step, which runs on every weekly run, so a Tuesday run
    holding next week before nflverse had listed its starters would have
    warned about a week it was not picking. Here it fires only when every
    pick is about to be rated on last game's quarterback."""
    teams = set(week_games['home_team']) | set(week_games['away_team'])
    if teams & set(overrides or {}):
        return None
    for side in ('home', 'away'):
        col = f'{side}_qb_id'
        if col in week_games.columns and any(_clean(v) for v in week_games[col]):
            return None
    return (f"WARNING: {season} week {week} is being locked with no announced starting "
            f"quarterback and no override for any team, so every pick uses last game's "
            f"quarterback.")


def site_is_neutral(game: pd.Series) -> bool | None:
    """True at a neutral site, False at the home team's, None when the
    schedule does not say (Stage 37 item 6)."""
    loc = game.get('location')
    if loc is None or (not isinstance(loc, str) and pd.isna(loc)):
        return None
    return str(loc).strip().lower() == 'neutral'


def _venue(game: pd.Series) -> str | None:
    v = game.get('stadium')
    return str(v) if isinstance(v, str) and v.strip() else None


def kickoff_utc(game: pd.Series) -> pd.Timestamp | None:
    """A game's kickoff as a UTC timestamp, or None with no gameday.

    gametime is EASTERN (see the record builder in predict_week()), and ET is EDT or
    EST depending on the date, so it is localised rather than offset by a
    fixed four or five hours. A missing time counts as the START of that
    day, Eastern: the earliest the game could be, which is the safe
    direction for both uses in decide_lock -- it locks earlier, and it
    treats the game as started sooner rather than later.
    """
    day = game.get('gameday')
    if day is None or (not isinstance(day, str) and pd.isna(day)):
        return None
    t = game.get('gametime')
    t = t if isinstance(t, str) and t else '00:00'
    local = pd.Timestamp(f"{pd.Timestamp(day).date()} {t}")
    return local.tz_localize('America/New_York').tz_convert('UTC')


def next_scheduled_run(now: pd.Timestamp, runs: tuple[tuple[int, int, int], ...] = SCHEDULED_RUNS_UTC,
                       ) -> pd.Timestamp:
    """The first scheduled run strictly after `now` (UTC)."""
    now = pd.Timestamp(now).tz_convert('UTC')
    times = []
    for weekday, hour, minute in runs:
        day = now.normalize() + pd.Timedelta(days=(weekday - now.weekday()) % 7)
        t = day + pd.Timedelta(hours=hour, minutes=minute)
        if t <= now:
            t += pd.Timedelta(days=7)
        times.append(t)
    return min(times)


LockDecision = namedtuple('LockDecision', 'lock started first_kickoff next_run')


def decide_lock(week_games: pd.DataFrame, now: pd.Timestamp,
                runs: tuple[tuple[int, int, int], ...] = SCHEDULED_RUNS_UTC,
                slack: pd.Timedelta = LOCK_SLACK) -> LockDecision:
    """Whether this run locks the week, and which games it is too late for.

    lock          -- True when the first game still to come kicks off before
                     the next scheduled run plus `slack`.
    started       -- (away, home) for every game that has already kicked
                     off. Those are never predicted: a pick saved after
                     kickoff is not a prediction, and the Methodology page
                     says every pick is locked before kickoff. On a
                     Tuesday lock this was ~61 hours of margin and could
                     not happen; on a Thursday lock it is about 13 (11:00
                     UTC to a 00:15 UTC Friday kickoff), and runs here start
                     up to 6.5 hours late, so a late or failed Thursday run
                     followed by a manual one can meet it.
    first_kickoff -- the earliest kickoff among games not yet started.
    next_run      -- when the next scheduled run is.

    A week with no known kickoff at all locks, as it did before this rule
    existed: there is nothing to hold for, and plan_week() already warns.
    """
    now = pd.Timestamp(now).tz_convert('UTC')
    next_run = next_scheduled_run(now, runs)
    started, upcoming = [], []
    for _, g in week_games.iterrows():
        k = kickoff_utc(g)
        if k is None:
            continue
        if k <= now:
            started.append((g['away_team'], g['home_team']))
        else:
            upcoming.append(k)
    if not upcoming:
        # Every known game has started (lock=False, plan_week() fails the run),
        # or no game has a known kickoff (lock=True, the old behaviour).
        return LockDecision(not started, started, None, next_run)
    first = min(upcoming)
    return LockDecision(first < next_run + slack, started, first, next_run)


def main(season: int, week: int) -> None:
    """One weekly run: read and check the data, fit the two models, refresh
    the current ratings and odds, decide what this run may do with the
    target week, then predict it and save the picks or a preview.

    Each step is its own function below, in the order it runs (Stage 32
    item 16, which split a 300-line main). What is printed, and in what
    order, is unchanged: src/pipeline/weekly_summary.py reads this log.
    tests/test_weekly_update_end_to_end.py runs the whole of it."""
    log.info(f"=== Weekly update: {season} Week {week} ===")

    inputs = load_inputs(season)
    model_a, model_b = fit_models(inputs.hist)
    current = refresh_current_state(inputs, season)
    plan = plan_week(season, week)
    if plan is None:
        return
    predictions = predict_week(plan.week_games, plan.started, current, inputs.qb,
                               (model_a, model_b), plan.qb_overrides, season, week)
    save_week(predictions, season, week, plan.preview)


Inputs = namedtuple('Inputs', 'raw plays week_keys week_to_idx qb qb_change_lookup '
                              'schedules_by_season hist')
Current = namedtuple('Current', 'team_ratings qb_cutoff starters_idx qb_changed')
Plan = namedtuple('Plan', 'week_games started preview qb_overrides')


def load_inputs(season: int) -> Inputs:
    """Step 1: every input the fits need, checked before anything is fitted."""
    log.info("Loading play-by-play data...")
    seasons_needed = sorted(set(TRAIN_SEASONS) | {season})
    raw = load_plays(seasons_needed)
    plays, week_keys, week_to_idx = prep_plays(raw)

    log.info("Building historical team ratings for every past week (leak-free)...")
    team_ratings_by_week = build_team_ratings(plays, week_keys, upto_cutoff_i=None)

    log.info("Building QB ratings...")
    qb = build_qb_ratings(raw)

    # No snap-count load here on purpose. O-line continuity came out of the
    # model at v2.1, and neither fitted model below uses ol_continuity_diff --
    # so loading six seasons of snap counts every Tuesday only produced a
    # number that was written to disk and read by nobody. Removing it takes a
    # whole upstream data source out of the unattended job; load_snap_counts is
    # in the same family as the call behind the 2026 Week 1 offseason crash
    # (tests/test_data_loader.py), so this is one less way for the 6am run to
    # fail. The feature itself is NOT gone: ol_continuity.py, the leak-free
    # tests covering it, and backtest.py's "[reference only] + OL continuity"
    # comparison all still exist, and backtest.py builds its own lookup from
    # snap counts rather than reading saved predictions -- so nothing about
    # revisiting OL continuity later depends on this field being stored.
    # Guarded by tests/test_weekly_pipeline.py.

    log.info("Building QB-change (backup detection) lookup...")
    qb_change_lookup = build_qb_change_lookup(qb, seasons_needed)
    log.info(f"  Detected {sum(qb_change_lookup.values())} QB changes across {len(qb_change_lookup)} team-weeks")

    log.info("Loading schedules (scores + lines) for training history...")
    schedules_by_season = {s: load_schedule(s) for s in seasons_needed}

    # Before anything is fitted: a bad week caught after the fits is
    # already inside the picks. Errors stop the run; warnings are printed and
    # carried into the weekly summary. See src/pipeline/data_quality.py for which is
    # which and why.
    log.info("Checking data quality...")
    enforce_data_quality(raw, schedules_by_season[season], season)

    log.info("Constructing historical training features...")
    hist = build_historical_features(plays, week_keys, week_to_idx, team_ratings_by_week,
                                       qb, schedules_by_season, ol_lookup=None, qb_change_lookup=qb_change_lookup)
    log.info(f"  {len(hist)} historical games with complete features")
    if len(hist) < 100:
        log.warning("WARNING: very little historical training data -- predictions below may be unreliable.")
    return Inputs(raw, plays, week_keys, week_to_idx, qb, qb_change_lookup,
                  schedules_by_season, hist)


def fit_models(hist: pd.DataFrame) -> tuple[LogisticRegression, LogisticRegression]:
    """Step 2: Model A (football only) and Model B (+ the market's spread).

    Fitted from MODEL_SPECS (src/pipeline/model_specs.py), the same specs
    the backtest scores, on every game with all of that model's features.
    predict_week builds each model's row in MODEL_A_FEATURES order, and its
    "why" breakdown names the coefficients in that order too."""
    log.info("Fitting Model A (football-only) and Model B (+ market)...")
    return MODEL_SPECS['model_a'].fit(hist), MODEL_SPECS['model_b'].fit(hist)


def current_ratings(plays: pd.DataFrame, week_keys: list[WeekKey]) -> Ratings:
    """The ratings as of right now: one fit over every play loaded.

    build_team_ratings returns None when fewer than MIN_PLAYS_FOR_RATING
    plays come before the cutoff. The live run loads six seasons, so that
    cannot happen today; but nothing enforced it, and if it ever did, the
    three writers below would each have crashed on None mid-run. It fails
    here instead, before anything is written, saying why (Stage 35, found
    when the third audit's overloads let mypy see the None)."""
    ratings = build_team_ratings(plays, week_keys, upto_cutoff_i=len(week_keys))
    if ratings is None:
        raise SystemExit(
            f"ERROR: fewer than {MIN_PLAYS_FOR_RATING} plays are loaded, too few to rate "
            f"any team. Nothing was written. Check the play-by-play load above.")
    return ratings


def refresh_current_state(inputs: Inputs, season: int) -> Current:
    """Step 3: the ratings as of right now, written for the page (ratings,
    playoff odds, this season's history), and each team's current starter."""
    plays, week_keys = inputs.plays, inputs.week_keys
    qb, hist, schedules_by_season = inputs.qb, inputs.hist, inputs.schedules_by_season
    log.info("Building current ('as of right now') team + QB ratings...")
    current_team_ratings = current_ratings(plays, week_keys)
    save_current_ratings(current_team_ratings, season_schedule=schedules_by_season.get(season))
    save_playoff_odds(current_team_ratings, schedules_by_season.get(season), hist, season)
    current_season_weeks = [w for (s, w) in week_keys if s == season]
    if current_season_weeks:
        last_completed_week = max(current_season_weeks)
        append_live_history(current_team_ratings, season, last_completed_week)
    else:
        log.info(f"No completed weeks yet for {season} -- skipping live history entry "
              f"(these ratings reflect prior-season data, not a real {season} week).")
    qb_cutoff = len(qb['week_keys'])
    # fallback starter source: most recent season with any starter data
    starter_season = season if season in [s for s, w in qb['week_keys']] else season - 1
    current_starters = qb['identify_starters'](starter_season)
    current_starters_idx = current_starters.sort_values('week').drop_duplicates(subset=['posteam'], keep='last').set_index('posteam')

    # "Did this team just change starters" as of right now: compare the two
    # most recent known starts per team (not the leak-free historical
    # lookup, which only covers completed weeks -- this is the live,
    # forward-looking version of the same signal).
    current_qb_changed = {}
    for team, grp in current_starters.sort_values('week').groupby('posteam'):
        if len(grp) >= 2:
            last_two = grp.tail(2)['passer_player_id'].tolist()
            current_qb_changed[team] = int(last_two[0] != last_two[1])
        else:
            current_qb_changed[team] = 0
    return Current(current_team_ratings, qb_cutoff, current_starters_idx, current_qb_changed)


def plan_week(season: int, week: int) -> Plan | None:
    """Step 4: what this run may do with the target week. None when there
    is nothing to do (no games, too early, already locked and started);
    raises SystemExit when every game kicked off with nothing locked;
    otherwise the games still to pick, those already started, whether this
    run holds (a preview) or locks, and any sourced QB overrides."""
    log.info("Loading target week's schedule + current lines...")
    sched = load_schedule(season)
    week_games = sched[sched['week'] == week]

    if len(week_games) == 0:
        log.info(f"No games found for {season} week {week} -- likely means the season "
              f"(including playoffs) is over. Nothing to predict. Exiting cleanly.")
        return None

    # Line-movement archive: log today's spread for every game in the target
    # week, EVERY time this runs -- including the weeks before the lock-in
    # guard allows real predictions. This is deliberately placed before that
    # guard so we capture multiple readings over time as kickoff approaches
    # (e.g. a reading from 3 weeks out, another from 1 week out, another the
    # day before). Unlike predictions/, this file is meant to accumulate
    # multiple entries over time -- append, don't treat as write-once.
    log_line_snapshot(season, week, week_games)

    if 'gameday' in week_games.columns:
        earliest = pd.to_datetime(week_games['gameday']).min()
        if pd.notna(earliest):
            days_until = (earliest.date() - date.today()).days
            if days_until > LOCKIN_WINDOW_DAYS:
                log.info(f"Earliest game in {season} week {week} is {earliest.date()} "
                      f"({days_until} days away). That's more than the {LOCKIN_WINDOW_DAYS}-day "
                      f"lock-in window -- too early for injury/QB info to be reliable. "
                      f"Skipping this run without saving anything. Re-run closer to kickoff.")
                return None
    else:
        log.warning("WARNING: schedule data has no 'gameday' column -- can't check how far out "
              "this week is. Proceeding anyway, but this safety check isn't active.")

    # Inside the window is not the same as time to lock. See SCHEDULED_RUNS_UTC.
    decision = decide_lock(week_games, pd.Timestamp.now(tz='UTC'))
    # A week already locked is finished business, whatever the clock says
    # now (Stage 30 item 4). Without this, `--week N` run after every game
    # of a LOCKED week had kicked off fell into the branch below and wrote a
    # skip record beside the saved picks -- a week both locked and skipped --
    # and failed the run.
    locked_path = PRED_DIR / f'{season}_week{week}.json'
    if decision.started and not decision.lock and locked_path.exists():
        log.info(f"{season} week {week} is already locked in predictions/{locked_path.name}, "
              f"and every game has kicked off. Nothing to do.")
        return None
    if decision.started and not decision.lock:
        # Still a failure -- the run fails and opens its issue (Stage 4) --
        # but the week is recorded as skipped first, so the next run moves
        # on to the week after instead of refusing this one forever.
        skipped = record_skipped_week(
            season, week, 'every game kicked off with nothing locked',
            pd.Timestamp.now(tz='UTC'))
        raise SystemExit(
            f"ERROR: every game in {season} week {week} has already kicked off and "
            f"nothing was ever locked for it. A pick saved now would not be a "
            f"prediction, so none is saved. The scheduled runs missed this week: "
            f"check the Actions history. Recorded as skipped in "
            f"predictions/skipped/{skipped.name}, so the next run moves on to "
            f"week {week + 1}.")
    # Holding is not the same as saying nothing: the picks as they stand are
    # built the same way and saved as a preview (PREVIEW_DIR), never as a lock.
    preview = not decision.lock
    if preview:
        log.info(f"Holding {season} week {week}: its first game kicks off "
              f"{decision.first_kickoff:%a %Y-%m-%d %H:%M} UTC, after the next scheduled "
              f"run ({decision.next_run:%a %Y-%m-%d %H:%M} UTC), which will lock it with "
              f"whatever QB news has landed by then. Saving a preview only; "
              f"nothing is locked.")
    started = set(decision.started)
    for away, home in decision.started:
        log.warning(f"WARNING: {away}@{home} has already kicked off and gets NO pick. The run "
              f"that should have locked it did not; a pick saved after kickoff is not a "
              f"prediction.")

    qb_overrides = load_qb_overrides(season, week)
    if qb_overrides:
        log.info(f"  QB overrides for week {week}: " + ", ".join(
            f"{t} -> {o['player_name']}" for t, o in sorted(qb_overrides.items())))
    # Lock time only (#186): on a Tuesday preview nflverse has usually not
    # listed next week's starters yet, so the warning would fire every week.
    no_starters = None if preview else starter_warning(week_games, qb_overrides, season, week)
    if no_starters:
        log.warning(no_starters)
    return Plan(week_games, started, preview, qb_overrides)


def predict_week(week_games: pd.DataFrame, started: set[tuple[str, str]], current: Current,
                 qb: dict[str, Any], models: tuple[LogisticRegression, LogisticRegression],
                 qb_overrides: dict[str, dict], season: int, week: int) -> list[Pick]:
    """Step 5: one pick per game not yet started, ranked by confidence."""
    model_a, model_b = models
    current_team_ratings, qb_cutoff = current.team_ratings, current.qb_cutoff
    current_starters_idx, current_qb_changed = current.starters_idx, current.qb_changed
    predictions = []
    for _, g in week_games.iterrows():
        home, away = g['home_team'], g['away_team']
        if (away, home) in started:
            continue
        if home not in current_team_ratings or away not in current_team_ratings:
            log.info(f"  Skipping {away}@{home}: no team rating available")
            continue
        h_off, h_def = current_team_ratings[home]
        a_off, a_def = current_team_ratings[away]
        off_matchup = h_off - a_def
        def_matchup = a_off - h_def

        per_side, qb_fields, context_notes = resolve_starters(
            g, current_starters_idx, current_qb_changed, qb_overrides)
        (home_qb_id, home_qb_changed), (away_qb_id, away_qb_changed) = per_side['home'], per_side['away']
        if home_qb_id and away_qb_id:
            home_qb_rating = qb['trailing_rating'](home_qb_id, qb_cutoff)
            away_qb_rating = qb['trailing_rating'](away_qb_id, qb_cutoff)
            qb_matchup = home_qb_rating - away_qb_rating
        else:
            qb_matchup = 0.0
            context_notes.append("No known starter found -- QB feature defaulted to neutral (0). Verify manually.")

        # OL continuity was removed from the live model at v2.1 (Stage 6 OL
        # Model V2 pass) after two independent negative tests -- Stage 1's
        # bootstrap CI included zero, and the confirmatory test had "no OL
        # feature" beating both raw and smoothed versions. It was kept here
        # afterwards as saved-but-unused data; that stopped 2026-09-04, since
        # nothing ever read the saved value and producing it cost the weekly
        # job an entire upstream data source. See the comment in load_inputs()
        # above the QB-change lookup for the full reasoning.

        qb_change_diff = home_qb_changed - away_qb_changed

        prob_a = model_a.predict_proba([[off_matchup, def_matchup, qb_matchup, qb_change_diff]])[0][1]

        # "Why" breakdown: each feature's raw contribution to the log-odds,
        # i.e. coefficient * feature value. Signed toward home team (positive
        # = pushes toward home win). This is exactly what the logistic
        # regression actually used -- not a post-hoc approximation.
        coefs = model_a.coef_[0]
        why = {
            'off_matchup': round(float(coefs[0] * off_matchup), 4),
            'def_matchup': round(float(coefs[1] * def_matchup), 4),
            'qb_matchup': round(float(coefs[2] * qb_matchup), 4),
            'qb_change': round(float(coefs[3] * qb_change_diff), 4),
        }

        spread = g.get('spread_line', np.nan)
        if pd.notna(spread):
            prob_b = model_b.predict_proba([[off_matchup, def_matchup, qb_matchup, qb_change_diff, spread]])[0][1]
            mkt = market_prob(spread)
        else:
            prob_b, mkt = None, None

        # When the game is played. These three come straight off the schedule
        # frame -- data_loader does not subset columns, so they have always
        # been in scope here and simply were not written down, which is why
        # the Week Board has no chronological order and the card has no start
        # time. There is no broadcast-network column in this source at all;
        # espn/ftn/pff/pfr are cross-reference IDs. Channel needs a new feed.
        #
        # gametime is EASTERN. Established from the distribution rather than
        # assumed: the six Sunday 09:30 kickoffs in a season are the London
        # and Munich games, which are 2:30pm local -- a figure that is only
        # coherent as ET. The zone lives in the FIELD NAME for the same
        # reason a measured number ships with its command: a time whose zone
        # is unstated is unfalsifiable by anyone but its author. Note for
        # whoever renders it that ET is EDT until early November and EST
        # after, so week 10 onward crosses the US clock change.
        gameday = g.get('gameday')
        gametime = g.get('gametime')
        weekday = g.get('weekday')

        predictions.append({
            'season': season, 'week': week, 'home': home, 'away': away,
            # Stage 37 item 6: a game at a neutral site (London, Munich,
            # Sao Paulo...) still has a listed home team, and both models
            # still give it the home edge; the card says so. nflverse's
            # `location` is 'Home' or 'Neutral'. Optional columns: absent
            # means unknown (None), never a guessed False.
            'neutral_site': site_is_neutral(g),
            'venue': _venue(g),
            'gameday': str(gameday) if pd.notna(gameday) else None,
            'gametime_et': str(gametime) if pd.notna(gametime) else None,
            'weekday': str(weekday) if pd.notna(weekday) else None,
            'model_version': MODEL_VERSION,
            'off_matchup': round(off_matchup, 4), 'def_matchup': round(def_matchup, 4),
            'qb_matchup': round(qb_matchup, 4),
            'qb_change_diff': qb_change_diff,
            'spread_line': spread if pd.notna(spread) else None,
            'model_a_home_win_prob': round(float(prob_a), 4),
            'model_b_home_win_prob': round(float(prob_b), 4) if prob_b is not None else None,
            'market_prob_home': round(mkt, 4) if mkt is not None else None,
            'context_notes': context_notes,
            # Populated by the routine's web-search step (a script alone can't
            # research current news) -- see README for the expected prompt
            # addition. Left as None here; the routine appends real findings
            # (injuries, coaching/staff changes, anything else worth flagging)
            # before this file gets committed. A script-only run leaves this
            # empty, which the dashboard displays honestly as "no notes yet"
            # rather than fabricating something.
            'why': why,
            **qb_fields,
        })

    # Confidence ranking: sort this week's games by how far each pick is
    # from a toss-up (using Model B's probability when available, since
    # it's the better-performing model; falls back to Model A otherwise).
    # Rank 1 = most confident. Standard confidence-pool points = N..1.
    def confidence_key(p):
        prob = p['model_b_home_win_prob'] if p['model_b_home_win_prob'] is not None else p['model_a_home_win_prob']
        return abs(prob - 0.5)

    ranked = sorted(predictions, key=confidence_key, reverse=True)
    n = len(ranked)
    for i, p in enumerate(ranked):
        p['confidence_rank'] = i + 1
        p['confidence_points'] = n - i
    return predictions


def save_week(predictions: list[Pick], season: int, week: int, preview: bool) -> None:
    """Step 6: a preview, or the week's picks, which are permanent once saved."""
    if preview:
        path = save_preview(predictions, season, week, pd.Timestamp.now(tz='UTC'))
        if path is not None:
            log.info(f"Saved a preview of {len(predictions)} picks to "
                  f"predictions/preview/{path.name} (not locked, never graded)")
        return

    out_path = PRED_DIR / f'{season}_week{week}.json'
    if out_path.exists():
        log.warning(f"WARNING: {out_path} already exists -- NOT overwriting (predictions are permanent once saved).")
    else:
        refuse_an_empty_week(predictions, season, week)
        # Atomic: this file can never be overwritten, so a half-written one
        # would be permanent (Stage 24).
        write_json_atomic(out_path, predictions, indent=2)
        # The week's Tuesday preview is superseded the moment it locks
        # (Stage 30 item 3). The page already ignores a locked week's
        # preview; deleting it keeps a stale file out of predictions/, and
        # the workflow's predictions/** pattern stages the deletion.
        stale = PREVIEW_DIR / f'{season}_week{week}.json'
        if stale.exists():
            stale.unlink()
            log.info(f"Removed predictions/preview/{stale.name}: the week is locked now.")
        log.info(f"Saved {len(predictions)} predictions to {out_path}")
        for p in predictions:
            log.info(f"  {p['away']} @ {p['home']}: Model A home={p['model_a_home_win_prob']:.1%}"
                  + (f", Model B home={p['model_b_home_win_prob']:.1%}" if p['model_b_home_win_prob'] else "")
                  + (f"  [notes: {'; '.join(p['context_notes'])}]" if p['context_notes'] else ""))

    log.info("\nNOTE: run grade_predictions.py separately once this week's games complete.")
    log.info("NOTE: this script does not regenerate dashboard.html yet -- see generate_dashboard.py.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--season', type=int, required=True)
    parser.add_argument('--week', type=int, default=None,
                         help='Week number. If omitted, auto-detects the next '
                              'un-saved week for this season.')
    args = parser.parse_args()
    week = args.week if args.week is not None else determine_next_week(args.season)
    main(args.season, week)
