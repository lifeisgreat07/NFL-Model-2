"""Team news for the week's cards: which starters will not play, and whether
the quarterback changed. Short on purpose (Stage 16).

The hypothesis, stated before building (CLAUDE.md Stage 16): a reader
deciding whether to trust a pick needs two things -- which STARTERS are not
expected to play, and whether the QUARTERBACK is someone new. Every other
line of an injury report is noise for that reader. So this keeps:

- Starters listed Out or Doubtful on the official injury report, by name.
  A starter is rank 1 on the team's latest depth chart, on offense or
  defense, plus the kicker and punter.
- Starters listed Questionable, as a COUNT, not a list.
- The quarterback the pick was made with, read from the saved prediction
  itself (v2.5 predictions carry `home_qb`, its basis and last game's
  starter), and whether he differs from last game's. One source of truth:
  the news line cannot name a different quarterback from the one the model
  used.

ABSENT IS NOT HEALTHY. Until a week's injury report is published, a team's
entry says so (`injury_report: "not yet published"`) instead of an empty
list, which would read as "nobody hurt". Nothing is filled in.

Writes data/team_news/<season>_week<N>.json for each locked week not yet
fully graded (--pending) or the weeks named. Items expire with their week:
each file is one week.

    python src/team_news.py --pending
    python src/team_news.py --season 2026 --weeks 4
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

ROOT = Path(__file__).parent.parent
NEWS_DIR = ROOT / 'data' / 'team_news'
PRED_DIR = ROOT / 'predictions'
RESULTS_DIR = ROOT / 'results'
KICKING = ('PK', 'P')
SOURCES = {'injuries': 'nflverse injury report, via nflreadpy.load_injuries',
           'depth_chart': 'nflverse depth charts, via nflreadpy.load_depth_charts'}


def _pandas(frame):
    return frame.to_pandas() if hasattr(frame, 'to_pandas') else frame


def _text(value):
    """A string, or None for a missing value -- never NaN, which is not JSON."""
    return value if isinstance(value, str) and value else None


def starters(depth):
    """{team: {gsis_id}} from each team's LATEST depth-chart snapshot: rank 1
    on offense or defense, plus the kicker and punter."""
    if depth is None or len(depth) == 0:
        return {}
    latest = depth[depth['dt'] == depth.groupby('team')['dt'].transform('max')]
    rank1 = latest[latest['pos_rank'].astype(str) == '1']
    keep = rank1[(rank1['pos_grp'] != 'Special Teams') | rank1['pos_abb'].isin(KICKING)]
    return {team: set(g['gsis_id'].dropna()) for team, g in keep.groupby('team')}


def injuries_for(injuries, starter_ids, team, week):
    """(out, doubtful, questionable_count, published) for one team and week."""
    rows = injuries[(injuries['week'] == week) & (injuries['team'] == team)]
    published = bool(len(injuries[injuries['week'] == week]))
    mine = rows[rows['gsis_id'].isin(starter_ids)]
    def listed(status):
        hit = mine[mine['report_status'] == status]
        return [{'name': r['full_name'], 'position': r['position'],
                 'injury': _text(r['report_primary_injury'])}
                for _, r in hit.sort_values('full_name').iterrows()]
    questionable = int((mine['report_status'] == 'Questionable').sum())
    return listed('Out'), listed('Doubtful'), questionable, published


def quarterback(pick, side):
    """The pick's own quarterback and whether he is new, or None when the
    saved prediction predates the fields (weeks locked before v2.5)."""
    name = pick.get(f'{side}_qb')
    if not name:
        return None
    last_id, chosen_id = pick.get(f'last_game_{side}_qb_id'), pick.get(f'{side}_qb_id')
    changed = bool(last_id) and bool(chosen_id) and last_id != chosen_id
    return {'name': name, 'basis': pick.get(f'{side}_qb_basis'),
            'changed_from': pick.get(f'last_game_{side}_qb') if changed else None}


def build_week(preds, injuries, depth, week):
    starter_ids = starters(depth)
    teams = {}
    for p in preds:
        for side in ('home', 'away'):
            team = p[side]
            out, doubtful, questionable, published = injuries_for(
                injuries, starter_ids.get(team, set()), team, week)
            entry = {'qb': quarterback(p, side)}
            if not starter_ids.get(team):
                entry['injury_report'] = 'no depth chart for this team'
            elif published:
                entry.update(injury_report='published', out=out, doubtful=doubtful,
                             questionable_starters=questionable)
            else:
                entry['injury_report'] = 'not yet published'
            teams[team] = entry
    return teams


def write_week(season, week, teams, depth_dt, now, news_dir=NEWS_DIR):
    news_dir.mkdir(parents=True, exist_ok=True)
    path = news_dir / f'{season}_week{week}.json'
    body = {'season': season, 'week': week,
            'read_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'sources': dict(SOURCES, depth_chart_snapshot=depth_dt), 'teams': teams}
    if path.exists():
        old = json.loads(path.read_text(encoding='utf-8'))
        if old.get('teams') == teams:
            return False
    path.write_text(json.dumps(body, indent=2) + '\n', encoding='utf-8')
    return True


def main(argv=None, now=None, load=None, pred_dir=PRED_DIR, results_dir=RESULTS_DIR,
         news_dir=NEWS_DIR):
    ap = argparse.ArgumentParser()
    ap.add_argument('--season', type=int, default=None)
    which = ap.add_mutually_exclusive_group(required=True)
    which.add_argument('--weeks', type=int, nargs='+')
    which.add_argument('--pending', action='store_true')
    args = ap.parse_args(argv)
    now = now or datetime.now(timezone.utc)
    from weekend_refresh import current_season, weeks_to_refresh
    season = args.season or current_season(now)
    weeks = weeks_to_refresh(season, pred_dir, results_dir) if args.pending else args.weeks
    if not weeks:
        print(f'{season}: no locked week is waiting on grading; no team news to read.')
        return 0
    if load is None:
        import nflreadpy as nfl
        load = lambda s: (_pandas(nfl.load_injuries([s])), _pandas(nfl.load_depth_charts([s])))
    injuries, depth = load(season)
    depth_dt = str(depth['dt'].max()) if len(depth) else None
    for week in weeks:
        path = pred_dir / f'{season}_week{week}.json'
        if not path.exists():
            print(f'WARNING week {week}: no saved picks, so no teams to report on')
            continue
        preds = json.loads(path.read_text(encoding='utf-8'))
        teams = build_week(preds, injuries, depth, week)
        wrote = write_week(season, week, teams, depth_dt, now, news_dir)
        named = sum(len(t.get('out', [])) + len(t.get('doubtful', [])) for t in teams.values())
        states = sorted({t['injury_report'] for t in teams.values()})
        print(f"week {week}: {len(teams)} teams, {named} starter(s) out or doubtful, "
              f"report {', '.join(states)} -- {'written' if wrote else 'unchanged, not rewritten'}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
