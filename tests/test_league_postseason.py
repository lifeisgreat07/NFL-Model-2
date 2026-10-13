"""
The postseason on the synthetic league: weeks 19 to 22 locked, played and
graded in turn, then the empty week 23 (Stage 39 item 1, from the
2026-10-04 fourth audit: "playoff weeks 19 to 22 and an empty week 23").

Nothing ran the pipeline past the regular season before this file. What
each round must do:

  19 Wild Card, 20 Divisional, 21 Conference, 22 Super Bowl
      -- every game gets a pick when the week locks; each pick carries its
         round's `game_type` as the schedule gives it (Stage 68 item 27);
         the week grades in full once played, and leaves nothing open for
         the weekend refresh.
  22 Super Bowl
      -- nflverse lists it with `location` 'Neutral', so neither model
         gives the listed home team a home edge (Stage 38 N1, v2.6).
  23 (no games)
      -- after the Super Bowl the Tuesday and Thursday runs keep coming
         until the season turns over (Stage 40, January). Each must exit
         cleanly: no picks, no preview, no skip record, no failed run.
         determine_next_week walks straight from 19 to 23; the note under
         it says so, and this is where that is executed rather than read.

The rounds' sizes here are the synthetic league's (4, 2, 2, 1 games; eight
teams), not the NFL's (6, 4, 2, 1); `check_build` for 6-, 4-, 2- and
1-game weeks is held by #360's tests. The bracket is not consistent, and
nothing here needs it to be: no code reads who advanced.

The whole chain runs once for the module (five weekly runs, about three
seconds here), and each test reads what it left behind.

Run with: pytest tests/test_league_postseason.py -v
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent))

import synthetic_league as league

from src.sports.nfl import data_loader
from src.sports.nfl import grade_predictions as gp
from src.sports.nfl import weekend_refresh as wr
from src.sports.nfl import weekly_update as wu

H = pd.Timedelta(hours=1)
S = league.TARGET
# (week, game_type, unplayed regular-season week whose rows it reuses, which rows)
ROUNDS = [(19, 'WC', 5, slice(0, 4)), (20, 'DIV', 6, slice(0, 2)),
          (21, 'CON', 7, slice(0, 2)), (22, 'SB', 6, slice(2, 3))]
GAMES = {week: len(range(4)[rows]) for week, _, _, rows in ROUNDS}
TYPES = {week: gtype for week, gtype, _, _ in ROUNDS}


def postseason_schedules(now):
    """(play-by-play, schedules): the synthetic league with TARGET's weeks
    1-4 played, as built, and its unplayed weeks 5-7 replaced by weeks
    19-22. Every playoff game kicks off within hours of `now`, so each week
    locks when its run comes."""
    pbp, schedules = league.build(now, [H, 2 * H, 3 * H, 4 * H])
    sched = schedules[S]
    reg = sched[sched['week'] <= league.PLAYED_WEEKS].assign(location=np.nan)
    playoff = []
    for week, gtype, source, rows in ROUNDS:
        for k, (_, row) in enumerate(sched[sched['week'] == source].iloc[rows].iterrows()):
            row = row.copy()
            row['week'], row['game_type'] = week, gtype
            row['location'] = 'Neutral' if gtype == 'SB' else 'Home'
            row['gameday'], row['gametime'], row['weekday'] = league._kickoff_fields(now + (k + 1) * H)
            playoff.append(row)
    full = pd.concat([reg, pd.DataFrame(playoff)], ignore_index=True)
    return pbp, {**schedules, S: full}


def with_scores(schedules, week):
    """A copy with `week` played: home wins the even-numbered games, away
    the odd. No ties; a playoff game has none."""
    sched = schedules[S].copy()
    at = sched.index[sched['week'] == week]
    for k, i in enumerate(at):
        sched.loc[i, ['home_score', 'away_score']] = [24.0, 17.0] if k % 2 == 0 else [13.0, 20.0]
    return {**schedules, S: sched}


@pytest.fixture(scope='module')
def season(tmp_path_factory):
    """Run the postseason once. Returns what it left: the folders, the
    next week asked for after each lock, and the week-23 run's outcome."""
    tmp = tmp_path_factory.mktemp('postseason')
    dirs = {'pred': tmp / 'predictions', 'results': tmp / 'results',
            'status': tmp / 'data' / 'game_status', 'data': tmp / 'data'}
    for p in dirs.values():
        p.mkdir(parents=True, exist_ok=True)
    out = {'dirs': dirs, 'next_week': [], 'week23': None}
    with pytest.MonkeyPatch.context() as mp:
        for name, path in (('PRED_DIR', dirs['pred']), ('SKIPPED_DIR', dirs['pred'] / 'skipped'),
                           ('PREVIEW_DIR', dirs['pred'] / 'preview'), ('DATA_DIR', dirs['data']),
                           ('LINE_HISTORY_DIR', dirs['data'] / 'line_history'),
                           ('QB_OVERRIDE_DIR', dirs['data'] / 'qb_overrides')):
            path.mkdir(parents=True, exist_ok=True)
            mp.setattr(wu, name, path)
        real_simulate = wu.simulate_season
        mp.setattr(wu, 'simulate_season',
                   lambda *a, n_sim=10000, **k: real_simulate(*a, n_sim=200, **k))
        mp.setattr(gp, 'PRED_DIR', dirs['pred'])
        mp.setattr(gp, 'RESULTS_DIR', dirs['results'])
        now = pd.Timestamp.now(tz='UTC')
        pbp, schedules = postseason_schedules(now)
        current = {'s': schedules}
        mp.setattr(wu, 'load_plays', lambda seasons: pbp[pbp['season'].isin(seasons)])
        mp.setattr(wu, 'load_schedule',
                   lambda season: current['s'].get(season, league.empty_schedule()))
        mp.setattr(data_loader, 'load_schedule', lambda season: current['s'][season])

        for week, _, _, _ in ROUNDS:
            wu.main(S, week)
            out['next_week'].append(wu.determine_next_week(S))
            current['s'] = with_scores(current['s'], week)
            gp.main(S, week)
        try:
            out['week23'] = wu.main(S, 23)
        except SystemExit as e:  # the run would fail and open an issue
            out['week23'] = e
        out['open_weeks'] = wr.weeks_to_refresh(S, pred_dir=dirs['pred'], results_dir=dirs['results'])
    return out


