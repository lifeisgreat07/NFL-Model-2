"""The MLB data probe judges each source on the shape a later stage needs.

Stage 97 item 1. `src/sports/mlb/data_probe.py` reads the sources MLB's go/no-go
will rely on; the network part runs in `.github/workflows/mlb-data-probe.yml`,
from GitHub's own runners. Payloads here are small and synthetic, in the Stats
API's, Retrosheet's and ESPN's shapes.

Run with: pytest tests/test_mlb_data_probe.py -v
"""
import io
import json
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from src.sports.mlb import data_probe as probe

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'mlb-data-probe.yml'
NOW = datetime(2026, 11, 11, tzinfo=UTC)


def game(pk=777245, home=120, away=111, date='2025-07-04T15:05:00Z', state='Final', dh='N', number=1,
         probables=True):
    def side(club, pitcher):
        s = {'team': {'id': club}}
        if probables:
            s['probablePitcher'] = {'id': pitcher}
        return s
    return {'gamePk': pk, 'gameDate': date, 'officialDate': date[:10], 'doubleHeader': dh, 'gameNumber': number,
            'status': {'detailedState': state}, 'teams': {'home': side(home, 1), 'away': side(away, 2)}}


def day(*games):
    return {'dates': [{'games': list(games)}]}


def test_a_complete_schedule_passes():
    assert probe.check_schedule(day(game(), game(pk=777246, home=112, away=138))) == []


def test_a_schedule_game_missing_what_the_lock_needs_is_named():
    assert 'two clubs' in probe.check_schedule(day(game(away=120)))[0]
    assert 'a UTC start' in probe.check_schedule(day(game(date='2025-07-04T11:05:00-04:00')))[0]
    assert 'a state' in probe.check_schedule(day(game(state='')))[0]
    assert 'gameNumber' in probe.check_schedule(day(dict(game(), gameNumber=None)))[0]
    assert probe.check_schedule({'dates': []}) == ['no games on a date that had games']


def test_every_game_needs_both_probable_pitchers():
    assert probe.check_probables(day(game())) == []
    assert probe.check_probables(day(game(), game(pk=2, probables=False))) == ['1 of 2 games name both probables']
    assert probe.check_probables({'dates': []}) == ['0 of 0 games name both probables']


def test_a_doubleheader_is_two_gamepks_numbered_one_and_two():
    first, second = game(pk=1, dh='S', number=1), game(pk=2, dh='S', number=2)
    assert probe.check_doubleheader(day(first, second, game(pk=3, home=112, away=138))) == []
    assert probe.check_doubleheader(day(first, dict(second, gamePk=1))) == [
        'a doubleheader whose two games share a gamePk']
    assert probe.check_doubleheader(day(first, dict(second, gameNumber=1))) == [
        'a doubleheader without game numbers 1 and 2']
    assert probe.check_doubleheader(day(first)) == ['no doubleheader on a date that had one']


def test_the_season_ahead_must_be_listed_in_full():
    assert probe.check_season({'totalGames': 2430}) == []
    assert probe.check_season({'totalGames': 162}) == ['162 games listed, fewer than 2400']
    assert probe.check_season({}) != []


def box(drop=None, pitchers=(1,)):
    stats = {g: {n: 0 for n in names if n != drop} for g, names in probe.BOX_STATS.items()}
    return {'teams': {s: {'teamStats': stats, 'pitchers': list(pitchers)} for s in ('home', 'away')}}


def test_a_box_score_needs_the_rating_totals_and_a_starter():
    assert probe.check_box_score(box()) == []
    assert 'no earnedRuns' in probe.check_box_score(box(drop='earnedRuns'))[0]
    assert 'no pitchers, so no starter' in probe.check_box_score(box(pitchers=()))[0]
    assert probe.check_box_score({'teams': {'home': {}}}) == ['no home and away in the box score']


def test_the_league_has_thirty_clubs():
    assert probe.check_teams({'teams': [{'id': i} for i in range(1, 31)]}) == []
    assert probe.check_teams({'teams': [{'id': i} for i in range(1, 30)]}) == ['29 clubs, not 30']


def game_log(rows=2430, fields=161):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('gl2025.txt', '\n'.join(','.join(['"x"'] * fields) for _ in range(rows)))
    return buf.getvalue()


def test_a_retrosheet_game_log_is_a_zipped_season_with_the_scores():
    assert probe.check_retro(game_log()) == []
    assert probe.check_retro(game_log(rows=100)) == ['100 games, fewer than 2400']
    assert probe.check_retro(game_log(fields=9)) == ['2430 lines too short to hold the score']
    assert 'not a zip' in probe.check_retro(b'<!DOCTYPE html>404')[0]


def test_odds_need_both_moneylines():
    assert probe.check_odds({'items': [{'homeTeamOdds': {'moneyLine': -150}, 'awayTeamOdds': {'moneyLine': 130}}]}) == []
    assert probe.check_odds({'items': [{'homeTeamOdds': {'moneyLine': -150}, 'awayTeamOdds': {}}]}) == [
        'a moneyline is missing for one club']
    assert probe.check_odds({'items': []}) == ['no odds for a past game']


