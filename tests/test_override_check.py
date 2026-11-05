"""
Stage 88 item 4 (the 2026-11-02 review): a QB override is checked against the
team's roster at quarterback, and its source against an allowlist, on the
pull request that adds it and again at the lock.

No test here reads the network: the roster is passed in.

Run with: pytest tests/test_override_check.py -v
"""
import json
from pathlib import Path

import pytest

from src.sports.nfl import override_check as oc
from src.sports.nfl import weekly_update as wu
from src.sports.nfl.paths import TEAM_NAMES

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / '.github' / 'workflows'

ROSTER = {
    '00-0038400': {'team': 'PHI', 'position': 'QB', 'status': 'ACT', 'name': 'Tanner McKee'},
    '00-0036389': {'team': 'PHI', 'position': 'QB', 'status': 'RES', 'name': 'Jalen Hurts'},
    '00-0041251': {'team': 'TB', 'position': 'QB', 'status': 'DEV', 'name': 'Jalon Daniels'},
    '00-0035000': {'team': 'TB', 'position': 'WR', 'status': 'ACT', 'name': 'A Receiver'},
}
DOMAINS = oc.allowed_domains()


def override(team='PHI', pid='00-0038400', name='Tanner McKee',
             source='https://www.espn.com/nfl/story/_/id/50218378/eagles'):
    return {'team': team, 'player_id': pid, 'player_name': name, 'source': source}


# --- the allowlist -----------------------------------------------------------------

def test_every_team_has_its_own_site_and_the_outlets_are_listed():
    spec = json.loads(oc.SOURCES.read_text(encoding='utf-8'))
    assert set(spec['teams']) == set(TEAM_NAMES)
    assert len(set(spec['teams'].values())) == 32
    assert {'nfl.com', 'espn.com', 'cbssports.com'} <= set(spec['outlets'])


@pytest.mark.parametrize('url', ['https://www.espn.com/nfl/story/x', 'https://espn.com/x',
                                 'https://www.philadelphiaeagles.com/news/x', 'http://www.nfl.com/news/x'])
def test_a_listed_site_or_its_subdomain_is_allowed(url):
    assert oc.source_allowed(url, DOMAINS)


@pytest.mark.parametrize('url', ['https://notespn.com/x', 'https://espn.com.evil.example/x',
                                 'https://example.com/?u=https://espn.com', 'ftp://espn.com/x',
                                 'espn.com/nfl', 'https://x.com/someone/status/1'])
def test_anything_else_is_not(url):
    assert not oc.source_allowed(url, DOMAINS)


# --- the roster --------------------------------------------------------------------

def test_a_quarterback_on_the_team_who_can_play_passes():
    assert oc.problems([override()], ROSTER, DOMAINS) == {}
    assert oc.problems([override('TB', '00-0041251', 'Jalon Daniels', 'https://www.nfl.com/news/x')],
                       ROSTER, DOMAINS) == {}


@pytest.mark.parametrize('entry, says', [
    (override(pid='00-0099999', name='Nobody'), 'is not on any current roster'),
    (override(team='TB'), "is on PHI's roster, not TB's"),
    (override(team='TB', pid='00-0035000', name='A Receiver'), 'is listed at WR, not quarterback'),
    (override(pid='00-0036389', name='Jalen Hurts'), 'has roster status RES, which cannot start'),
])
def test_a_player_who_cannot_be_the_teams_starter_is_named(entry, says):
    found = oc.problems([entry], ROSTER, DOMAINS)
    assert list(found) == [entry['team']] and says in found[entry['team']][0]


def test_an_unlisted_source_is_named_and_an_unreadable_roster_checks_only_the_source():
    bad = override(source='https://someblog.example/eagles')
    (msg,) = oc.problems([bad], ROSTER, DOMAINS)['PHI']
    assert 'someblog.example/eagles is not a team site or a listed outlet' in msg
    assert oc.problems([override(pid='00-0099999')], None, DOMAINS) == {}


# --- at the lock ---------------------------------------------------------------------

def test_the_lock_drops_an_override_that_fails_and_keeps_the_rest():
    overrides = {'PHI': override(pid='00-0036389', name='Jalen Hurts'),
                 'TB': override('TB', '00-0041251', 'Jalon Daniels', 'https://www.nfl.com/news/x')}
    kept, lines = oc.screen(overrides, 2026, loader=lambda season: ROSTER, domains=DOMAINS)
    assert list(kept) == ['TB']
    assert lines == ["DEGRADED: QB overrides: not used, PHI: Jalen Hurts (00-0036389) has roster status RES, "
                     "which cannot start; the pick uses the schedule's starter"]


