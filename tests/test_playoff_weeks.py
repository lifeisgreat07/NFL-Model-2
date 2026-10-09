"""The NFL's playoff weeks, before they arrive (Stage 39 items 1, 2, 3 and 7).

nflverse numbers the playoffs on from the regular season: since 2021, week
19 is the Wild Card round (six games), 20 the Divisional (four), 21 the
Conference Championships (two) and 22 the Super Bowl (one). Nothing played
yet has reached them, so this holds what will happen:

- the board names the round, not "Week 19" (item 2);
- the built page's checks pass a latest week of 6, 4, 2 or 1 games, and the
  weekend refresh keeps a 1-game week open until its game is graded (item 3);
- every kind of kickoff the season holds, the playoffs included, gets a
  status refresh soon after its game ends, from the weekend refresh's and
  the Weekly update's own cron lines (item 7). Friday games are the named
  exception: no slot runs between Friday 05:17 and Sunday 21:47 UTC, so a
  Black Friday or Christmas game's card says "started" until Sunday evening.
  Adding a Saturday slot is a cron-job.org change, which is Mark's.

The rest of item 1 lives where the rule does: the postponed and cancelled
games in tests/test_league_scenarios.py, the tie in
tests/test_pipeline_chain_end_to_end.py, the calendar cases in
tests/test_pick_lock_time.py, and the empty week after the Super Bowl in
weekly_update.plan_week, which exits cleanly on a week with no games.

Run with: pytest tests/test_playoff_weeks.py -v
"""
import json
import re
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from src.core.start_delay import Cron, crons
from src.core.template_parts import JOINED_TEMPLATE
from src.sports.nfl import check_build as cb
from src.sports.nfl import weekend_refresh as wr

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / '.github' / 'workflows'
NODE = shutil.which('node')
ET = ZoneInfo('America/New_York')
ROUNDS = {19: (6, 'Wild Card'), 20: (4, 'Divisional'), 21: (2, 'Conference Championships'), 22: (1, 'Super Bowl')}


# ---------------------------------------------------------------- round names (item 2)