def picks(season, week):
    return json.loads((season['dirs']['pred'] / f'{S}_week{week}.json').read_text(encoding='utf-8'))


def graded(season, week):
    return json.loads((season['dirs']['results'] / f'{S}_week{week}_graded.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('week', sorted(GAMES))
def test_every_playoff_game_is_picked_and_carries_its_round(season, week):
    saved = picks(season, week)
    assert len(saved) == GAMES[week]
    assert {p['game_type'] for p in saved} == {TYPES[week]}
    assert {p['week'] for p in saved} == {week}


@pytest.mark.parametrize('week', sorted(GAMES))
def test_every_playoff_week_is_graded_in_full(season, week):
    rows = graded(season, week)
    assert len(rows) == GAMES[week]
    for r in rows:
        for key in ('model_a_correct', 'model_b_correct', 'market_correct'):
            assert r[key] in (0, 1), (key, r)


def test_the_super_bowl_gives_no_home_edge_and_the_other_rounds_do(season):
    (sb,) = picks(season, 22)
    assert sb['neutral_site'] is True and sb['home_edge_removed'] is True
    for week in (19, 20, 21):
        for p in picks(season, week):
            assert p['neutral_site'] is False and not p['home_edge_removed'], p


def test_the_next_week_walks_from_the_wild_card_to_23(season):
    assert season['next_week'] == [20, 21, 22, 23]


def test_week_23_exits_cleanly_and_writes_nothing(season):
    assert not isinstance(season['week23'], BaseException), season['week23']
    pred = season['dirs']['pred']
    for folder in (pred, pred / 'preview', pred / 'skipped'):
        assert not list(folder.glob(f'{S}_week23*')), folder


def test_nothing_is_left_open_after_the_super_bowl(season):
    assert season['open_weeks'] == []
