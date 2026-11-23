"""
Stage 86 item 5 (the 2026-11-02 review): an invariant over committed data
becomes a postcondition of the run that writes the data.

The weekly run writes data/nfl/current_ratings.json and appends the same
ratings to data/nfl/team_history_<season>.json; Power Ratings' rank change
rests on the first being the second's latest week. The run now checks that
after writing both, prints a DEGRADED line when it fails, and the Weekly
update raises an issue on that line and closes it on the run's OK line.

Run with: pytest tests/test_ratings_snapshot.py -v
"""
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from src.sports.nfl import generate_dashboard as gd
from src.sports.nfl import ratings_snapshot as rs
from src.sports.nfl import weekly_update as wu

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'nfl-weekly-update.yml'
TITLE = "NFL: the ratings snapshot is not its history's latest week"


def snap(**nets):
    return [{'team': t, 'net': n} for t, n in nets.items()]


def hist(*weeks):
    out = {}
    for w, nets in enumerate(weeks, start=1):
        for team, net in nets.items():
            out.setdefault(team, []).append({'week': w, 'net': net})
    return out


def test_a_snapshot_that_is_the_latest_week_agrees():
    assert rs.mismatches(snap(A=0.2, B=-0.1), hist({'A': 0.1, 'B': 0.0}, {'A': 0.2, 'B': -0.1})) == []


def test_one_rounding_step_is_still_the_same_week():
    """The 2026-10-29 case: -0.073 in the history, -0.0731 in the snapshot."""
    assert rs.mismatches(snap(WAS=-0.0731), hist({'WAS': -0.073})) == []
    assert rs.mismatches(snap(WAS=-0.0734), hist({'WAS': -0.073})) == ['WAS: -0.0734 in the snapshot, -0.073 in week 1']


def test_a_snapshot_of_an_earlier_week_or_a_missing_team_is_named():
    h = hist({'A': 0.1, 'B': 0.0}, {'A': 0.2})
    assert rs.mismatches(snap(A=0.1, B=0.0), h) == ['A: 0.1 in the snapshot, 0.2 in week 2', 'B: not in week 2 of the history']
    assert rs.mismatches(snap(A=0.1), {}) == ['the season history has no week']


def test_the_check_reads_the_season_files_and_says_degraded(tmp_path):
    assert rs.check(tmp_path, 2026) == []  # no history yet: nothing to check
    (tmp_path / 'current_ratings.json').write_text(json.dumps(snap(A=0.5)))
    (tmp_path / 'team_history_2026.json').write_text(json.dumps(hist({'A': 0.1})))
    (line,) = rs.check(tmp_path, 2026)
    assert line.startswith('DEGRADED: ratings snapshot: data/nfl/current_ratings.json is not the latest week of '
                           'data/nfl/team_history_2026.json') and line.endswith('A: 0.5 in the snapshot, 0.1 in week 1')
    many = {f'T{i:02d}': 0.0 for i in range(11)}
    (tmp_path / 'current_ratings.json').write_text(json.dumps(snap(**{t: 1.0 for t in many})))
    (tmp_path / 'team_history_2026.json').write_text(json.dumps(hist(many)))
    (line,) = rs.check(tmp_path, 2026)
    assert line.count(' in the snapshot,') == 8 and line.endswith('; and 3 more')


def test_the_dashboard_and_the_check_share_one_tolerance():
    assert gd.SNAPSHOT_MATCH_TOL is rs.TOL


# --- the run that writes the data checks it -------------------------------------