def test_a_live_price_list_needs_something_in_it():
    assert probe.check_events([{}]) == [] and probe.check_events({'markets': [{}]}) == []
    assert probe.check_events([]) == ['no events listed'] and probe.check_events({'events': []}) == ['no events listed']


def test_the_seasons_follow_the_world_series():
    assert probe.last_finished_season(NOW) == 2026
    assert probe.last_finished_season(datetime(2026, 10, 31, tzinfo=UTC)) == 2025


def fake_get(overrides=None):
    responses = {
        f'date={probe.DOUBLEHEADER_DATE}': day(game(pk=1, dh='S', number=1), game(pk=2, dh='S', number=2)),
        f'date={probe.PAST_DATE}': day(game()),
        'season=2027&gameType=R': {'totalGames': 2430},
        '/boxscore': box(),
        '/teams?': {'teams': [{'id': i} for i in range(1, 31)]},
        '/scoreboard?': {'events': [{'id': '401696600'}]},
        '/odds': {'items': [{'homeTeamOdds': {'moneyLine': -150}, 'awayTeamOdds': {'moneyLine': 130}}]},
        'draftkings.com': {'events': [{}]},
        'kalshi.com': {'markets': [{}]},
        'polymarket.com': [{}],
    }
    responses.update(overrides or {})

    def get(url):
        for pattern, body in responses.items():
            if pattern in url:
                if isinstance(body, Exception):
                    raise body
                return json.dumps(body)
        raise AssertionError(f'unexpected url {url}')
    return get


def fake_bytes(url):
    assert url == f'{probe.RETRO}/gl2025.zip', url
    return game_log()


def test_every_required_source_usable_exits_zero_and_reads_the_season_ahead(capsys):
    seen = []
    get = fake_get()

    def spy(url):
        seen.append(url)
        return get(url)
    assert probe.main(get=spy, get_bytes=fake_bytes, now=NOW) == 0
    assert any('season=2027&gameType=R' in u for u in seen) and any('/teams?sportId=1&season=2027' in u for u in seen)
    assert any('/game/777245/boxscore' in u for u in seen), 'the box score is the past day\'s first final game'
    assert 'all usable from here' in capsys.readouterr().out


def test_a_required_source_missing_fails_the_run_and_says_which(capsys):
    assert probe.main(get=fake_get({'/boxscore': OSError('HTTP Error 404: Not Found')}), get_bytes=fake_bytes,
                      now=NOW) == 1
    out = capsys.readouterr().out
    assert 'Stats API box score: UNREACHABLE' in out and 'NOT all usable' in out


def test_a_required_source_in_the_wrong_shape_fails_the_run(capsys):
    assert probe.main(get=fake_get({'season=2027&gameType=R': {'totalGames': 0}}), get_bytes=fake_bytes,
                      now=NOW) == 1
    assert 'Stats API season 2027: NOT usable as-is' in capsys.readouterr().out


def test_a_candidate_refused_is_reported_and_does_not_fail_the_run(capsys):
    refused = {'draftkings.com': OSError('HTTP Error 403: Forbidden'), '/scoreboard?': OSError('HTTP Error 403')}
    assert probe.main(get=fake_get(refused), get_bytes=fake_bytes, now=NOW) == 0
    out = capsys.readouterr().out
    assert 'DraftKings MLB: UNREACHABLE' in out and 'ESPN scoreboard: UNREACHABLE' in out


def test_on_a_runner_one_notice_sums_every_source_up(capsys, monkeypatch):
    monkeypatch.setenv('GITHUB_ACTIONS', 'true')
    assert probe.main(get=fake_get({'kalshi.com': OSError('HTTP Error 403')}), get_bytes=fake_bytes, now=NOW) == 0
    notices = [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith('::notice')]
    assert len(notices) == 1
    for part in ('Stats API schedule 2025-07-04: ok', 'Stats API doubleheader 2025-04-26: ok',
                 'Kalshi MLB game markets: UNREACHABLE', 'Retrosheet game log 2025: ok'):
        assert part in notices[0], part


def test_off_a_runner_there_is_no_notice(capsys, monkeypatch):
    monkeypatch.delenv('GITHUB_ACTIONS', raising=False)
    probe.main(get=fake_get(), get_bytes=fake_bytes, now=NOW)
    assert '::notice' not in capsys.readouterr().out


def test_the_workflow_runs_the_probe_on_its_own_pull_requests_and_writes_nothing():
    wf = WORKFLOW.read_text(encoding='utf-8')
    assert re.search(r'^name: MLB ', wf, re.M)
    assert "'src/sports/mlb/data_probe.py'" in wf and "'.github/workflows/mlb-data-probe.yml'" in wf
    assert 'workflow_dispatch' in wf and 'schedule:' not in wf
    assert 'python -m src.sports.mlb.data_probe' in wf
    assert re.search(r'permissions:\s*\n\s*contents: read\s*\n', wf)
    assert 'git-auto-commit' not in wf and 'git add' not in wf and 'git push' not in wf