def test_an_unreadable_roster_keeps_the_overrides_and_says_so():
    def broken(season):
        raise OSError('nflverse unreachable')
    kept, lines = oc.screen({'PHI': override()}, 2026, loader=broken, domains=DOMAINS)
    assert list(kept) == ['PHI']
    assert lines == ['DEGRADED: QB overrides: the roster could not be read (OSError: nflverse unreachable), '
                     'so the overrides were used without the roster check']
    kept, lines = oc.screen({'PHI': override()}, 2026, loader=lambda s: {}, domains=DOMAINS)
    assert list(kept) == ['PHI'] and 'the roster came back empty' in lines[0]


def test_no_overrides_reads_no_roster():
    def never(season):
        raise AssertionError('read the roster for nothing')
    assert oc.screen({}, 2026, loader=never) == ({}, [])


def test_plan_week_screens_the_overrides_before_using_them():
    src = Path(wu.__file__).read_text(encoding='utf-8')
    load = src.index('    qb_overrides = load_qb_overrides(season, week)\n')
    screen = src.index('    qb_overrides, screened = override_check.screen(qb_overrides, season)\n')
    used = src.index('    no_starters = None if preview else starter_warning(week_games, qb_overrides, season, week)')
    assert load < screen < used
    assert '    for line in screened:\n        log.info(line)\n' in src[screen:used]


# --- on the pull request -------------------------------------------------------------

def write(tmp_path, name, entries):
    path = tmp_path / name
    path.write_text(json.dumps(entries), encoding='utf-8')
    return str(path)


def test_the_pr_check_passes_good_files_and_fails_a_bad_one(tmp_path, capsys):
    good = write(tmp_path, '2026_week9.json', [override()])
    assert oc.main([good], loader=lambda s: ROSTER) == 0
    bad = write(tmp_path, '2026_week10.json', [override(pid='00-0036389', name='Jalen Hurts')])
    assert oc.main([good, bad], loader=lambda s: ROSTER) == 1
    out = capsys.readouterr().out
    assert '2026_week10.json: PHI: Jalen Hurts (00-0036389) has roster status RES' in out


def test_the_pr_check_fails_when_it_cannot_check(tmp_path, capsys):
    good = write(tmp_path, '2026_week9.json', [override()])

    def broken(season):
        raise OSError('down')
    assert oc.main([good], loader=broken) == 1
    assert 'could not be read (OSError: down); not checked' in capsys.readouterr().out
    malformed = write(tmp_path, '2026_week11.json', [{'team': 'PHI'}])
    assert oc.main([malformed], loader=lambda s: ROSTER) == 1
    assert oc.main([write(tmp_path, 'notes.json', [])], loader=lambda s: ROSTER) == 1


def test_the_committed_override_files_pass_the_source_check():
    """The roster has moved on since; the sources have not."""
    for path in sorted((ROOT / 'data' / 'nfl' / 'qb_overrides').glob('*.json')):
        entries = json.loads(path.read_text(encoding='utf-8'))
        assert oc.problems(entries, None, DOMAINS) == {}, path.name


def test_the_pr_workflow_runs_the_base_commits_check_on_the_heads_files():
    text = (WORKFLOWS / 'nfl-override-check.yml').read_text(encoding='utf-8')
    assert "paths:\n      - 'data/nfl/qb_overrides/**'" in text
    assert 'ref: ${{ github.event.pull_request.base.sha }}' in text and 'persist-credentials: false' in text
    assert '?ref=$HEAD_SHA' in text and 'python -m src.sports.nfl.override_check "$RUNNER_TEMP"/overrides/*.json' in text
    assert 'shell: bash' in text  # pipefail: the check's exit code survives the tee
    assert 'contents: write' not in text and 'issues: write' not in text


def test_the_weekly_workflow_raises_an_issue_on_a_refused_override():
    text = (WORKFLOWS / 'nfl-weekly-update.yml').read_text(encoding='utf-8')
    (step,) = [s for s in text.split('\n      - ') if s.startswith('name: Did the lock refuse a QB override?')]
    assert "grep -q '^DEGRADED: QB overrides:' weekly-update.log" in step
    assert '--title "NFL: the lock did not use a QB override"' in step and 'continue-on-error: true' in step
    assert text.index('- name: Generate/lock in this week') < text.index('- name: Did the lock refuse a QB override?')