def run_refresh(tmp_path, monkeypatch, history_net):
    """refresh_current_state with its writers faked: the snapshot says A is
    at 0.3, and the history's latest week says `history_net`."""
    monkeypatch.setattr(wu, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(wu, 'current_ratings', lambda plays, keys: {'A': (0.5, 0.2)})

    def save_current(ratings, season_schedule=None):
        (tmp_path / 'current_ratings.json').write_text(json.dumps(snap(A=0.3)))

    def append(ratings, season, week):
        (tmp_path / f'team_history_{season}.json').write_text(json.dumps(hist({'A': history_net})))

    monkeypatch.setattr(wu, 'save_current_ratings', save_current)
    monkeypatch.setattr(wu, 'save_playoff_odds', lambda *a, **k: None)
    monkeypatch.setattr(wu, 'append_live_history', append)
    starters = pd.DataFrame({'posteam': ['A'], 'week': [1], 'passer_player_id': ['x']})
    inputs = SimpleNamespace(plays=None, week_keys=[(2026, 1)], hist=None, schedules_by_season={},
                             qb={'week_keys': [(2026, 1)], 'identify_starters': lambda s: starters})
    wu.refresh_current_state(inputs, 2026)


def test_the_weekly_run_checks_what_it_wrote_and_says_so(tmp_path, monkeypatch, capsys):
    run_refresh(tmp_path, monkeypatch, 0.3)
    out = capsys.readouterr().out
    assert rs.OK in out.splitlines() and 'DEGRADED' not in out


def test_a_run_whose_snapshot_is_not_its_history_prints_degraded_not_ok(tmp_path, monkeypatch, capsys):
    run_refresh(tmp_path, monkeypatch, 0.1)
    lines = capsys.readouterr().out.splitlines()
    assert any(re.match(r'^DEGRADED: ratings snapshot: .*A: 0\.3 in the snapshot, 0\.1 in week 1$', s) for s in lines)
    assert rs.OK not in lines


# --- the workflow raises and closes the issue -------------------------------------

def step():
    text = WORKFLOW.read_text(encoding='utf-8')
    (s,) = [s for s in text.split('\n      - ') if f'--title "{TITLE}"' in s and '--resolve' not in s.split('elif')[0]]
    return text, s


def test_the_weekly_workflow_alerts_on_the_degraded_line_and_closes_on_the_ok_line():
    text, s = step()
    assert text.index('- name: Generate/lock in this week') < text.index(s)
    assert 'continue-on-error: true' in s and "if: ${{ !cancelled() }}" in s
    raise_part, resolve_part = s.split('elif')
    assert "grep -q '^DEGRADED: ratings snapshot:' weekly-update.log" in raise_part
    assert f'python -m src.core.alerts --title "{TITLE}"' in raise_part
    assert f"grep -q '^{rs.OK.split(':')[0]}:' weekly-update.log" in resolve_part
    assert f'python -m src.core.alerts --resolve --title "{TITLE}"' in resolve_part


# --- the history keeps the latest re-computation of its latest week (#790) -------------

def history_after(tmp_path, monkeypatch, start, ratings, week):
    monkeypatch.setattr(wu, 'DATA_DIR', tmp_path)
    (tmp_path / 'team_history_2026.json').write_text(json.dumps(start))
    wu.append_live_history(ratings, 2026, week)
    return json.loads((tmp_path / 'team_history_2026.json').read_text())


def point(week, off, deff):
    return {'week': week, 'net': round(off - deff, 4), 'off': off, 'def': deff}


def test_a_new_week_is_appended(tmp_path, monkeypatch):
    out = history_after(tmp_path, monkeypatch, {'BUF': [point(9, 0.12, -0.01)]}, {'BUF': (0.1161, -0.0086)}, 10)
    assert out == {'BUF': [point(9, 0.12, -0.01), point(10, 0.1161, -0.0086)]}


def test_a_re_computed_latest_week_replaces_its_point(tmp_path, monkeypatch):
    """2026-11-19: Thursday re-computed week 10 on revised play-by-play; BUF moved from 0.1418 to 0.1246."""
    start = {'BUF': [point(9, 0.12, -0.01), point(10, 0.1297, -0.0121)]}
    out = history_after(tmp_path, monkeypatch, start, {'BUF': (0.1161, -0.0086)}, 10)
    assert out == {'BUF': [point(9, 0.12, -0.01), point(10, 0.1161, -0.0086)]}
    assert out['BUF'][-1]['net'] == 0.1247 and len(out['BUF']) == 2


def test_a_week_before_the_latest_is_never_changed(tmp_path, monkeypatch):
    start = {'BUF': [point(9, 0.12, -0.01), point(10, 0.1297, -0.0121)]}
    out = history_after(tmp_path, monkeypatch, start, {'BUF': (0.5, 0.1)}, 9)
    assert out == start


def test_the_latest_is_the_season_s_not_the_team_s(tmp_path, monkeypatch):
    """A team whose newest point is an older week (it was missing from the latest) is not rewritten there."""
    start = {'BUF': [point(9, 0.12, -0.01)], 'MIA': [point(9, 0.0, 0.0), point(10, 0.01, 0.0)]}
    out = history_after(tmp_path, monkeypatch, start, {'BUF': (0.5, 0.1)}, 9)
    assert out['BUF'] == [point(9, 0.12, -0.01)]


def test_the_snapshot_and_history_agree_after_a_thursday_re_computation(tmp_path, monkeypatch):
    """Both writers for real, then the run's own check: the 2026-11-19 sequence ends OK, not DEGRADED."""
    monkeypatch.setattr(wu, 'DATA_DIR', tmp_path)
    (tmp_path / 'team_history_2026.json').write_text(json.dumps({'BUF': [point(10, 0.1297, -0.0121)]}))
    thursday = {'BUF': (0.1161, -0.0086)}
    wu.save_current_ratings(thursday)
    wu.append_live_history(thursday, 2026, 10)
    assert rs.check(tmp_path, 2026) == []