def function_source(src, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


@pytest.fixture(scope='module')
def labels():
    if not NODE:
        pytest.skip('node not available')
    weeks = {f'2026_week{w}': {'season': 2026, 'week': w} for w in (18, 19, 20, 21, 22)}
    weeks['2020_week19'] = {'season': 2020, 'week': 19}
    weeks['2026_week19p'] = {'season': 2026, 'week': 19, 'preview': True}
    src = JOINED_TEMPLATE.read_text(encoding='utf-8')
    js = (f'const weeks = {json.dumps(weeks)};' + function_source(src, 'weekLabel')
          + 'const o = {}; for (const k in weeks) o[k] = weekLabel(k); process.stdout.write(JSON.stringify(o));')
    r = subprocess.run([NODE, '-e', js], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_each_playoff_week_is_named_for_its_round(labels):
    for week, (_, name) in ROUNDS.items():
        assert labels[f'2026_week{week}'] == f'2026 · {name}'


def test_the_regular_season_and_a_preview_keep_their_labels(labels):
    assert labels['2026_week18'] == '2026 · Week 18'
    assert labels['2026_week19p'] == '2026 · Wild Card (preview)'


def test_a_season_before_2021_keeps_week_numbers(labels):
    """Seventeen-week seasons put the Wild Card round at week 18, so the
    names apply from 2021 only."""
    assert labels['2020_week19'] == '2020 · Week 19'


# ---------------------------------------------------------------- small weeks (item 3)

def good_page(latest, games):
    teams = sorted(cb.NFL_TEAMS)
    payloads = {
        'agentLog': {'summary': {}}, 'versionHistory': [{'version': '2.5'}], 'modelVersion': '2.5',
        'teams': [{'team': t} for t in teams], 'playoffMeta': {'season': 2026},
        'weeks': {'2026_week18': {'games': [{'home': 'KC'}] * 16}, latest: {'games': [{'home': 'KC'}] * games}},
        'latestWeekKey': latest, 'picksPdfs': [latest], 'accuracy': {'weeks': []},
        'teamHistory': {'names': {}, 'timeline': {t: [{'net': 0}] for t in teams}},
        'calibration': {'models': {'model_a': {}}}, 'recentRuns': None,
    }
    return '<script>\n' + '\n'.join(f'const {k} = {json.dumps(v)};' for k, v in payloads.items()) + '\n</script>'


@pytest.mark.parametrize('week', sorted(ROUNDS))
def test_the_build_check_passes_a_playoff_week_of_any_size(week):
    report = cb.check(good_page(f'2026_week{week}', ROUNDS[week][0]))
    assert report.errors == [], report.errors


def write_week(folder, name, n):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(json.dumps([{'home': 'KC', 'away': 'PHI'}] * n), encoding='utf-8')


@pytest.mark.parametrize('week', sorted(ROUNDS))
def test_a_playoff_week_stays_open_until_every_game_is_graded(tmp_path, week):
    n = ROUNDS[week][0]
    pred, res = tmp_path / 'pred', tmp_path / 'res'
    write_week(pred, f'2026_week{week}.json', n)
    res.mkdir()
    assert wr.weeks_to_refresh(2026, pred_dir=pred, results_dir=res, cancelled={}) == [week]
    write_week(res, f'2026_week{week}_graded.json', n - 1)
    assert wr.weeks_to_refresh(2026, pred_dir=pred, results_dir=res, cancelled={}) == [week]
    write_week(res, f'2026_week{week}_graded.json', n)
    assert wr.weeks_to_refresh(2026, pred_dir=pred, results_dir=res, cancelled={}) == []


# ---------------------------------------------------------------- status refresh (item 7)

#: One of each kind of kickoff the 2026 season holds, in Eastern time.
KICKOFFS = {
    'Wednesday opener': '2026-09-09 20:20', 'Thursday night': '2026-10-08 20:15',
    'London, Sunday morning': '2026-10-11 09:30', 'Sunday early': '2026-10-11 13:00',
    'Sunday late': '2026-10-11 16:25', 'Sunday night': '2026-10-11 20:20', 'Monday night': '2026-10-12 20:15',
    'Thanksgiving night': '2026-11-26 20:20', 'Saturday in December': '2026-12-19 20:15',
    'Week 18 Saturday': '2027-01-09 20:15', 'Wild Card Saturday': '2027-01-16 20:15',
    'Wild Card Monday': '2027-01-18 20:15', 'Divisional Sunday': '2027-01-24 18:30',
    'Conference Sunday': '2027-01-31 18:30', 'Super Bowl': '2027-02-14 18:30',
    'Black Friday': '2026-11-27 15:00', 'Christmas, Friday afternoon': '2026-12-25 13:00',
    'Christmas, Friday night': '2026-12-25 20:15',
}
#: A game is final about this long after kickoff.
GAME_LENGTH = timedelta(hours=3, minutes=30)
#: The refresh must follow the end within this; a Friday game within FRIDAY.
WITHIN = timedelta(hours=24)
FRIDAY = timedelta(hours=49)


def refresh_crons():
    return (crons((WORKFLOWS / 'nfl-weekend-refresh.yml').read_text(encoding='utf-8'))
            + crons((WORKFLOWS / 'nfl-weekly-update.yml').read_text(encoding='utf-8')))


def next_refresh(after, exprs):
    t = after.replace(second=0, microsecond=0)
    for i in range(60 * 24 * 8):
        tt = t + timedelta(minutes=i)
        if any(Cron(e).matches(tt) for e in exprs):
            return tt
    return None


@pytest.mark.parametrize('name', sorted(KICKOFFS))
def test_every_kind_of_kickoff_gets_a_status_refresh_soon_after_the_game(name):
    exprs = refresh_crons()
    kick = datetime.fromisoformat(KICKOFFS[name]).replace(tzinfo=ET).astimezone(UTC)
    end = kick + GAME_LENGTH
    found = next_refresh(end, exprs)
    assert found is not None, f'{name}: no refresh slot in the eight days after it'
    limit = FRIDAY if kick.astimezone(ET).weekday() == 4 else WITHIN
    gap = found - end
    assert gap <= limit, f'{name}: the first refresh after the game comes {gap} later ({found:%a %H:%M} UTC)'


def test_the_friday_exception_is_needed_and_no_wider():
    """If a slot is added that covers Friday games, this fails, and the
    exception above should go."""
    exprs = refresh_crons()
    gaps = []
    for name, s in KICKOFFS.items():
        kick = datetime.fromisoformat(s).replace(tzinfo=ET).astimezone(UTC)
        if kick.astimezone(ET).weekday() == 4:
            gaps.append(next_refresh(kick + GAME_LENGTH, exprs) - (kick + GAME_LENGTH))
    assert max(gaps) > WITHIN, 'every Friday game is now refreshed within a day: drop the exception'
